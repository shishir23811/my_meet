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
        
        # Note about localhost
        note = QLabel("Tip: Use '127.0.0.1' or 'localhost' for same-machine testing")
        note.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(note)
        
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
        
        # Create formatted session info
        session_info = f"Session ID: {self.session_id}\nServer Address: {self.server_ip}"
        
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
        
        logger.info(f"Attempting to join session '{session_id}' at '{server_address}' as '{self.username}'")
        logger.info(f"Session ID length: {len(session_id)}, characters: {[c for c in session_id]}")
        self.join_session.emit(session_id, server_address, self.username)
    
    def handle_go_back(self):
        """Handle back button - return to login."""
        logger.info(f"User '{self.username}' logging out")
        self.go_back.emit()
