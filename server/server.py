"""
Server networking for LAN Communication Application.

Multi-client TCP server for control channel and UDP relay for media streams.
Manages sessions, user connections, message routing, and stream forwarding.
"""

import socket
import threading
import json
import time
from typing import Dict, Set, Optional
from utils.logger import setup_logger
from utils.config import config, DEFAULT_TCP_PORT, DEFAULT_UDP_PORT, BUFFER_SIZE
from utils.network_proto import (
    MessageType, serialize_message, deserialize_message,
    create_message, UDPPacket
)
from utils.file_transfer import ServerFileManager

logger = setup_logger(__name__)

class ClientConnection:
    """Represents a connected client."""
    
    def __init__(self, socket: socket.socket, address: tuple, username: str):
        self.socket = socket
        self.address = address
        self.username = username
        self.udp_address = None  # Will be set when UDP packets arrive
        self.connected = True
        self.last_heartbeat = time.time()

class LANServer:
    """
    LAN Communication Server.
    
    Responsibilities:
    - Accept TCP connections for control channel
    - Maintain user session and presence
    - Route chat messages, file metadata, and control commands
    - Relay UDP audio/video streams between clients
    - Mix audio streams (placeholder for production)
    """
    
    def __init__(self, session_id: str, host_username: str, 
                 tcp_port: int = None, udp_port: int = None):
        """
        Initialize server.
        
        Args:
            session_id: Unique session identifier
            host_username: Username of the host
            tcp_port: TCP port for control channel (default from config)
            udp_port: UDP port for media streams (default from config)
        """
        self.session_id = session_id
        self.host_username = host_username
        self.tcp_port = tcp_port or config.get('network.tcp_port', DEFAULT_TCP_PORT)
        self.udp_port = udp_port or config.get('network.udp_port', DEFAULT_UDP_PORT)
        
        # Client management
        self.clients: Dict[str, ClientConnection] = {}  # username -> ClientConnection
        self.clients_lock = threading.Lock()
        
        # Server sockets
        self.tcp_socket: Optional[socket.socket] = None
        self.udp_socket: Optional[socket.socket] = None
        
        # Server state
        self.running = False
        self.threads: Set[threading.Thread] = set()
        
        # File manager
        self.file_manager = ServerFileManager()
        
        logger.info(f"Server initialized: session_id={session_id}, host={host_username}")
    
    def start(self):
        """Start the server (TCP and UDP listeners)."""
        try:
            # Create and bind TCP socket
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.tcp_socket.bind(('0.0.0.0', self.tcp_port))
            self.tcp_socket.listen(10)
            logger.info(f"TCP server listening on port {self.tcp_port}")
            
            # Create and bind UDP socket
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.bind(('0.0.0.0', self.udp_port))
            logger.info(f"UDP server listening on port {self.udp_port}")
            
            self.running = True
            
            # Start TCP accept thread
            tcp_thread = threading.Thread(target=self._tcp_accept_loop, daemon=True)
            tcp_thread.start()
            self.threads.add(tcp_thread)
            
            # Start UDP receive thread
            udp_thread = threading.Thread(target=self._udp_receive_loop, daemon=True)
            udp_thread.start()
            self.threads.add(udp_thread)
            
            # Start heartbeat thread
            heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
            heartbeat_thread.start()
            self.threads.add(heartbeat_thread)
            
            logger.info("Server started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            self.stop()
            raise
    
    def stop(self):
        """Stop the server and close all connections."""
        logger.info("Stopping server...")
        self.running = False
        
        # Close all client connections
        with self.clients_lock:
            for username, client in list(self.clients.items()):
                try:
                    client.socket.close()
                except:
                    pass
            self.clients.clear()
        
        # Close server sockets
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
        
        # Clean up files
        if self.file_manager:
            self.file_manager.cleanup_session_files()
        
        logger.info("Server stopped")
    
    # ========================================================================
    # TCP Control Channel
    # ========================================================================
    
    def _tcp_accept_loop(self):
        """Accept incoming TCP connections."""
        logger.info("TCP accept loop started")
        
        while self.running:
            try:
                self.tcp_socket.settimeout(1.0)
                client_socket, address = self.tcp_socket.accept()
                logger.info(f"New TCP connection from {address}")
                
                # Handle client in new thread
                client_thread = threading.Thread(
                    target=self._handle_tcp_client,
                    args=(client_socket, address),
                    daemon=True
                )
                client_thread.start()
                self.threads.add(client_thread)
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"TCP accept error: {e}")
        
        logger.info("TCP accept loop stopped")
    
    def _handle_tcp_client(self, client_socket: socket.socket, address: tuple):
        """
        Handle a TCP client connection.
        
        Expects authentication as first message, then processes control messages.
        """
        username = None
        buffer = b''
        
        try:
            while self.running:
                # Receive data
                data = client_socket.recv(BUFFER_SIZE)
                if not data:
                    logger.info(f"Client {address} disconnected")
                    break
                
                buffer += data
                
                # Try to deserialize messages from buffer
                while len(buffer) >= 4:
                    # Check if we have a complete message (4-byte length prefix)
                    import struct
                    msg_length = struct.unpack(">I", buffer[:4])[0]
                    
                    if len(buffer) < 4 + msg_length:
                        break  # Wait for more data
                    
                    # Extract message
                    message_data = buffer[4:4+msg_length]
                    buffer = buffer[4+msg_length:]
                    
                    # Deserialize and handle
                    try:
                        message = json.loads(message_data.decode('utf-8'))
                        username = self._handle_control_message(
                            message, client_socket, address, username
                        )
                    except Exception as e:
                        logger.error(f"Error handling message: {e}")
        
        except Exception as e:
            logger.error(f"TCP client handler error: {e}")
        
        finally:
            # Clean up client
            if username:
                self._remove_client(username)
            try:
                client_socket.close()
            except:
                pass
    
    def _handle_control_message(self, message: dict, client_socket: socket.socket,
                                address: tuple, current_username: Optional[str]) -> Optional[str]:
        """
        Handle a control channel message.
        
        Returns the username if this is an auth request, otherwise returns current_username.
        """
        msg_type = message.get('type')
        logger.debug(f"Received message type: {msg_type}")
        
        # Authentication
        if msg_type == MessageType.AUTH_REQUEST.value:
            username = message.get('username')
            session_id = message.get('session_id')
            
            if session_id != self.session_id:
                # Invalid session ID
                response = create_message(
                    MessageType.AUTH_RESPONSE,
                    success=False,
                    reason="Invalid session ID"
                )
                self._send_tcp_message(client_socket, response)
                return None
            
            # Add client
            with self.clients_lock:
                if username in self.clients:
                    # Username already taken
                    response = create_message(
                        MessageType.AUTH_RESPONSE,
                        success=False,
                        reason="Username already in use"
                    )
                    self._send_tcp_message(client_socket, response)
                    return None
                
                client = ClientConnection(client_socket, address, username)
                self.clients[username] = client
            
            # Send success response
            response = create_message(
                MessageType.AUTH_RESPONSE,
                success=True,
                username=username
            )
            self._send_tcp_message(client_socket, response)
            
            # Notify all clients of new user
            user_joined_msg = create_message(
                MessageType.USER_JOINED,
                username=username
            )
            self._broadcast_message(user_joined_msg)
            
            # Send user list to new client
            user_list = [u for u in self.clients.keys()]
            user_list_msg = create_message(
                MessageType.USER_LIST,
                users=user_list
            )
            self._send_tcp_message(client_socket, user_list_msg)
            
            logger.info(f"User '{username}' authenticated and joined session")
            return username
        
        # Chat message
        elif msg_type == MessageType.CHAT_MESSAGE.value:
            from_user = message.get('from_user')
            mode = message.get('mode', 'broadcast')
            to_users = message.get('to_users', [])
            
            # Route message based on mode
            if mode == 'broadcast':
                self._broadcast_message(message, exclude=from_user)
            elif mode == 'multicast':
                self._multicast_message(message, to_users)
            elif mode == 'unicast' and to_users:
                self._unicast_message(message, to_users[0])
            
            logger.info(f"Chat message from '{from_user}' in {mode} mode")
        
        # File offer
        elif msg_type == MessageType.FILE_OFFER.value:
            from_user = message.get('from_user')
            file_id = message.get('file_id')
            filename = message.get('filename')
            file_size = message.get('file_size')
            mode = message.get('mode', 'broadcast')
            to_users = message.get('to_users', [])
            
            # Handle file offer in file manager
            if file_id and filename and file_size:
                # Calculate checksum placeholder (will be provided with chunks)
                self.file_manager.handle_file_offer(file_id, filename, file_size, "", from_user)
            
            # Route file offer to other clients
            if mode == 'broadcast':
                self._broadcast_message(message, exclude=from_user)
            elif mode == 'multicast':
                self._multicast_message(message, to_users)
            elif mode == 'unicast' and to_users:
                self._unicast_message(message, to_users[0])
            
            logger.info(f"File offer from '{from_user}': {filename}")
        
        # File chunk
        elif msg_type == "file_chunk":
            file_id = message.get('file_id')
            chunk_index = message.get('chunk_index')
            chunk_data_hex = message.get('data')
            checksum = message.get('checksum')
            
            if file_id and chunk_index is not None and chunk_data_hex:
                try:
                    # Convert hex string back to bytes
                    chunk_data = bytes.fromhex(chunk_data_hex)
                    
                    # Handle chunk in file manager
                    success = self.file_manager.handle_file_chunk(file_id, chunk_index, chunk_data)
                    
                    if success:
                        logger.debug(f"Processed file chunk {chunk_index} for {file_id}")
                    else:
                        logger.warning(f"Failed to process file chunk {chunk_index} for {file_id}")
                        
                except Exception as e:
                    logger.error(f"Error processing file chunk: {e}")
        
        # File request (download)
        elif msg_type == "file_request":
            file_id = message.get('file_id')
            from_user = message.get('from_user')
            
            if file_id and from_user:
                # Check if file is available
                file_path = self.file_manager.get_file_path(file_id)
                if file_path:
                    # Send file to requesting user
                    self._send_file_to_user(file_id, from_user)
                else:
                    # Send error response
                    error_msg = create_message(
                        MessageType.ERROR,
                        error_code="FILE_NOT_FOUND",
                        message=f"File {file_id} not found"
                    )
                    with self.clients_lock:
                        if from_user in self.clients:
                            self._send_tcp_message(self.clients[from_user].socket, error_msg)
        
        # File complete
        elif msg_type == "file_complete":
            file_id = message.get('file_id')
            logger.info(f"File upload completed: {file_id}")
            
            # Broadcast file list update to all clients
            available_files = self.file_manager.get_available_files()
            file_list_msg = create_message(
                MessageType.FILE_LIST,
                files=[
                    {
                        "file_id": fid,
                        "filename": info.filename,
                        "size": info.file_size,
                        "owner": info.uploader
                    }
                    for fid, info in available_files.items()
                ]
            )
            self._broadcast_message(file_list_msg)
        
        # Ping/Pong (heartbeat)
        elif msg_type == MessageType.PING.value:
            if current_username and current_username in self.clients:
                self.clients[current_username].last_heartbeat = time.time()
            
            # Send pong
            pong = create_message(MessageType.PONG)
            self._send_tcp_message(client_socket, pong)
        
        # Screen frame
        elif msg_type == "screen_frame":
            from_user = message.get('from_user')
            
            # Relay screen frame to all other clients
            self._broadcast_message(message, exclude=from_user)
            logger.debug(f"Relayed screen frame from {from_user}")
        
        # Leave session
        elif msg_type == MessageType.LEAVE_SESSION.value:
            username_leaving = message.get('username', current_username)
            logger.info(f"User '{username_leaving}' leaving session")
            return None  # This will trigger cleanup
        
        return current_username
    
    def _send_tcp_message(self, client_socket: socket.socket, message: dict):
        """Send a TCP message to a specific client."""
        try:
            serialized = serialize_message(message)
            client_socket.sendall(serialized)
        except Exception as e:
            logger.error(f"Failed to send TCP message: {e}")
    
    def _broadcast_message(self, message: dict, exclude: str = None):
        """Broadcast a message to all connected clients."""
        with self.clients_lock:
            for username, client in self.clients.items():
                if username == exclude:
                    continue
                try:
                    self._send_tcp_message(client.socket, message)
                except Exception as e:
                    logger.error(f"Failed to broadcast to '{username}': {e}")
    
    def _multicast_message(self, message: dict, target_users: list):
        """Send message to specific list of users."""
        with self.clients_lock:
            for username in target_users:
                if username in self.clients:
                    try:
                        self._send_tcp_message(self.clients[username].socket, message)
                    except Exception as e:
                        logger.error(f"Failed to multicast to '{username}': {e}")
    
    def _unicast_message(self, message: dict, target_user: str):
        """Send message to a single user."""
        with self.clients_lock:
            if target_user in self.clients:
                try:
                    self._send_tcp_message(self.clients[target_user].socket, message)
                except Exception as e:
                    logger.error(f"Failed to unicast to '{target_user}': {e}")
    
    def _remove_client(self, username: str):
        """Remove a client and notify others."""
        with self.clients_lock:
            if username in self.clients:
                del self.clients[username]
                logger.info(f"Removed client '{username}'")
        
        # Notify others
        user_left_msg = create_message(
            MessageType.USER_LEFT,
            username=username
        )
        self._broadcast_message(user_left_msg)
    
    # ========================================================================
    # UDP Media Stream Relay
    # ========================================================================
    
    def _udp_receive_loop(self):
        """Receive and relay UDP media packets."""
        logger.info("UDP receive loop started")
        
        while self.running:
            try:
                self.udp_socket.settimeout(1.0)
                data, address = self.udp_socket.recvfrom(65536)
                
                # Try to parse UDP packet
                packet = UDPPacket.unpack(data)
                if packet:
                    # TODO: Identify sender by stream_id or address
                    # For now, relay to all other clients
                    self._relay_udp_packet(data, address)
                else:
                    logger.warning(f"Received invalid UDP packet from {address}")
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"UDP receive error: {e}")
        
        logger.info("UDP receive loop stopped")
    
    def _relay_udp_packet(self, packet_data: bytes, sender_address: tuple):
        """
        Relay UDP packet to all clients except sender.
        
        In production, this would:
        - Identify the sender
        - Mix audio streams if needed
        - Transcode video if needed
        - Apply bandwidth management
        """
        # TODO: Implement proper sender identification and selective relay
        # For now, broadcast to all clients with UDP addresses
        
        with self.clients_lock:
            for username, client in self.clients.items():
                if client.udp_address and client.udp_address != sender_address:
                    try:
                        self.udp_socket.sendto(packet_data, client.udp_address)
                    except Exception as e:
                        logger.error(f"Failed to relay UDP to '{username}': {e}")
    
    # ========================================================================
    # Heartbeat and Connection Monitoring
    # ========================================================================
    
    def _heartbeat_loop(self):
        """Monitor client connections via heartbeat."""
        logger.info("Heartbeat loop started")
        
        HEARTBEAT_INTERVAL = 30  # seconds
        HEARTBEAT_TIMEOUT = 90  # seconds
        
        while self.running:
            time.sleep(HEARTBEAT_INTERVAL)
            
            current_time = time.time()
            disconnected_users = []
            
            with self.clients_lock:
                for username, client in self.clients.items():
                    if current_time - client.last_heartbeat > HEARTBEAT_TIMEOUT:
                        disconnected_users.append(username)
                        logger.warning(f"Client '{username}' heartbeat timeout")
            
            # Remove disconnected clients
            for username in disconnected_users:
                self._remove_client(username)
        
        logger.info("Heartbeat loop stopped")
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    def get_connected_users(self) -> list:
        """Get list of connected usernames."""
        with self.clients_lock:
            return list(self.clients.keys())
    
    def get_client_count(self) -> int:
        """Get number of connected clients."""
        with self.clients_lock:
            return len(self.clients)
    
    def _send_file_to_user(self, file_id: str, username: str):
        """Send file chunks to a specific user."""
        try:
            file_path = self.file_manager.get_file_path(file_id)
            if not file_path or not file_path.exists():
                logger.error(f"File not found for download: {file_id}")
                return
            
            # Get file info
            available_files = self.file_manager.get_available_files()
            if file_id not in available_files:
                logger.error(f"File info not found: {file_id}")
                return
            
            file_info = available_files[file_id]
            
            # Send file in chunks
            chunk_size = 65536  # 64KB chunks
            total_chunks = (file_info.file_size + chunk_size - 1) // chunk_size
            
            with open(file_path, 'rb') as f:
                for chunk_index in range(total_chunks):
                    chunk_data = f.read(chunk_size)
                    if not chunk_data:
                        break
                    
                    # Send chunk to user
                    chunk_msg = create_message(
                        "file_chunk",
                        file_id=file_id,
                        chunk_index=chunk_index,
                        total_chunks=total_chunks,
                        data=chunk_data.hex(),
                        checksum=file_info.checksum
                    )
                    
                    with self.clients_lock:
                        if username in self.clients:
                            self._send_tcp_message(self.clients[username].socket, chunk_msg)
                        else:
                            logger.warning(f"User {username} not found for file download")
                            return
                    
                    # Small delay to prevent overwhelming
                    time.sleep(0.01)
            
            # Send completion message
            complete_msg = create_message(
                "file_complete",
                file_id=file_id,
                checksum=file_info.checksum
            )
            
            with self.clients_lock:
                if username in self.clients:
                    self._send_tcp_message(self.clients[username].socket, complete_msg)
            
            logger.info(f"File sent to {username}: {file_info.filename}")
            
        except Exception as e:
            logger.error(f"Error sending file to user: {e}")


# ============================================================================
# Standalone Server Runner (for testing)
# ============================================================================

def run_server_standalone(session_id: str = "TEST123", host_username: str = "server_host"):
    """
    Run server in standalone mode for testing.
    
    Args:
        session_id: Session ID for this server instance
        host_username: Username of the host
    """
    logger.info(f"Starting standalone server: session={session_id}, host={host_username}")
    
    server = LANServer(session_id, host_username)
    
    try:
        server.start()
        
        # Keep server running
        logger.info("Server is running. Press Ctrl+C to stop.")
        while server.running:
            time.sleep(1)
    
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    
    finally:
        server.stop()
        logger.info("Server shutdown complete")


if __name__ == "__main__":
    # Run server in standalone mode
    import sys
    
    session_id = sys.argv[1] if len(sys.argv) > 1 else "TEST123"
    host_username = sys.argv[2] if len(sys.argv) > 2 else "server_host"
    
    run_server_standalone(session_id, host_username)
