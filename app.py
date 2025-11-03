"""
Main application launcher for LAN Communication Application.

Manages window flow: Login → HostJoin → MainApp
Integrates GUI with client/server networking components.
"""

import sys
import os
import socket
import threading
from PySide6.QtWidgets import QApplication, QStackedWidget, QMessageBox
from PySide6.QtCore import Qt, Slot
from utils.logger import setup_logger
from utils.error_manager import error_manager, ErrorCategory, ErrorSeverity
from utils.config import DEFAULT_TCP_PORT, DEFAULT_UDP_PORT
from gui.login import LoginWindow
from gui.hostjoin import HostJoinWindow
from gui.mainapp import MainAppWindow
from server.server import LANServer
from client.client import LANClient
from client.media_capture import MediaCaptureManager

logger = setup_logger(__name__)

class LANCommunicatorApp(QStackedWidget):
    """
    Main application controller.
    
    Manages window transitions and integrates GUI with networking.
    """
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LAN Communicator")
        self.resize(800, 600)
        
        # State
        self.current_username = None
        self.session_id = None
        self.is_host = False
        self.server_address = None
        self.server = None
        self.client = None
        self.media_capture = None
        
        # Create windows
        self.login_window = LoginWindow()
        self.hostjoin_window = None  # Created after login
        self.main_window = None  # Created after host/join
        
        # Add login window
        self.addWidget(self.login_window)
        
        # Connect login signals
        self.login_window.login_successful.connect(self.on_login_successful)
        
        logger.info("LANCommunicatorApp initialized")
    
    def get_local_ip_address(self):
        """Get the local IP address of this machine."""
        try:
            # Connect to a remote address to determine local IP
            # This doesn't actually send data, just determines routing
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                return local_ip
        except Exception:
            # Fallback to localhost if unable to determine IP
            return "127.0.0.1"
    
    @Slot(str)
    def on_login_successful(self, username: str):
        """Handle successful login."""
        logger.info(f"Login successful for user '{username}'")
        self.current_username = username
        
        # Create and show host/join window
        self.hostjoin_window = HostJoinWindow(username)
        self.hostjoin_window.host_session.connect(self.on_host_session)
        self.hostjoin_window.join_session.connect(self.on_join_session)
        self.hostjoin_window.join_session_with_ports.connect(self.on_join_session_with_ports)
        self.hostjoin_window.go_back.connect(self.on_logout)
        
        self.addWidget(self.hostjoin_window)
        self.setCurrentWidget(self.hostjoin_window)
    
    @Slot(str, str)
    def on_host_session(self, session_id: str, username: str):
        """Handle hosting a session."""
        logger.info(f"Hosting session '{session_id}' as '{username}'")
        self.session_id = session_id
        self.is_host = True
        self.server_address = self.get_local_ip_address()
        
        try:
            # Start server
            self.server = LANServer(session_id, username)
            server_thread = threading.Thread(target=self.server.start, daemon=True)
            server_thread.start()
            
            # Wait for server to start and get actual ports
            import time
            time.sleep(1.0)  # Give server more time to start
            
            # Check if server started successfully
            if not self.server.running:
                raise Exception("Server failed to start - check port availability")
            
            # Connect as client to own server using actual server ports
            self.client = LANClient(
                username, 
                '127.0.0.1', 
                session_id,
                tcp_port=self.server.tcp_port,
                udp_port=self.server.udp_port
            )
            self.client.set_app_reference(self)
            self.media_capture = MediaCaptureManager(self.client)
            
            # Connect client signals
            self._connect_client_signals()
            
            # Connect to server
            if self.client.connect():
                # Update host/join window with actual ports used
                if self.hostjoin_window:
                    self.hostjoin_window.update_server_ports(self.server.tcp_port, self.server.udp_port)
                
                # Create and show main window
                self._create_main_window()
            else:
                QMessageBox.critical(self, "Connection Failed",
                                   "Failed to connect to server.")
                self.server.stop()
                self.server = None
                
        except Exception as e:
            logger.error(f"Failed to host session: {e}")
            
            # Provide more specific error messages
            error_msg = str(e)
            if "10048" in error_msg or "address already in use" in error_msg.lower():
                error_msg = ("Port already in use. Please try again in a few seconds, "
                           "or restart the application to free up ports.")
            elif "server failed to start" in error_msg.lower():
                error_msg = ("Server failed to start. This might be due to port conflicts "
                           "or permission issues. Try restarting the application.")
            
            QMessageBox.critical(self, "Failed to Host Session", error_msg)
            
            if self.server:
                self.server.stop()
                self.server = None
    
    def _test_server_connectivity(self, server_address: str, port: int, timeout: float = 5.0) -> bool:
        """Test if server is reachable on the specified port."""
        try:
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.settimeout(timeout)
            result = test_socket.connect_ex((server_address, port))
            test_socket.close()
            return result == 0
        except Exception as e:
            logger.debug(f"Connectivity test failed: {e}")
            return False

    @Slot(str, str, str)
    def on_join_session(self, session_id: str, server_address: str, username: str):
        """Handle joining a session."""
        logger.info(f"Joining session '{session_id}' at '{server_address}' as '{username}'")
        self.session_id = session_id
        self.is_host = False
        self.server_address = server_address
        
        try:
            # Test server connectivity first
            logger.info(f"Testing connectivity to {server_address}:{DEFAULT_TCP_PORT}")
            if not self._test_server_connectivity(server_address, DEFAULT_TCP_PORT, timeout=3.0):
                error_msg = (f"Cannot reach server at {server_address}:{DEFAULT_TCP_PORT}.\n\n"
                           f"Please check:\n"
                           f"• The host has started the session\n"
                           f"• Both devices are on the same network\n"
                           f"• The IP address is correct\n"
                           f"• Firewall allows connections on port {DEFAULT_TCP_PORT}\n\n"
                           f"For detailed diagnostics, run:\n"
                           f"python network_diagnostics.py {server_address}")
                
                QMessageBox.critical(self, "Server Not Reachable", error_msg)
                return
            
            # Create client with default ports (server should be using standard ports)
            self.client = LANClient(
                username, 
                server_address, 
                session_id,
                tcp_port=DEFAULT_TCP_PORT,
                udp_port=DEFAULT_UDP_PORT
            )
            self.client.set_app_reference(self)
            self.media_capture = MediaCaptureManager(self.client)
            
            # Connect client signals
            self._connect_client_signals()
            
            # Connect to server
            logger.info(f"Server is reachable, attempting to connect to {server_address}:{DEFAULT_TCP_PORT}")
            if self.client.connect():
                # Wait for authentication (will trigger _create_main_window via signal)
                logger.info("Successfully connected to server, waiting for authentication")
            else:
                error_msg = (f"Failed to connect to server at {server_address}:{DEFAULT_TCP_PORT}.\n\n"
                           f"Possible causes:\n"
                           f"• Server is not running or not reachable\n"
                           f"• Firewall is blocking the connection\n"
                           f"• Wrong IP address or port\n"
                           f"• Network connectivity issues\n\n"
                           f"Please check that:\n"
                           f"1. The host has started the session\n"
                           f"2. Both devices are on the same network\n"
                           f"3. Firewall allows connections on port {DEFAULT_TCP_PORT}")
                
                QMessageBox.critical(self, "Connection Failed", error_msg)
                
        except Exception as e:
            logger.error(f"Failed to join session: {e}")
            
            # Provide more specific error messages
            error_msg = str(e)
            if "10060" in error_msg or "timed out" in error_msg.lower():
                if sys.platform.startswith('win'):
                    firewall_msg = (f"🔥 MOST LIKELY CAUSE: Windows Firewall\n\n"
                                  f"HOST COMPUTER ({server_address}) MUST:\n"
                                  f"1. Run setup_firewall.bat as Administrator\n"
                                  f"2. Or manually open Windows Defender Firewall (wf.msc)\n"
                                  f"3. Create Inbound Rules for ports {DEFAULT_TCP_PORT} and {DEFAULT_UDP_PORT}")
                else:
                    firewall_msg = (f"🔥 MOST LIKELY CAUSE: Firewall\n\n"
                                  f"HOST COMPUTER ({server_address}) MUST:\n"
                                  f"1. Run ./setup_firewall_ubuntu.sh\n"
                                  f"2. Or manually: sudo ufw allow {DEFAULT_TCP_PORT}/tcp\n"
                                  f"3. And: sudo ufw allow {DEFAULT_UDP_PORT}/udp")
                
                error_msg = (f"Connection timed out to {server_address}:{DEFAULT_TCP_PORT}\n\n"
                           f"{firewall_msg}\n\n"
                           f"OTHER POSSIBLE CAUSES:\n"
                           f"• Host hasn't started the session\n"
                           f"• Different network segments\n"
                           f"• Router blocking inter-device communication\n\n"
                           f"See NETWORK_TROUBLESHOOTING.md for detailed steps")
            elif "10061" in error_msg or "connection refused" in error_msg.lower():
                error_msg = (f"Connection refused by {server_address}:{DEFAULT_TCP_PORT}.\n\n"
                           f"This usually means:\n"
                           f"• No server is listening on that port\n"
                           f"• The host hasn't started the session yet\n\n"
                           f"Please make sure the host has started the session.")
            
            QMessageBox.critical(self, "Connection Error", error_msg)
    
    @Slot(str, str, str, int, int)
    def on_join_session_with_ports(self, session_id: str, server_address: str, username: str, tcp_port: int, udp_port: int):
        """Handle joining a session with custom ports."""
        logger.info(f"Joining session '{session_id}' at '{server_address}:{tcp_port}' as '{username}'")
        self.session_id = session_id
        self.is_host = False
        self.server_address = server_address
        
        try:
            # Test server connectivity first
            logger.info(f"Testing connectivity to {server_address}:{tcp_port}")
            if not self._test_server_connectivity(server_address, tcp_port, timeout=3.0):
                error_msg = (f"Cannot reach server at {server_address}:{tcp_port}.\n\n"
                           f"Please check:\n"
                           f"• The host has started the session\n"
                           f"• Both devices are on the same network\n"
                           f"• The IP address and ports are correct\n"
                           f"• Firewall allows connections on port {tcp_port}")
                
                QMessageBox.critical(self, "Server Not Reachable", error_msg)
                return
            
            # Create client with specified ports
            self.client = LANClient(
                username, 
                server_address, 
                session_id,
                tcp_port=tcp_port,
                udp_port=udp_port
            )
            self.client.set_app_reference(self)
            self.media_capture = MediaCaptureManager(self.client)
            
            # Connect client signals
            self._connect_client_signals()
            
            # Connect to server
            logger.info(f"Server is reachable, attempting to connect to {server_address}:{tcp_port}")
            if self.client.connect():
                # Wait for authentication (will trigger _create_main_window via signal)
                logger.info("Successfully connected to server, waiting for authentication")
            else:
                QMessageBox.critical(self, "Connection Failed",
                                   f"Failed to connect to server at {server_address}:{tcp_port}.")
                
        except Exception as e:
            logger.error(f"Failed to join session: {e}")
            QMessageBox.critical(self, "Connection Error", f"Failed to join session: {e}")
    
    def _test_server_connectivity(self, server_address: str, port: int, timeout: float = 5.0) -> bool:
        """Test if server is reachable on the specified port."""
        try:
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.settimeout(timeout)
            result = test_socket.connect_ex((server_address, port))
            test_socket.close()
            return result == 0
        except Exception as e:
            logger.debug(f"Connectivity test failed: {e}")
            return False
    
    def _connect_client_signals(self):
        """Connect client network signals to handlers."""
        self.client.auth_success.connect(self.on_auth_success)
        self.client.auth_failed.connect(self.on_auth_failed)
        self.client.chat_message_received.connect(self.on_chat_message_received)
        self.client.user_joined.connect(self.on_user_joined)
        self.client.user_left.connect(self.on_user_left)
        self.client.user_list_received.connect(self.on_user_list_received)
        self.client.file_offer_received.connect(self.on_file_offer_received)
        self.client.audio_data_received.connect(self.on_audio_data_received)
        self.client.video_data_received.connect(self.on_video_data_received)
        self.client.screen_frame_received.connect(self.on_screen_frame_received)
        self.client.disconnected.connect(self.on_disconnected)
        self.client.error_occurred.connect(self.on_client_error)
        
        # Reconnection signals
        self.client.reconnection_started.connect(self.on_reconnection_started)
        self.client.reconnection_failed.connect(self.on_reconnection_failed)
        self.client.reconnection_succeeded.connect(self.on_reconnection_succeeded)
        self.client.manual_retry_required.connect(self.on_manual_retry_required)
        
        logger.info("Client signals connected")
    
    def _create_main_window(self):
        """Create and show the main application window."""
        self.main_window = MainAppWindow(
            self.current_username,
            self.session_id,
            self.is_host,
            self.server_address
        )
        
        # Connect main window signals to client methods
        self.main_window.send_chat_message.connect(self.on_send_chat_message)
        self.main_window.upload_file.connect(self.on_upload_file)
        self.main_window.download_file.connect(self.on_download_file)
        self.main_window.start_audio.connect(self.on_start_audio)
        self.main_window.stop_audio.connect(self.on_stop_audio)
        self.main_window.start_video.connect(self.on_start_video)
        self.main_window.stop_video.connect(self.on_stop_video)
        self.main_window.start_screen_share.connect(self.on_start_screen_share)
        self.main_window.stop_screen_share.connect(self.on_stop_screen_share)
        self.main_window.leave_session.connect(self.on_leave_session)
        
        # Connect media manager for audio strength monitoring
        if self.media_capture:
            self.main_window.set_media_manager(self.media_capture)
        
        self.addWidget(self.main_window)
        self.setCurrentWidget(self.main_window)
        
        logger.info("Main window created and displayed")
    
    # ========================================================================
    # Client Signal Handlers
    # ========================================================================
    
    @Slot(str)
    def on_auth_success(self, username: str):
        """Handle successful authentication."""
        logger.info(f"Authentication successful for '{username}'")
        if not self.main_window:
            self._create_main_window()
    
    @Slot(str)
    def on_auth_failed(self, reason: str):
        """Handle authentication failure."""
        logger.warning(f"Authentication failed: {reason}")
        
        # Report error through error manager
        error_manager.report_error(
            category=ErrorCategory.AUTHENTICATION,
            error_type='auth_failed',
            severity=ErrorSeverity.ERROR,
            component='client',
            details=reason
        )
        
        QMessageBox.critical(self, "Authentication Failed", reason)
        
        # Return to host/join window
        if self.hostjoin_window:
            self.setCurrentWidget(self.hostjoin_window)
    
    @Slot(str, str)
    def on_chat_message_received(self, sender: str, message: str):
        """Handle received chat message."""
        if self.main_window:
            self.main_window.display_message(sender, message, "received")
    
    @Slot(str)
    def on_user_joined(self, username: str):
        """Handle user joined notification."""
        if self.main_window:
            self.main_window.add_user(username, {})
            self.main_window.display_message("System", f"{username} joined the session", "received")
    
    @Slot(str)
    def on_user_left(self, username: str):
        """Handle user left notification."""
        if self.main_window:
            self.main_window.remove_user(username)
            self.main_window.display_message("System", f"{username} left the session", "received")
    
    @Slot(list)
    def on_user_list_received(self, users: list):
        """Handle user list update."""
        if self.main_window:
            for username in users:
                if username != self.current_username:
                    self.main_window.add_user(username, {})
        logger.info(f"User list updated: {users}")
    
    @Slot(str, str, int, str)
    def on_file_offer_received(self, file_id: str, filename: str, size: int, uploader: str):
        """Handle file offer."""
        if self.main_window:
            self.main_window.add_available_file(file_id, filename, size, uploader)
    
    @Slot(str, bytes)
    def on_audio_data_received(self, username: str, audio_data: bytes):
        """Handle received audio data and detect speaking."""
        if self.media_capture:
            self.media_capture.process_received_audio(username, audio_data)
        
        # Detect if user is speaking based on audio data
        if self.main_window and audio_data:
            try:
                import numpy as np
                # Convert audio data to numpy array for analysis
                audio_array = np.frombuffer(audio_data, dtype=np.int16)
                
                # Calculate RMS to detect speaking
                rms = np.sqrt(np.mean(audio_array.astype(np.float32) ** 2))
                normalized_rms = rms / 32767.0  # Normalize for 16-bit audio
                
                # Simple threshold for speaking detection
                is_speaking = normalized_rms > 0.01  # Adjust threshold as needed
                
                # Update user speaking state in GUI
                self.main_window.update_user_speaking_state(username, is_speaking)
                
            except Exception as e:
                logger.error(f"Error detecting speaking for {username}: {e}")
    
    @Slot(str, bytes)
    def on_video_data_received(self, username: str, video_data: bytes):
        """Handle received video data."""
        if self.main_window:
            self.main_window.update_video_frame(username, video_data)
    
    @Slot(str, bytes, int, int)
    def on_screen_frame_received(self, username: str, frame_data: bytes, width: int, height: int):
        """Handle received screen frame."""
        if self.main_window:
            self.main_window.update_screen_frame(frame_data, width, height)
    
    @Slot()
    def on_disconnected(self):
        """Handle disconnection from server."""
        logger.warning("Disconnected from server")
        
        # Report disconnection through error manager
        error_manager.report_error(
            category=ErrorCategory.NETWORK,
            error_type='connection_lost',
            severity=ErrorSeverity.WARNING,
            component='network'
        )
        
        if self.main_window:
            self.main_window.set_connection_status(False)
            # Only show message if it's a manual disconnect or reconnection failed
            if self.client and not self.client.is_reconnecting():
                error_manager.report_error(
                    category=ErrorCategory.NETWORK,
                    error_type='connection_lost',
                    severity=ErrorSeverity.ERROR,
                    component='network',
                    details="Connection to server lost unexpectedly"
                )
    
    @Slot(int, int)
    def on_reconnection_started(self, attempt: int, max_attempts: int):
        """Handle reconnection attempt started."""
        logger.info(f"Reconnection attempt {attempt}/{max_attempts} started")
        if self.main_window:
            self.main_window.show_reconnection_status(f"Reconnecting... (attempt {attempt}/{max_attempts})")
    
    @Slot(str)
    def on_reconnection_failed(self, reason: str):
        """Handle reconnection attempt failed."""
        logger.warning(f"Reconnection failed: {reason}")
        
        # Report reconnection failure
        error_manager.report_error(
            category=ErrorCategory.NETWORK,
            error_type='reconnection_failed',
            severity=ErrorSeverity.WARNING,
            component='network',
            details=reason
        )
        
        if self.main_window:
            self.main_window.show_reconnection_status(f"Reconnection failed: {reason}")
    
    @Slot()
    def on_reconnection_succeeded(self):
        """Handle successful reconnection."""
        logger.info("Reconnection successful")
        if self.main_window:
            self.main_window.set_connection_status(True)
            self.main_window.show_reconnection_status("Reconnected successfully!")
            # Clear status after a few seconds
            from PySide6.QtCore import QTimer
            QTimer.singleShot(3000, lambda: self.main_window.show_reconnection_status(""))
    
    @Slot(str)
    def on_client_error(self, error_message: str):
        """Handle general client errors."""
        logger.error(f"Client error: {error_message}")
        
        # Categorize error based on message content
        if "connection" in error_message.lower():
            category = ErrorCategory.NETWORK
            error_type = "connection_error"
        elif "auth" in error_message.lower():
            category = ErrorCategory.AUTHENTICATION
            error_type = "auth_error"
        else:
            category = ErrorCategory.SYSTEM
            error_type = "client_error"
        
        error_manager.report_error(
            category=category,
            error_type=error_type,
            severity=ErrorSeverity.ERROR,
            component='client',
            details=error_message
        )
    
    @Slot()
    def on_manual_retry_required(self):
        """Handle when manual retry is required after automatic reconnection fails."""
        logger.warning("Manual retry required - automatic reconnection failed")
        
        # Report critical network error
        error_manager.report_error(
            category=ErrorCategory.NETWORK,
            error_type='manual_retry_required',
            severity=ErrorSeverity.CRITICAL,
            component='network',
            details="Automatic reconnection failed, manual intervention required"
        )
        
        if self.main_window:
            self.main_window.set_connection_status(False)
            # Show dialog with retry option
            from PySide6.QtWidgets import QMessageBox, QPushButton
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Connection Lost")
            msg_box.setText("Connection to server lost and automatic reconnection failed.")
            msg_box.setInformativeText("Would you like to try reconnecting manually?")
            
            retry_btn = msg_box.addButton("Retry", QMessageBox.ActionRole)
            leave_btn = msg_box.addButton("Leave Session", QMessageBox.RejectRole)
            msg_box.setDefaultButton(retry_btn)
            
            msg_box.exec()
            
            if msg_box.clickedButton() == retry_btn:
                if self.client:
                    self.client.manual_reconnect()
            else:
                self.on_leave_session()
    
    # ========================================================================
    # Main Window Signal Handlers
    # ========================================================================
    
    @Slot(str, str, list)
    def on_send_chat_message(self, message: str, mode: str, targets: list):
        """Handle send chat message from GUI."""
        if self.client:
            self.client.send_chat_message(message, mode, targets)
    
    @Slot(str, str, list)
    def on_upload_file(self, file_path: str, mode: str, targets: list):
        """Handle file upload from GUI."""
        if self.client:
            try:
                file_id = self.client.upload_file(file_path, mode, targets)
                if file_id:
                    logger.info(f"Started file upload: {file_path} (ID: {file_id})")
                    error_manager.update_component_status('file_transfer', 'processing', f'Uploading {os.path.basename(file_path)}')
                else:
                    logger.error(f"Failed to start file upload: {file_path}")
                    error_manager.report_error(
                        category=ErrorCategory.FILE_TRANSFER,
                        error_type='upload_failed',
                        severity=ErrorSeverity.ERROR,
                        component='file_transfer',
                        details=f"Failed to start upload: {file_path}"
                    )
            except Exception as e:
                logger.error(f"Error uploading file: {e}")
                error_manager.report_error(
                    category=ErrorCategory.FILE_TRANSFER,
                    error_type='upload_failed',
                    severity=ErrorSeverity.ERROR,
                    component='file_transfer',
                    details=str(e)
                )
    
    @Slot(str)
    def on_download_file(self, file_id: str):
        """Handle file download from GUI."""
        if self.client:
            try:
                # For now, download to current directory
                import os
                save_path = os.path.join(os.getcwd(), f"download_{file_id}")
                success = self.client.download_file(file_id, save_path)
                if success:
                    logger.info(f"Started file download: {file_id}")
                    error_manager.update_component_status('file_transfer', 'processing', f'Downloading file {file_id}')
                else:
                    logger.error(f"Failed to start file download: {file_id}")
                    error_manager.report_error(
                        category=ErrorCategory.FILE_TRANSFER,
                        error_type='download_failed',
                        severity=ErrorSeverity.ERROR,
                        component='file_transfer',
                        details=f"Failed to start download: {file_id}"
                    )
            except Exception as e:
                logger.error(f"Error downloading file: {e}")
                error_manager.report_error(
                    category=ErrorCategory.FILE_TRANSFER,
                    error_type='download_failed',
                    severity=ErrorSeverity.ERROR,
                    component='file_transfer',
                    details=str(e)
                )
    
    @Slot()
    def on_start_audio(self):
        """Handle start audio request."""
        if self.media_capture:
            try:
                self.media_capture.start_audio()
                error_manager.update_component_status('audio', 'active', 'Audio capture started')
            except Exception as e:
                logger.error(f"Failed to start audio: {e}")
                error_manager.report_error(
                    category=ErrorCategory.MEDIA,
                    error_type='audio_start_failed',
                    severity=ErrorSeverity.ERROR,
                    component='audio',
                    details=str(e)
                )
    
    @Slot()
    def on_stop_audio(self):
        """Handle stop audio request."""
        if self.media_capture:
            try:
                self.media_capture.stop_audio()
                error_manager.update_component_status('audio', 'inactive', 'Audio capture stopped')
            except Exception as e:
                logger.error(f"Failed to stop audio: {e}")
                error_manager.report_error(
                    category=ErrorCategory.MEDIA,
                    error_type='audio_stop_failed',
                    severity=ErrorSeverity.WARNING,
                    component='audio',
                    details=str(e)
                )
    
    @Slot()
    def on_start_video(self):
        """Handle start video request."""
        if self.media_capture:
            try:
                self.media_capture.start_video()
                error_manager.update_component_status('video', 'active', 'Video capture started')
            except Exception as e:
                logger.error(f"Failed to start video: {e}")
                error_manager.report_error(
                    category=ErrorCategory.MEDIA,
                    error_type='video_start_failed',
                    severity=ErrorSeverity.ERROR,
                    component='video',
                    details=str(e)
                )
    
    @Slot()
    def on_stop_video(self):
        """Handle stop video request."""
        if self.media_capture:
            try:
                self.media_capture.stop_video()
                error_manager.update_component_status('video', 'inactive', 'Video capture stopped')
            except Exception as e:
                logger.error(f"Failed to stop video: {e}")
                error_manager.report_error(
                    category=ErrorCategory.MEDIA,
                    error_type='video_stop_failed',
                    severity=ErrorSeverity.WARNING,
                    component='video',
                    details=str(e)
                )
    
    @Slot()
    def on_start_screen_share(self):
        """Handle start screen share request."""
        if self.media_capture:
            try:
                success = self.media_capture.start_screen_share()
                if success:
                    error_manager.update_component_status('screen_share', 'active', 'Screen sharing started')
                    logger.info("Screen sharing started successfully")
                else:
                    error_message = self.media_capture.get_screen_error()
                    error_manager.report_error(
                        category=ErrorCategory.MEDIA,
                        error_type='screen_share_start_failed',
                        severity=ErrorSeverity.ERROR,
                        component='screen_share',
                        details=error_message or 'Unknown screen sharing error'
                    )
            except Exception as e:
                logger.error(f"Failed to start screen sharing: {e}")
                error_manager.report_error(
                    category=ErrorCategory.MEDIA,
                    error_type='screen_share_start_failed',
                    severity=ErrorSeverity.ERROR,
                    component='screen_share',
                    details=str(e)
                )
    
    @Slot()
    def on_stop_screen_share(self):
        """Handle stop screen share request."""
        if self.media_capture:
            try:
                self.media_capture.stop_screen_share()
                error_manager.update_component_status('screen_share', 'inactive', 'Screen sharing stopped')
                logger.info("Screen sharing stopped successfully")
            except Exception as e:
                logger.error(f"Failed to stop screen sharing: {e}")
                error_manager.report_error(
                    category=ErrorCategory.MEDIA,
                    error_type='screen_share_stop_failed',
                    severity=ErrorSeverity.WARNING,
                    component='screen_share',
                    details=str(e)
                )
    
    def update_self_video_frame(self, frame_data: bytes):
        """Update self video frame in GUI."""
        logger.debug(f"update_self_video_frame called, frame size: {len(frame_data)}, username: {self.current_username}")
        if self.main_window:
            self.main_window.update_user_video_frame(self.current_username, frame_data)
        else:
            logger.warning("No main window available for video frame update")
    
    def on_user_video_stopped(self, username: str):
        """Handle when a user stops their video."""
        if self.main_window:
            self.main_window.clear_user_video(username)
    
    @Slot()
    def on_leave_session(self):
        """Handle leave session request."""
        logger.info("Leaving session")
        
        # Disconnect client
        if self.client:
            self.client.disconnect()
            self.client = None
        
        # Stop server if hosting
        if self.server:
            self.server.stop()
            self.server = None
        
        # Return to host/join window
        if self.hostjoin_window:
            self.setCurrentWidget(self.hostjoin_window)
        
        # Remove main window
        if self.main_window:
            self.removeWidget(self.main_window)
            self.main_window = None
    
    @Slot()
    def on_logout(self):
        """Handle logout request."""
        logger.info("Logging out")
        
        # Clean up any active session
        if self.client:
            self.client.disconnect()
            self.client = None
        
        if self.server:
            self.server.stop()
            self.server = None
        
        # Remove windows
        if self.main_window:
            self.removeWidget(self.main_window)
            self.main_window = None
        
        if self.hostjoin_window:
            self.removeWidget(self.hostjoin_window)
            self.hostjoin_window = None
        
        # Return to login
        self.setCurrentWidget(self.login_window)
        self.current_username = None
        self.session_id = None
    
    def closeEvent(self, event):
        """Handle application close."""
        logger.info("Application closing")
        
        # Clean up
        if self.client:
            self.client.disconnect()
        
        if self.server:
            self.server.stop()
        
        event.accept()


def main():
    """Main entry point for the application."""
    logger.info("=" * 60)
    logger.info("LAN Communication Application Starting")
    logger.info("=" * 60)
    
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("LAN Communicator")
    app.setOrganizationName("LAN Comm")
    
    # Set application style
    app.setStyle("Fusion")
    
    # Create and show main window
    main_window = LANCommunicatorApp()
    main_window.show()
    
    logger.info("Application window displayed")
    
    # Run event loop
    exit_code = app.exec()
    
    logger.info(f"Application exiting with code {exit_code}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())