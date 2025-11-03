"""
HostJoinWindow for LAN Communication Application.
Provides UI for hosting a new session or joining an existing one.
"""

import secrets
import socket
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QStackedWidget, QMessageBox
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont
from utils.logger import setup_logger
from utils.config import config, DEFAULT_TCP_PORT, DEFAULT_UDP_PORT

logger = setup_logger(__name__)

class HostJoinWindow(QWidget):
    """
    Window for hosting or joining a communication session.
    Provides session ID generation and connection setup.
    """
    
    # Signals
    host_session = Signal(str, str)  # session_id, username
    join_session = Signal(str, str, str)  # session_id, server_address, username
    join_session_with_ports = Signal(str, str, str, int, int)  # session_id, server_address, username, tcp_port, udp_port
    go_back = Signal()  # Return to login
    
    def __init__(self, username: str):
        super().__init__()
        self.username = username
        self.session_id = None
        self.server_ip = self.get_local_ip_address()
        self.setWindowTitle("LAN Communicator - Session")
        self.resize(500, 400)
        self.setup_ui()
        logger.info(f"HostJoinWindow initialized for user '{username}'")
    
    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # Title
        title = QLabel(f"Welcome, {self.username}!")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        subtitle = QLabel("Host a new session or join an existing one")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: gray;")
        layout.addWidget(subtitle)
        
        # Stacked widget for Host/Join views
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.addWidget(self.create_selection_page())
        self.stacked_widget.addWidget(self.create_host_page())
        self.stacked_widget.addWidget(self.create_join_page())
        layout.addWidget(self.stacked_widget)
        
        # Back button
        back_btn = QPushButton("← Logout")
        back_btn.clicked.connect(self.handle_go_back)
        layout.addWidget(back_btn)
    
    def create_selection_page(self) -> QWidget:
        """Create the initial selection page."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(20)
        
        layout.addStretch()
        
        # Host button
        host_btn = QPushButton("Host a Session")
        host_btn.setMinimumHeight(80)
        host_btn.setStyleSheet("""
            QPushButton {
                font-size: 18px;
                font-weight: bold;
                background-color: #4CAF50;
                color: white;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        host_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1))
        layout.addWidget(host_btn)
        
        # Join button
        join_btn = QPushButton("Join a Session")
        join_btn.setMinimumHeight(80)
        join_btn.setStyleSheet("""
            QPushButton {
                font-size: 18px;
                font-weight: bold;
                background-color: #2196F3;
                color: white;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """)
        join_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(2))
        layout.addWidget(join_btn)
        
        layout.addStretch()
        
        return page
    
    def create_host_page(self) -> QWidget:
        """Create the host session page."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(15)
        
        # Instructions
        instructions = QLabel("Host a New Session")
        instructions_font = QFont()
        instructions_font.setPointSize(16)
        instructions_font.setBold(True)
        instructions.setFont(instructions_font)
        layout.addWidget(instructions)
        
        info = QLabel("Generate a session ID to share with others.\n"
                     "Your computer will act as the server.")
        info.setWordWrap(True)
        info.setStyleSheet("color: gray;")
        layout.addWidget(info)
        
        layout.addSpacing(20)
        
        # Session ID display
        layout.addWidget(QLabel("Session ID:"))
        self.host_session_id = QLineEdit()
        self.host_session_id.setReadOnly(True)
        self.host_session_id.setMinimumHeight(40)
        self.host_session_id.setStyleSheet("""
            QLineEdit {
                font-size: 18px;
                font-weight: bold;
                text-align: center;
                background-color: #f0f0f0;
            }
        """)
        layout.addWidget(self.host_session_id)
        
        # Server IP display
        layout.addWidget(QLabel("Server IP Address:"))
        self.server_ip_display = QLineEdit()
        self.server_ip_display.setText(self.server_ip)
        self.server_ip_display.setReadOnly(True)
        self.server_ip_display.setMinimumHeight(40)
        self.server_ip_display.setStyleSheet("""
            QLineEdit {
                font-size: 14px;
                font-weight: bold;
                text-align: center;
                background-color: #f0f0f0;
            }
        """)
        layout.addWidget(self.server_ip_display)
        
        # Port display (will be updated when server starts)
        layout.addWidget(QLabel("Server Ports:"))
        self.port_display = QLineEdit()
        self.port_display.setText(f"TCP: {DEFAULT_TCP_PORT}, UDP: {DEFAULT_UDP_PORT} (default)")
        self.port_display.setReadOnly(True)
        self.port_display.setMinimumHeight(40)
        self.port_display.setStyleSheet("""
            QLineEdit {
                font-size: 14px;
                font-weight: bold;
                text-align: center;
                background-color: #e8f4f8;
            }
        """)
        layout.addWidget(self.port_display)
        
        # Generate button
        generate_btn = QPushButton("Generate Session ID")
        generate_btn.setMinimumHeight(40)
        generate_btn.clicked.connect(self.generate_session_id)
        layout.addWidget(generate_btn)
        
        # Copy buttons layout
        copy_layout = QHBoxLayout()
        
        # Copy session ID button
        copy_session_btn = QPushButton("Copy Session ID")
        copy_session_btn.clicked.connect(self.copy_session_id)
        copy_layout.addWidget(copy_session_btn)
        
        # Copy all info button
        copy_all_btn = QPushButton("Copy All Info")
        copy_all_btn.clicked.connect(self.copy_all_info)
        copy_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """)
        copy_layout.addWidget(copy_all_btn)
        
        layout.addLayout(copy_layout)
        
        layout.addSpacing(20)
        
        # Network settings display
        tcp_port = config.get('network.tcp_port', DEFAULT_TCP_PORT)
        udp_port = config.get('network.udp_port', DEFAULT_UDP_PORT)
        settings_label = QLabel(f"TCP Port: {tcp_port} | UDP Port: {udp_port}")
        settings_label.setAlignment(Qt.AlignCenter)
        settings_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(settings_label)
        
        # Start hosting button
        start_host_btn = QPushButton("Start Hosting")
        start_host_btn.setMinimumHeight(50)
        start_host_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 16px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        start_host_btn.clicked.connect(self.start_hosting)
        layout.addWidget(start_host_btn)
        
        # Back button
        back_btn = QPushButton("← Back")
        back_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        layout.addWidget(back_btn)
        
        layout.addStretch()
        
        return page
    
    def create_join_page(self) -> QWidget:
        """Create the join session page."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(15)
        
        # Instructions
        instructions = QLabel("Join an Existing Session")
        instructions_font = QFont()
        instructions_font.setPointSize(16)
        instructions_font.setBold(True)
        instructions.setFont(instructions_font)
        layout.addWidget(instructions)
        
        info = QLabel("Enter the session ID and server address provided by the host.")
        info.setWordWrap(True)
        info.setStyleSheet("color: gray;")
        layout.addWidget(info)
        
        layout.addSpacing(20)
        
        # Session ID input
        layout.addWidget(QLabel("Session ID:"))
        self.join_session_id = QLineEdit()
        self.join_session_id.setPlaceholderText("Enter session ID (e.g., A1B2C3D4)")
        self.join_session_id.setMaxLength(8)  # Session IDs are 8 characters
        self.join_session_id.setMinimumHeight(40)
        # Convert to uppercase as user types
        self.join_session_id.textChanged.connect(lambda text: self.join_session_id.setText(text.upper()) if text != text.upper() else None)
        layout.addWidget(self.join_session_id)
        
        # Server address input
        layout.addWidget(QLabel("Server Address (IP):"))
        self.join_server_address = QLineEdit()
        self.join_server_address.setPlaceholderText("e.g., 192.168.1.100")
        self.join_server_address.setMinimumHeight(40)
        self.join_server_address.returnPressed.connect(self.start_joining)
        layout.addWidget(self.join_server_address)
        
        # Port inputs (optional, with defaults)
        port_layout = QHBoxLayout()
        
        # TCP Port
        port_layout.addWidget(QLabel("TCP Port:"))
        self.join_tcp_port = QLineEdit()
        self.join_tcp_port.setPlaceholderText("From session info")
        self.join_tcp_port.setMaxLength(5)
        self.join_tcp_port.setMinimumHeight(40)
        port_layout.addWidget(self.join_tcp_port)
        
        # UDP Port
        port_layout.addWidget(QLabel("UDP Port:"))
        self.join_udp_port = QLineEdit()
        self.join_udp_port.setPlaceholderText("From session info")
        self.join_udp_port.setMaxLength(5)
        self.join_udp_port.setMinimumHeight(40)
        port_layout.addWidget(self.join_udp_port)
        
        layout.addLayout(port_layout)
        
        # Note about ports and localhost
        note = QLabel("⚠️ IMPORTANT: Enter the TCP and UDP ports from the session info shared by the host.\nLeave empty only if host is using default ports (54321, 54322).")
        note.setStyleSheet("color: #d63031; font-size: 11px; font-weight: bold;")
        note.setWordWrap(True)
        layout.addWidget(note)
        
        # Paste session info button
        paste_btn = QPushButton("📋 Paste Session Info from Clipboard")
        paste_btn.setMinimumHeight(35)
        paste_btn.clicked.connect(self.paste_session_info)
        paste_btn.setStyleSheet("""
            QPushButton {
                background-color: #0984e3;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #74b9ff;
            }
        """)
        layout.addWidget(paste_btn)
        
        layout.addSpacing(20)
        
        # Join button
        join_btn = QPushButton("Join Session")
        join_btn.setMinimumHeight(50)
        join_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-size: 16px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """)
        join_btn.clicked.connect(self.start_joining)
        layout.addWidget(join_btn)
        
        # Back button
        back_btn = QPushButton("← Back")
        back_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        layout.addWidget(back_btn)
        
        layout.addStretch()
        
        return page
    
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
    
    def generate_session_id(self):
        """Generate a random session ID."""
        # Generate 8-character alphanumeric session ID
        self.session_id = secrets.token_hex(4).upper()
        self.host_session_id.setText(self.session_id)
        logger.info(f"Generated session ID: {self.session_id}")
        QMessageBox.information(self, "Session ID Generated", 
                              f"Session ID: {self.session_id}\n\n"
                              "Share this ID with others to let them join your session.")
    
    def copy_session_id(self):
        """Copy session ID to clipboard."""
        if not self.session_id:
            QMessageBox.warning(self, "No Session ID", 
                              "Please generate a session ID first.")
            return
        
        from PySide6.QtGui import QGuiApplication
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(self.session_id)
        QMessageBox.information(self, "Copied", 
                              f"Session ID '{self.session_id}' copied to clipboard!")
        logger.info("Session ID copied to clipboard")
    
    def copy_all_info(self):
        """Copy session ID and server IP address to clipboard."""
        if not self.session_id:
            QMessageBox.warning(self, "No Session ID", 
                              "Please generate a session ID first.")
            return
        
        from PySide6.QtGui import QGuiApplication
        
        # Create formatted session info with port information
        port_info = ""
        if hasattr(self, 'actual_tcp_port') and hasattr(self, 'actual_udp_port'):
            # Always show actual ports used by the server
            port_info = f"\nTCP Port: {self.actual_tcp_port}\nUDP Port: {self.actual_udp_port}"
        else:
            # Fallback to default ports if server hasn't started yet
            port_info = f"\nTCP Port: {DEFAULT_TCP_PORT}\nUDP Port: {DEFAULT_UDP_PORT}"
        
        session_info = f"Session ID: {self.session_id}\nServer Address: {self.server_ip}{port_info}"
        
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(session_info)
        QMessageBox.information(self, "Copied", 
                              f"Session information copied to clipboard!\n\n{session_info}")
        logger.info(f"Complete session info copied to clipboard: {session_info}")
    
    def start_hosting(self):
        """Start hosting a session."""
        if not self.session_id:
            QMessageBox.warning(self, "No Session ID", 
                              "Please generate a session ID first.")
            return
        
        logger.info(f"Starting to host session '{self.session_id}' for user '{self.username}'")
        self.host_session.emit(self.session_id, self.username)
    
    def start_joining(self):
        """Start joining a session."""
        session_id = self.join_session_id.text().strip().upper()  # Ensure uppercase
        server_address = self.join_server_address.text().strip()
        
        # Get custom ports or use defaults
        tcp_port_text = self.join_tcp_port.text().strip()
        udp_port_text = self.join_udp_port.text().strip()
        
        try:
            tcp_port = int(tcp_port_text) if tcp_port_text else DEFAULT_TCP_PORT
            udp_port = int(udp_port_text) if udp_port_text else DEFAULT_UDP_PORT
        except ValueError:
            QMessageBox.warning(self, "Invalid Port", 
                              "Ports must be numbers between 1024 and 65535.")
            return
        
        # Validate port ranges
        if not (1024 <= tcp_port <= 65535) or not (1024 <= udp_port <= 65535):
            QMessageBox.warning(self, "Invalid Port Range", 
                              "Ports must be between 1024 and 65535.")
            return
        
        if not session_id:
            QMessageBox.warning(self, "Input Error", 
                              "Please enter a session ID.")
            return
        
        # Validate session ID format
        if len(session_id) != 8:
            QMessageBox.warning(self, "Invalid Session ID", 
                              f"Session ID must be 8 characters long.\nYou entered: '{session_id}' ({len(session_id)} characters)")
            return
        
        # Check if session ID contains only valid hex characters
        valid_chars = set('0123456789ABCDEF')
        if not set(session_id).issubset(valid_chars):
            QMessageBox.warning(self, "Invalid Session ID", 
                              f"Session ID must contain only numbers and letters A-F.\nYou entered: '{session_id}'")
            return
        
        if not server_address:
            QMessageBox.warning(self, "Input Error", 
                              "Please enter the server address.")
            return
        
        logger.info(f"Attempting to join session '{session_id}' at '{server_address}:{tcp_port}' as '{self.username}'")
        logger.info(f"Using ports: TCP {tcp_port}, UDP {udp_port}")
        
        # Use new signal with port information
        self.join_session_with_ports.emit(session_id, server_address, self.username, tcp_port, udp_port)
    
    def paste_session_info(self):
        """Parse and fill session information from clipboard."""
        try:
            from PySide6.QtGui import QGuiApplication
            clipboard = QGuiApplication.clipboard()
            clipboard_text = clipboard.text().strip()
            
            if not clipboard_text:
                QMessageBox.warning(self, "Empty Clipboard", 
                                  "Clipboard is empty. Please copy session info from the host first.")
                return
            
            # Parse session info
            session_id = None
            server_address = None
            tcp_port = None
            udp_port = None
            
            lines = clipboard_text.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('Session ID:'):
                    session_id = line.split(':', 1)[1].strip()
                elif line.startswith('Server Address:'):
                    server_address = line.split(':', 1)[1].strip()
                elif line.startswith('TCP Port:'):
                    try:
                        tcp_port = int(line.split(':', 1)[1].strip())
                    except ValueError:
                        pass
                elif line.startswith('UDP Port:'):
                    try:
                        udp_port = int(line.split(':', 1)[1].strip())
                    except ValueError:
                        pass
            
            # Fill the form fields
            filled_fields = []
            if session_id:
                self.join_session_id.setText(session_id.upper())
                filled_fields.append("Session ID")
            
            if server_address:
                self.join_server_address.setText(server_address)
                filled_fields.append("Server Address")
            
            if tcp_port:
                self.join_tcp_port.setText(str(tcp_port))
                filled_fields.append("TCP Port")
            
            if udp_port:
                self.join_udp_port.setText(str(udp_port))
                filled_fields.append("UDP Port")
            
            if filled_fields:
                QMessageBox.information(self, "Session Info Parsed", 
                                      f"Successfully filled: {', '.join(filled_fields)}\n\n"
                                      f"Please verify the information and click 'Join Session'.")
                logger.info(f"Parsed session info from clipboard: {filled_fields}")
            else:
                QMessageBox.warning(self, "Invalid Format", 
                                  "Could not parse session information from clipboard.\n\n"
                                  "Expected format:\n"
                                  "Session ID: XXXXXXXX\n"
                                  "Server Address: X.X.X.X\n"
                                  "TCP Port: XXXXX\n"
                                  "UDP Port: XXXXX")
                
        except Exception as e:
            logger.error(f"Error parsing session info: {e}")
            QMessageBox.critical(self, "Parse Error", 
                               f"Error parsing session information: {e}")
    
    def update_server_ports(self, tcp_port: int, udp_port: int):
        """Update the actual server ports used (for session sharing)."""
        self.actual_tcp_port = tcp_port
        self.actual_udp_port = udp_port
        
        # Update the visual port display
        if hasattr(self, 'port_display'):
            if tcp_port == DEFAULT_TCP_PORT and udp_port == DEFAULT_UDP_PORT:
                self.port_display.setText(f"TCP: {tcp_port}, UDP: {udp_port} (default)")
                self.port_display.setStyleSheet("""
                    QLineEdit {
                        font-size: 14px;
                        font-weight: bold;
                        text-align: center;
                        background-color: #e8f8e8;
                    }
                """)
            else:
                self.port_display.setText(f"TCP: {tcp_port}, UDP: {udp_port} (auto-selected)")
                self.port_display.setStyleSheet("""
                    QLineEdit {
                        font-size: 14px;
                        font-weight: bold;
                        text-align: center;
                        background-color: #fff8e8;
                    }
                """)
        
        logger.info(f"Server ports updated: TCP {tcp_port}, UDP {udp_port}")
    
    def handle_go_back(self):
        """Handle back button - return to login."""
        logger.info(f"User '{self.username}' logging out")
        self.go_back.emit()
