"""
Client networking for LAN Communication Application.

Handles TCP control channel and UDP media streaming to/from server.
Runs in separate threads to avoid blocking the GUI.
"""

import socket
import threading
import json
import time
from typing import Optional, Callable
from PySide6.QtCore import QObject, Signal
from utils.logger import setup_logger
from utils.config import config, DEFAULT_TCP_PORT, DEFAULT_UDP_PORT, BUFFER_SIZE
from utils.network_proto import (
    MessageType, serialize_message, create_message,
    UDPPacket, StreamType, generate_stream_id
)
from utils.file_transfer import FileTransferManager

logger = setup_logger(__name__)

class LANClient(QObject):
    """
    LAN Communication Client.
    
    Manages connection to server, sends control messages and media streams.
    Emits Qt signals for GUI updates (thread-safe).
    """
    
    # Qt Signals for GUI updates (thread-safe)
    connected = Signal()
    disconnected = Signal()
    auth_success = Signal(str)  # username
    auth_failed = Signal(str)  # reason
    chat_message_received = Signal(str, str)  # sender, message
    user_joined = Signal(str)  # username
    user_left = Signal(str)  # username
    user_list_received = Signal(list)  # list of usernames
    file_offer_received = Signal(str, str, int, str)  # file_id, filename, size, uploader
    audio_data_received = Signal(str, bytes)  # username, audio_data
    video_data_received = Signal(str, bytes)  # username, video_data
    screen_frame_received = Signal(str, bytes, int, int)  # username, frame_data, width, height
    error_occurred = Signal(str)  # error message
    
    # Reconnection signals
    reconnection_started = Signal(int, int)  # attempt, max_attempts
    reconnection_failed = Signal(str)  # reason
    reconnection_succeeded = Signal()
    manual_retry_required = Signal()  # when automatic reconnection fails
    
    def __init__(self, username: str, server_address: str, session_id: str,
                 tcp_port: int = None, udp_port: int = None):
        """
        Initialize client.
        
        Args:
            username: Client username
            server_address: Server IP address
            session_id: Session ID to join
            tcp_port: TCP port (default from config)
            udp_port: UDP port (default from config)
        """
        super().__init__()
        
        self.username = username
        self.server_address = server_address
        self.session_id = session_id
        self.tcp_port = tcp_port or config.get('network.tcp_port', DEFAULT_TCP_PORT)
        self.udp_port = udp_port or config.get('network.udp_port', DEFAULT_UDP_PORT)
        
        logger.info(f"LANClient initialized with session_id: '{self.session_id}'")
        
        # Sockets
        self.tcp_socket: Optional[socket.socket] = None
        self.udp_socket: Optional[socket.socket] = None
        
        # State
        self.running = False
        self.authenticated = False
        self.threads = []
        self.connection_quality = 1.0  # 0.0 to 1.0
        self.last_heartbeat_response = time.time()
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        
        # Session state preservation
        self.session_state = {
            'user_list': [],
            'chat_history': [],
            'file_transfers': {},
            'active_uploads': {},
            'active_downloads': {},
            'media_state': {
                'audio_active': False,
                'video_active': False,
                'screen_sharing': False
            }
        }
        self.reconnection_in_progress = False
        self.manual_disconnect = False
        
        # Stream state
        self.audio_stream_id = generate_stream_id(username, StreamType.AUDIO)
        self.video_stream_id = generate_stream_id(username, StreamType.VIDEO)
        self.audio_seq_num = 0
        self.video_seq_num = 0
        
        # File transfer manager
        self.file_transfer_manager = FileTransferManager(self)
        
        logger.info(f"Client initialized: username={username}, server={server_address}:{tcp_port}")
    
    def connect(self) -> bool:
        """
        Connect to server and authenticate.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Create TCP socket
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_socket.connect((self.server_address, self.tcp_port))
            logger.info(f"Connected to TCP server at {self.server_address}:{self.tcp_port}")
            
            # Create UDP socket
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # Bind to any port for receiving
            self.udp_socket.bind(('0.0.0.0', 0))
            logger.info(f"UDP socket created on port {self.udp_socket.getsockname()[1]}")
            
            self.running = True
            self.connected.emit()
            
            # Send authentication request
            logger.info(f"Sending authentication: username='{self.username}', session_id='{self.session_id}'")
            auth_msg = create_message(
                MessageType.AUTH_REQUEST,
                username=self.username,
                session_id=self.session_id
            )
            self._send_tcp_message(auth_msg)
            
            # Start TCP receive thread
            tcp_thread = threading.Thread(target=self._tcp_receive_loop, daemon=True)
            tcp_thread.start()
            self.threads.append(tcp_thread)
            
            # Start UDP receive thread
            udp_thread = threading.Thread(target=self._udp_receive_loop, daemon=True)
            udp_thread.start()
            self.threads.append(udp_thread)
            
            # Start heartbeat thread
            heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
            heartbeat_thread.start()
            self.threads.append(heartbeat_thread)
            
            logger.info("Client threads started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to server: {e}")
            self.error_occurred.emit(f"Connection failed: {e}")
            self.disconnect()
            return False
    
    def disconnect(self, manual: bool = True):
        """
        Disconnect from server.
        
        Args:
            manual: True if this is a manual disconnect, False if due to network error
        """
        logger.info(f"Disconnecting from server... (manual={manual})")
        
        self.manual_disconnect = manual
        
        # Send leave message if authenticated
        if self.authenticated and manual:
            try:
                leave_msg = create_message(
                    MessageType.LEAVE_SESSION,
                    username=self.username
                )
                self._send_tcp_message(leave_msg)
            except:
                pass
        
        self.running = False
        self.authenticated = False
        
        # Close sockets
        if self.tcp_socket:
            try:
                self.tcp_socket.close()
            except:
                pass
        
        if self.udp_socket:
            try:
                self.udp_socket.close()
            except:
                pass
        
        if manual:
            self.disconnected.emit()
        logger.info("Client disconnected")
    
    # ========================================================================
    # TCP Control Channel
    # ========================================================================
    
    def _tcp_receive_loop(self):
        """Receive and process TCP control messages."""
        logger.info("TCP receive loop started")
        buffer = b''
        
        while self.running:
            try:
                data = self.tcp_socket.recv(BUFFER_SIZE)
                if not data:
                    logger.warning("TCP connection closed by server")
                    break
                
                buffer += data
                
                # Process complete messages from buffer
                while len(buffer) >= 4:
                    import struct
                    msg_length = struct.unpack(">I", buffer[:4])[0]
                    
                    if len(buffer) < 4 + msg_length:
                        break  # Wait for more data
                    
                    # Extract and process message
                    message_data = buffer[4:4+msg_length]
                    buffer = buffer[4+msg_length:]
                    
                    try:
                        message = json.loads(message_data.decode('utf-8'))
                        self._handle_control_message(message)
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")
            
            except Exception as e:
                if self.running:
                    logger.error(f"TCP receive error: {e}")
                    # Trigger reconnection if not manually disconnected
                    if not self.manual_disconnect:
                        self._handle_connection_lost()
                break
        
        logger.info("TCP receive loop stopped")
        if self.running and not self.manual_disconnect:
            self.disconnect(manual=False)
    
    def _handle_control_message(self, message: dict):
        """Handle incoming control message."""
        msg_type = message.get('type')
        logger.debug(f"Received message type: {msg_type}")
        
        # Authentication response
        if msg_type == MessageType.AUTH_RESPONSE.value:
            success = message.get('success', False)
            if success:
                self.authenticated = True
                self.auth_success.emit(self.username)
                logger.info("Authentication successful")
                
                # Send UDP hello packet after authentication is complete
                self._send_udp_hello()
            else:
                reason = message.get('reason', 'Unknown error')
                self.auth_failed.emit(reason)
                logger.warning(f"Authentication failed: {reason}")
        
        # User list
        elif msg_type == MessageType.USER_LIST.value:
            users = message.get('users', [])
            self.session_state['user_list'] = users
            self.user_list_received.emit(users)
            logger.info(f"Received user list: {users}")
        
        # User joined
        elif msg_type == MessageType.USER_JOINED.value:
            username = message.get('username')
            if username != self.username:
                if username not in self.session_state['user_list']:
                    self.session_state['user_list'].append(username)
                self.user_joined.emit(username)
                logger.info(f"User '{username}' joined")
        
        # User left
        elif msg_type == MessageType.USER_LEFT.value:
            username = message.get('username')
            if username in self.session_state['user_list']:
                self.session_state['user_list'].remove(username)
            self.user_left.emit(username)
            logger.info(f"User '{username}' left")
        
        # Chat message
        elif msg_type == MessageType.CHAT_MESSAGE.value:
            from_user = message.get('from_user')
            payload = message.get('payload')
            # Store in session state for recovery
            chat_entry = {
                'from_user': from_user,
                'message': payload,
                'timestamp': message.get('timestamp', time.time())
            }
            self.session_state['chat_history'].append(chat_entry)
            # Keep only last 100 messages
            if len(self.session_state['chat_history']) > 100:
                self.session_state['chat_history'] = self.session_state['chat_history'][-100:]
            
            self.chat_message_received.emit(from_user, payload)
            logger.info(f"Chat message from '{from_user}': {payload[:50]}...")
        
        # File offer
        elif msg_type == MessageType.FILE_OFFER.value:
            file_id = message.get('file_id')
            filename = message.get('filename')
            file_size = message.get('file_size')
            from_user = message.get('from_user')
            self.file_offer_received.emit(file_id, filename, file_size, from_user)
            logger.info(f"File offer from '{from_user}': {filename}")
        
        # File chunk (for downloads)
        elif msg_type == "file_chunk":
            file_id = message.get('file_id')
            chunk_index = message.get('chunk_index')
            chunk_data_hex = message.get('data')
            
            if file_id and chunk_index is not None and chunk_data_hex:
                try:
                    chunk_data = bytes.fromhex(chunk_data_hex)
                    self.file_transfer_manager.handle_download_chunk(file_id, chunk_index, chunk_data)
                except Exception as e:
                    logger.error(f"Error processing download chunk: {e}")
        
        # File complete (for downloads)
        elif msg_type == "file_complete":
            file_id = message.get('file_id')
            if file_id:
                self.file_transfer_manager.handle_download_complete(file_id)
        
        # File list
        elif msg_type == MessageType.FILE_LIST.value:
            files = message.get('files', [])
            for file_info in files:
                file_id = file_info.get('file_id')
                filename = file_info.get('filename')
                size = file_info.get('size')
                owner = file_info.get('owner')
                if file_id and filename and size and owner:
                    self.file_offer_received.emit(file_id, filename, size, owner)
        
        # Screen frame
        elif msg_type == "screen_frame":
            from_user = message.get('from_user')
            frame_data_hex = message.get('frame_data')
            width = message.get('width')
            height = message.get('height')
            
            if from_user and frame_data_hex:
                try:
                    frame_data = bytes.fromhex(frame_data_hex)
                    # Emit signal for GUI to handle
                    self.screen_frame_received.emit(from_user, frame_data, width or 0, height or 0)
                except Exception as e:
                    logger.error(f"Error processing screen frame: {e}")
        
        # Pong (heartbeat response)
        elif msg_type == MessageType.PONG.value:
            self.last_heartbeat_response = time.time()
            self.connection_quality = 1.0  # Reset connection quality on successful pong
            logger.debug("Received heartbeat pong")
    
    def _send_tcp_message(self, message: dict):
        """Send a TCP control message to server."""
        try:
            serialized = serialize_message(message)
            self.tcp_socket.sendall(serialized)
            logger.debug(f"Sent TCP message: {message.get('type')}")
        except Exception as e:
            logger.error(f"Failed to send TCP message: {e}")
            raise
    
    # ========================================================================
    # Public API for sending messages
    # ========================================================================
    
    def send_chat_message(self, text: str, mode: str = "broadcast", target_users: list = None):
        """
        Send a chat message.
        
        Args:
            text: Message text
            mode: 'broadcast', 'multicast', or 'unicast'
            target_users: List of target usernames (for multicast/unicast)
        """
        if not self.authenticated:
            logger.warning("Cannot send chat: not authenticated")
            return
        
        message = create_message(
            MessageType.CHAT_MESSAGE,
            from_user=self.username,
            mode=mode,
            to_users=target_users or [],
            payload=text
        )
        self._send_tcp_message(message)
        logger.info(f"Sent chat message in {mode} mode")
    
    def send_file_offer(self, file_id: str, filename: str, file_size: int,
                       mode: str = "broadcast", target_users: list = None):
        """
        Send a file offer notification.
        
        Args:
            file_id: Unique file identifier
            filename: Name of the file
            file_size: Size in bytes
            mode: 'broadcast', 'multicast', or 'unicast'
            target_users: List of target usernames
        """
        if not self.authenticated:
            logger.warning("Cannot send file offer: not authenticated")
            return
        
        message = create_message(
            MessageType.FILE_OFFER,
            from_user=self.username,
            file_id=file_id,
            filename=filename,
            file_size=file_size,
            mode=mode,
            to_users=target_users or []
        )
        self._send_tcp_message(message)
        logger.info(f"Sent file offer: {filename}")
    
    def upload_file(self, file_path: str, mode: str = "broadcast", target_users: list = None) -> Optional[str]:
        """
        Upload a file.
        
        Args:
            file_path: Path to file to upload
            mode: Communication mode
            target_users: Target users for multicast/unicast
            
        Returns:
            File ID if upload started, None otherwise
        """
        return self.file_transfer_manager.upload_file(file_path, mode, target_users)
    
    def download_file(self, file_id: str, save_path: str) -> bool:
        """
        Download a file.
        
        Args:
            file_id: ID of file to download
            save_path: Where to save the file
            
        Returns:
            True if download started successfully
        """
        return self.file_transfer_manager.download_file(file_id, save_path)
    
    def get_file_transfer_progress(self, file_id: str) -> float:
        """Get file transfer progress."""
        return self.file_transfer_manager.get_transfer_progress(file_id)
    
    def cancel_file_transfer(self, file_id: str):
        """Cancel a file transfer."""
        self.file_transfer_manager.cancel_transfer(file_id)
    
    # ========================================================================
    # UDP Media Streaming
    # ========================================================================
    
    def _udp_receive_loop(self):
        """Receive UDP media packets."""
        logger.info("UDP receive loop started")
        
        while self.running:
            try:
                self.udp_socket.settimeout(1.0)
                data, address = self.udp_socket.recvfrom(65536)
                
                # Parse UDP packet
                packet = UDPPacket.unpack(data)
                if packet:
                    self._process_udp_packet(packet, address)
                else:
                    logger.warning("Received invalid UDP packet")
            
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"UDP receive error: {e}")
        
        logger.info("UDP receive loop stopped")
    
    def _process_udp_packet(self, packet: 'UDPPacket', sender_address: tuple):
        """Process received UDP media packet."""
        try:
            # Determine stream type from stream_id
            stream_type = packet.stream_id & 0x0F  # Lower 4 bits
            
            # Find the sender username by matching stream_id
            sender_username = self._identify_sender_from_stream_id(packet.stream_id)
            
            if sender_username:
                if stream_type == 0x01:  # Audio stream
                    logger.info(f"Received audio packet from {sender_username}: seq={packet.seq_num}, size={len(packet.payload)}")
                    self.audio_data_received.emit(sender_username, packet.payload)
                elif stream_type == 0x02:  # Video stream
                    logger.info(f"Received video packet from {sender_username}: seq={packet.seq_num}, size={len(packet.payload)}")
                    self.video_data_received.emit(sender_username, packet.payload)
                else:
                    logger.warning(f"Unknown stream type: {stream_type}")
            else:
                logger.warning(f"Could not identify sender for stream_id {packet.stream_id}")
                
        except Exception as e:
            logger.error(f"Error processing UDP packet: {e}")
    
    def _identify_sender_from_stream_id(self, stream_id: int) -> str:
        """
        Identify the sender username from a stream ID.
        
        Args:
            stream_id: The stream ID from the UDP packet
            
        Returns:
            Username of the sender, or None if not found
        """
        # Extract stream type
        stream_type_value = stream_id & 0x0F
        
        # Check all known users (including self) to find matching stream ID
        all_users = list(self.session_state['user_list']) + [self.username]
        
        for username in all_users:
            # Generate expected stream IDs for this user
            from utils.network_proto import StreamType, generate_stream_id
            
            if stream_type_value == StreamType.AUDIO.value:
                expected_stream_id = generate_stream_id(username, StreamType.AUDIO)
            elif stream_type_value == StreamType.VIDEO.value:
                expected_stream_id = generate_stream_id(username, StreamType.VIDEO)
            else:
                continue
            
            if expected_stream_id == stream_id:
                return username
        
        return None
    
    def send_audio_packet(self, audio_data: bytes):
        """
        Send an audio packet via UDP with network quality monitoring.
        
        Args:
            audio_data: Encoded audio data
        """
        if not self.running:
            return
        
        # Check network quality before sending
        if self.connection_quality < 0.3:  # Poor network quality
            logger.debug("Skipping audio packet due to poor network quality")
            self._handle_media_degradation('audio')
            return
        
        try:
            packet = UDPPacket(
                stream_id=self.audio_stream_id,
                seq_num=self.audio_seq_num,
                timestamp=int(time.time() * 1_000_000),  # microseconds
                payload=audio_data
            )
            self.audio_seq_num += 1
            
            packed_data = packet.pack()
            self.udp_socket.sendto(packed_data, (self.server_address, self.udp_port))
            logger.info(f"Sent audio packet: seq={packet.seq_num}, size={len(audio_data)}")
            
            # Reset media error count on successful send
            if hasattr(self, 'audio_error_count'):
                self.audio_error_count = 0
        
        except Exception as e:
            logger.error(f"Failed to send audio packet: {e}")
            self._handle_media_send_error('audio', e)
    
    def _send_udp_hello(self):
        """Send a UDP hello packet to let server learn our UDP address."""
        try:
            # Create a special hello packet with a known stream ID
            hello_packet = UDPPacket(
                stream_id=0,  # Special stream ID for hello packets
                seq_num=0,
                timestamp=int(time.time() * 1_000_000),
                payload=f"HELLO:{self.username}".encode('utf-8')
            )
            
            packed_data = hello_packet.pack()
            self.udp_socket.sendto(packed_data, (self.server_address, self.udp_port))
            logger.info(f"Sent UDP hello packet to server")
            
        except Exception as e:
            logger.error(f"Failed to send UDP hello packet: {e}")
    
    def send_video_packet(self, video_data: bytes):
        """
        Send a video packet via UDP with network quality monitoring.
        
        Args:
            video_data: Encoded video frame data
        """
        if not self.running:
            return
        
        # Check network quality before sending
        if self.connection_quality < 0.5:  # Poor network quality for video
            logger.debug("Skipping video packet due to poor network quality")
            self._handle_media_degradation('video')
            return
        
        try:
            packet = UDPPacket(
                stream_id=self.video_stream_id,
                seq_num=self.video_seq_num,
                timestamp=int(time.time() * 1_000_000),
                payload=video_data
            )
            self.video_seq_num += 1
            
            packed_data = packet.pack()
            self.udp_socket.sendto(packed_data, (self.server_address, self.udp_port))
            logger.debug(f"Sent video packet: seq={packet.seq_num}, size={len(video_data)}")
            
            # Reset media error count on successful send
            if hasattr(self, 'video_error_count'):
                self.video_error_count = 0
        
        except Exception as e:
            logger.error(f"Failed to send video packet: {e}")
            self._handle_media_send_error('video', e)
    
    # ========================================================================
    # Heartbeat
    # ========================================================================
    
    def _heartbeat_loop(self):
        """Send periodic heartbeat pings to server."""
        logger.info("Heartbeat loop started")
        
        HEARTBEAT_INTERVAL = 20  # seconds
        HEARTBEAT_TIMEOUT = 60  # seconds
        
        while self.running:
            time.sleep(HEARTBEAT_INTERVAL)
            
            if self.authenticated:
                try:
                    # Check if we've received a recent pong
                    time_since_pong = time.time() - self.last_heartbeat_response
                    
                    if time_since_pong > HEARTBEAT_TIMEOUT:
                        # Connection appears to be lost
                        logger.warning(f"Heartbeat timeout: {time_since_pong:.1f}s since last pong")
                        self.connection_quality = max(0.0, 1.0 - (time_since_pong - HEARTBEAT_TIMEOUT) / HEARTBEAT_TIMEOUT)
                        
                        if time_since_pong > HEARTBEAT_TIMEOUT * 1.5:
                            # Connection is definitely lost - trigger reconnection
                            logger.error("Connection lost - heartbeat timeout exceeded")
                            if not self.manual_disconnect and not self.reconnection_in_progress:
                                self._handle_connection_lost()
                            break
                    
                    # Send ping
                    ping = create_message(MessageType.PING, username=self.username)
                    self._send_tcp_message(ping)
                    logger.debug("Sent heartbeat ping")
                    
                except Exception as e:
                    logger.error(f"Failed to send heartbeat: {e}")
                    self.connection_quality = max(0.0, self.connection_quality - 0.1)
                    
                    if self.connection_quality <= 0.0:
                        logger.error("Connection quality degraded to zero")
                        if not self.manual_disconnect and not self.reconnection_in_progress:
                            self._handle_connection_lost()
                        break
        
        logger.info("Heartbeat loop stopped")
    
    def _handle_connection_lost(self):
        """Handle connection loss with enhanced reconnection strategy."""
        if self.manual_disconnect or self.reconnection_in_progress:
            return
            
        logger.warning("Handling connection loss...")
        self.running = False
        self.authenticated = False
        
        # Don't attempt reconnection if manually disconnected
        if self.manual_disconnect:
            self.disconnected.emit()
            return
        
        # Attempt automatic reconnection with exponential backoff
        if self.reconnect_attempts < self.max_reconnect_attempts:
            self._attempt_reconnection()
        else:
            logger.error("Max reconnection attempts reached - requiring manual retry")
            self.manual_retry_required.emit()
    
    def _attempt_reconnection(self):
        """Attempt to reconnect with exponential backoff strategy (1s, 2s, 4s, 8s, max 30s)."""
        if self.reconnection_in_progress:
            return
            
        self.reconnection_in_progress = True
        self.reconnect_attempts += 1
        
        # Exponential backoff: 1s, 2s, 4s, 8s, then cap at 30s
        if self.reconnect_attempts == 1:
            delay = 1
        elif self.reconnect_attempts == 2:
            delay = 2
        elif self.reconnect_attempts == 3:
            delay = 4
        elif self.reconnect_attempts == 4:
            delay = 8
        else:
            delay = 30  # Max 30 seconds for subsequent attempts
        
        logger.info(f"Attempting reconnection {self.reconnect_attempts}/{self.max_reconnect_attempts} in {delay}s...")
        self.reconnection_started.emit(self.reconnect_attempts, self.max_reconnect_attempts)
        
        # Start reconnection in background thread
        reconnect_thread = threading.Thread(
            target=self._reconnect_after_delay,
            args=(delay,),
            daemon=True
        )
        reconnect_thread.start()
    
    def _reconnect_after_delay(self, delay: float):
        """Reconnect after specified delay with session state preservation."""
        time.sleep(delay)
        
        logger.info("Attempting to reconnect...")
        
        try:
            # Notify media manager about network interruption
            if hasattr(self, 'media_manager') and self.media_manager:
                self.media_manager.handle_network_interruption()
            
            # Close existing sockets cleanly
            self._cleanup_sockets()
            
            # Reset connection state but preserve session state
            self.tcp_socket = None
            self.udp_socket = None
            self.connection_quality = 1.0
            self.last_heartbeat_response = time.time()
            
            # Attempt reconnection
            if self.connect():
                logger.info("Reconnection successful - restoring session state")
                self._restore_session_state()
                
                # Notify media manager about network recovery
                if hasattr(self, 'media_manager') and self.media_manager:
                    # Use a timer to delay recovery slightly to ensure connection is stable
                    import threading
                    recovery_timer = threading.Timer(2.0, self.media_manager.handle_network_recovery)
                    recovery_timer.start()
                
                self.reconnect_attempts = 0  # Reset counter on success
                self.reconnection_in_progress = False
                self.reconnection_succeeded.emit()
            else:
                logger.warning(f"Reconnection attempt {self.reconnect_attempts} failed")
                self.reconnection_in_progress = False
                self.reconnection_failed.emit(f"Attempt {self.reconnect_attempts} failed")
                self._handle_connection_lost()  # Try again or give up
                
        except Exception as e:
            logger.error(f"Reconnection error: {e}")
            self.reconnection_in_progress = False
            self.reconnection_failed.emit(str(e))
            self._handle_connection_lost()
    
    def _cleanup_sockets(self):
        """Clean up existing socket connections."""
        if self.tcp_socket:
            try:
                self.tcp_socket.close()
            except Exception as e:
                logger.debug(f"Error closing TCP socket: {e}")
        
        if self.udp_socket:
            try:
                self.udp_socket.close()
            except Exception as e:
                logger.debug(f"Error closing UDP socket: {e}")
    
    def _restore_session_state(self):
        """Restore session state after successful reconnection."""
        try:
            # Request current user list to sync state
            if self.authenticated:
                # The server will send user list automatically after auth
                logger.info("Session state will be restored via server updates")
                
                # Restore media state if needed
                media_state = self.session_state.get('media_state', {})
                if media_state.get('audio_active'):
                    logger.info("Audio was active before disconnect - attempting to restart")
                    self._restore_media_stream('audio')
                if media_state.get('video_active'):
                    logger.info("Video was active before disconnect - attempting to restart")
                    self._restore_media_stream('video')
                if media_state.get('screen_sharing'):
                    logger.info("Screen sharing was active before disconnect - attempting to restart")
                    self._restore_media_stream('screen_share')
                
                # Restore file transfers
                self._restore_file_transfers()
                    
        except Exception as e:
            logger.error(f"Error restoring session state: {e}")
    
    def _restore_media_stream(self, stream_type: str):
        """
        Restore media stream after reconnection.
        
        Args:
            stream_type: Type of stream ('audio', 'video', 'screen_share')
        """
        try:
            # Import here to avoid circular imports
            from utils.error_manager import error_manager, ErrorCategory, ErrorSeverity
            
            # Check if we have a media capture manager
            if hasattr(self, 'media_manager') and self.media_manager:
                if stream_type == 'audio':
                    success = self.media_manager.start_audio()
                    if success:
                        logger.info("Audio stream restored successfully after reconnection")
                    else:
                        logger.warning("Failed to restore audio stream after reconnection")
                        error_manager.report_error(
                            ErrorCategory.MEDIA,
                            'stream_restore_failed',
                            ErrorSeverity.WARNING,
                            'audio',
                            'Audio stream could not be restored after reconnection'
                        )
                        # Clear the state since restoration failed
                        self.session_state['media_state']['audio_active'] = False
                
                elif stream_type == 'video':
                    success = self.media_manager.start_video()
                    if success:
                        logger.info("Video stream restored successfully after reconnection")
                    else:
                        logger.warning("Failed to restore video stream after reconnection")
                        error_manager.report_error(
                            ErrorCategory.MEDIA,
                            'stream_restore_failed',
                            ErrorSeverity.WARNING,
                            'video',
                            'Video stream could not be restored after reconnection'
                        )
                        # Clear the state since restoration failed
                        self.session_state['media_state']['video_active'] = False
                
                elif stream_type == 'screen_share':
                    success = self.media_manager.start_screen_share()
                    if success:
                        logger.info("Screen sharing restored successfully after reconnection")
                    else:
                        logger.warning("Failed to restore screen sharing after reconnection")
                        error_manager.report_error(
                            ErrorCategory.MEDIA,
                            'stream_restore_failed',
                            ErrorSeverity.WARNING,
                            'screen_share',
                            'Screen sharing could not be restored after reconnection'
                        )
                        # Clear the state since restoration failed
                        self.session_state['media_state']['screen_sharing'] = False
            else:
                logger.warning(f"No media manager available to restore {stream_type} stream")
                
        except Exception as e:
            logger.error(f"Error restoring {stream_type} stream: {e}")
    
    def _restore_file_transfers(self):
        """Restore file transfers after reconnection."""
        try:
            if hasattr(self, 'file_transfer_manager') and self.file_transfer_manager:
                # Get active transfers from session state
                active_uploads = self.session_state.get('active_uploads', {})
                active_downloads = self.session_state.get('active_downloads', {})
                
                # Resume uploads
                for file_id, transfer_info in active_uploads.items():
                    logger.info(f"Attempting to resume upload: {transfer_info.get('filename', file_id)}")
                    self.file_transfer_manager.resume_upload(file_id, transfer_info)
                
                # Resume downloads
                for file_id, transfer_info in active_downloads.items():
                    logger.info(f"Attempting to resume download: {transfer_info.get('filename', file_id)}")
                    self.file_transfer_manager.resume_download(file_id, transfer_info)
                    
        except Exception as e:
            logger.error(f"Error restoring file transfers: {e}")
    
    def manual_reconnect(self):
        """Manually trigger reconnection attempt (for GUI retry button)."""
        logger.info("Manual reconnection requested")
        self.reconnect_attempts = 0  # Reset attempts for manual retry
        self.manual_disconnect = False
        self.reconnection_in_progress = False
        self._attempt_reconnection()
    
    def reset_reconnection_state(self):
        """Reset reconnection state (called when user manually disconnects)."""
        self.reconnect_attempts = 0
        self.reconnection_in_progress = False
        self.manual_disconnect = True
    
    def get_connection_quality(self) -> float:
        """Get current connection quality (0.0 to 1.0)."""
        return self.connection_quality
    
    def set_media_state(self, audio_active: bool = None, video_active: bool = None, screen_sharing: bool = None):
        """Update media state for session preservation."""
        if audio_active is not None:
            self.session_state['media_state']['audio_active'] = audio_active
        if video_active is not None:
            self.session_state['media_state']['video_active'] = video_active
        if screen_sharing is not None:
            self.session_state['media_state']['screen_sharing'] = screen_sharing
    
    def get_session_state(self) -> dict:
        """Get current session state for debugging/monitoring."""
        return self.session_state.copy()
    
    def set_app_reference(self, app):
        """Set reference to the main app for GUI updates."""
        self.app = app
    
    def update_self_video_frame(self, frame_data: bytes):
        """Update self video frame in GUI."""
        if hasattr(self, 'app') and self.app:
            self.app.update_self_video_frame(frame_data)
    
    def is_reconnecting(self) -> bool:
        """Check if reconnection is currently in progress."""
        return self.reconnection_in_progress
    
    def _handle_media_send_error(self, media_type: str, error: Exception):
        """
        Handle media packet send errors with retry logic.
        
        Args:
            media_type: Type of media ('audio' or 'video')
            error: The exception that occurred
        """
        try:
            from utils.error_manager import error_manager, ErrorCategory, ErrorSeverity
            
            # Track error count for this media type
            error_count_attr = f'{media_type}_error_count'
            if not hasattr(self, error_count_attr):
                setattr(self, error_count_attr, 0)
            
            error_count = getattr(self, error_count_attr) + 1
            setattr(self, error_count_attr, error_count)
            
            # Degrade connection quality
            self.connection_quality = max(0.0, self.connection_quality - 0.1)
            
            if error_count >= 5:  # After 5 consecutive errors
                logger.warning(f"{media_type.title()} stream experiencing persistent errors - attempting recovery")
                
                # Report error
                error_manager.report_error(
                    ErrorCategory.MEDIA,
                    'stream_transmission_error',
                    ErrorSeverity.WARNING,
                    media_type,
                    f"Persistent {media_type} transmission errors: {str(error)}"
                )
                
                # Attempt to restart the media stream
                self._attempt_media_recovery(media_type)
                
                # Reset error count after recovery attempt
                setattr(self, error_count_attr, 0)
                
        except Exception as e:
            logger.error(f"Error handling media send error: {e}")
    
    def _handle_media_degradation(self, media_type: str):
        """
        Handle media degradation due to poor network quality.
        
        Args:
            media_type: Type of media ('audio' or 'video')
        """
        try:
            from utils.error_manager import error_manager, ErrorCategory, ErrorSeverity
            
            # Track degradation events
            degradation_attr = f'{media_type}_degradation_count'
            if not hasattr(self, degradation_attr):
                setattr(self, degradation_attr, 0)
            
            degradation_count = getattr(self, degradation_attr) + 1
            setattr(self, degradation_attr, degradation_count)
            
            # Report degradation after multiple events
            if degradation_count % 10 == 0:  # Every 10 degradation events
                error_manager.report_error(
                    ErrorCategory.NETWORK,
                    'media_quality_degraded',
                    ErrorSeverity.INFO,
                    media_type,
                    f"{media_type.title()} quality degraded due to poor network conditions"
                )
                
        except Exception as e:
            logger.error(f"Error handling media degradation: {e}")
    
    def _attempt_media_recovery(self, media_type: str):
        """
        Attempt to recover a media stream after errors.
        
        Args:
            media_type: Type of media ('audio', 'video', or 'screen_share')
        """
        try:
            logger.info(f"Attempting {media_type} stream recovery...")
            
            if hasattr(self, 'media_manager') and self.media_manager:
                # Stop and restart the media stream
                if media_type == 'audio':
                    self.media_manager.stop_audio()
                    time.sleep(0.5)  # Brief pause
                    success = self.media_manager.start_audio()
                elif media_type == 'video':
                    self.media_manager.stop_video()
                    time.sleep(0.5)
                    success = self.media_manager.start_video()
                elif media_type == 'screen_share':
                    self.media_manager.stop_screen_share()
                    time.sleep(0.5)
                    success = self.media_manager.start_screen_share()
                else:
                    success = False
                
                if success:
                    logger.info(f"{media_type.title()} stream recovery successful")
                    # Reset sequence numbers to avoid confusion
                    if media_type == 'audio':
                        self.audio_seq_num = 0
                    elif media_type == 'video':
                        self.video_seq_num = 0
                else:
                    logger.warning(f"{media_type.title()} stream recovery failed")
            else:
                logger.warning(f"No media manager available for {media_type} recovery")
                
        except Exception as e:
            logger.error(f"Error during {media_type} stream recovery: {e}")
    
    def get_network_quality(self) -> float:
        """Get current network quality (0.0 to 1.0)."""
        return self.connection_quality
    
    def set_media_manager(self, media_manager):
        """Set the media manager for stream recovery."""
        self.media_manager = media_manager


# ============================================================================
# Media Capture Stubs (Placeholders for Production)
# ============================================================================

class MediaCaptureStub:
    """
    Placeholder for media capture functionality.
    
    In production, this would:
    - Capture audio from microphone using sounddevice/pyaudio
    - Capture video from webcam using opencv-python
    - Encode media using appropriate codecs
    - Send packets via LANClient
    """
    
    def __init__(self, client: LANClient):
        self.client = client
        self.audio_active = False
        self.video_active = False
        logger.info("MediaCaptureStub initialized")
    
    def start_audio(self):
        """Start audio capture (placeholder)."""
        logger.info("Starting audio capture (stub)")
        self.audio_active = True
        # TODO: Implement real audio capture
        # - Open audio input device
        # - Capture frames in callback
        # - Encode (e.g., Opus codec)
        # - Call self.client.send_audio_packet(encoded_data)
    
    def stop_audio(self):
        """Stop audio capture (placeholder)."""
        logger.info("Stopping audio capture (stub)")
        self.audio_active = False
        # TODO: Close audio device
    
    def start_video(self):
        """Start video capture (placeholder)."""
        logger.info("Starting video capture (stub)")
        self.video_active = True
        # TODO: Implement real video capture
        # - Open webcam with cv2.VideoCapture()
        # - Capture frames in loop
        # - Encode (e.g., H.264 codec)
        # - Call self.client.send_video_packet(encoded_frame)
    
    def stop_video(self):
        """Stop video capture (placeholder)."""
        logger.info("Stopping video capture (stub)")
        self.video_active = False
        # TODO: Release webcam