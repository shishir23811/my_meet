"""
MainAppWindow for LAN Communication Application.
Main communication interface with chat, files, video, and user management.
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QLineEdit, QListWidget, QListWidgetItem,
    QTabWidget, QSplitter, QProgressBar, QFileDialog, QMessageBox,
    QCheckBox, QRadioButton, QButtonGroup, QGroupBox, QGridLayout,
    QStatusBar, QScrollArea, QFrame
)
from PySide6.QtCore import Signal, Qt, Slot, QSize, QTimer
from PySide6.QtGui import QPixmap, QImage
from utils.logger import setup_logger
from utils.error_manager import error_manager, ErrorCategory, ErrorSeverity
from gui.status_widgets import EnhancedStatusBar, NotificationWidget
from datetime import datetime
import os

logger = setup_logger(__name__)

class MainAppWindow(QMainWindow):
    """
    Main application window with full communication features.
    
    Features:
    - User list with checkboxes for multicast
    - Chat panel with message history
    - File transfer panel
    - Video/audio controls
    - Communication mode selector (unicast/multicast/broadcast)
    - Status bar with connection info
    """
    
    # Signals for network actions
    send_chat_message = Signal(str, str, list)  # message, mode, target_users
    upload_file = Signal(str, str, list)  # file_path, mode, target_users
    download_file = Signal(str)  # file_id
    start_audio = Signal()
    stop_audio = Signal()
    start_video = Signal()
    stop_video = Signal()
    start_screen_share = Signal()
    stop_screen_share = Signal()
    leave_session = Signal()
    
    def __init__(self, username: str, session_id: str, is_host: bool = False, server_address: str = None):
        super().__init__()
        self.username = username
        self.session_id = session_id
        self.is_host = is_host
        self.server_address = server_address or "localhost"
        self.connected_users = {}  # username -> user_info dict
        self.available_files = {}  # file_id -> file_info dict
        
        self.audio_active = False
        self.video_active = False
        self.screen_share_active = False
        
        # Error and status management
        self.error_manager = error_manager
        self.active_notifications = []
        self.status_update_timer = QTimer()
        self.status_update_timer.timeout.connect(self._update_feature_status)
        self.status_update_timer.start(2000)  # Update every 2 seconds
        
        self.setWindowTitle(f"LAN Communicator - {username}")
        self.resize(1200, 800)
        self.setup_ui()
        self._setup_error_handling()
        logger.info(f"MainAppWindow initialized for user '{username}' in session '{session_id}'")
    
    def setup_ui(self):
        """Set up the main user interface."""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create main splitter: left sidebar | center content
        splitter = QSplitter(Qt.Horizontal)
        
        # Left sidebar - users and mode selector
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # Center content - tabs for chat, files, video
        center_panel = self.create_center_panel()
        splitter.addWidget(center_panel)
        
        # Set splitter proportions: 20% left, 80% center
        splitter.setSizes([250, 950])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(splitter)
        
        # Status bar
        self.setup_status_bar()
    
    def create_left_panel(self) -> QWidget:
        """Create left sidebar with user list and mode selector."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Session info
        session_label = QLabel(f"Session: {self.session_id}")
        session_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout.addWidget(session_label)
        
        role_label = QLabel("Role: " + ("Host" if self.is_host else "Participant"))
        role_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(role_label)
        
        # Server address info
        server_label = QLabel(f"Server: {self.server_address}")
        server_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(server_label)
        
        # Copy session info button
        copy_info_btn = QPushButton("📋 Copy Session Info")
        copy_info_btn.setMinimumHeight(30)
        copy_info_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 6px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """)
        copy_info_btn.clicked.connect(self.copy_session_info)
        layout.addWidget(copy_info_btn)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        layout.addWidget(separator)
        
        # User list header with ALL/None button
        users_header_layout = QHBoxLayout()
        
        users_label = QLabel("Active Users")
        users_label.setStyleSheet("font-weight: bold;")
        users_header_layout.addWidget(users_label)
        
        # ALL/None toggle button
        self.select_all_btn = QPushButton("All")
        self.select_all_btn.setFixedSize(50, 25)
        self.select_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 10px;
                font-weight: bold;
                border-radius: 3px;
                padding: 2px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.select_all_btn.clicked.connect(self.toggle_select_all_users)
        users_header_layout.addWidget(self.select_all_btn)
        
        layout.addLayout(users_header_layout)
        
        # User list
        self.user_list_widget = QListWidget()
        self.user_list_widget.itemChanged.connect(self.on_user_selection_changed)
        layout.addWidget(self.user_list_widget)
        
        # Leave session button
        leave_btn = QPushButton("Leave Session")
        leave_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        leave_btn.clicked.connect(self.handle_leave_session)
        layout.addWidget(leave_btn)
        
        return panel
    
    def create_center_panel(self) -> QWidget:
        """Create center panel with tabs for different features."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self.create_chat_tab(), "💬 Chat")
        self.tab_widget.addTab(self.create_files_tab(), "📁 Files")
        self.tab_widget.addTab(self.create_media_tab(), "📹 Audio/Video")
        self.tab_widget.addTab(self.create_screen_tab(), "🖥️ Screen Share")
        
        layout.addWidget(self.tab_widget)
        
        return panel
    
    def create_chat_tab(self) -> QWidget:
        """Create chat tab with message history and input."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Chat history
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 10px;
            }
        """)
        layout.addWidget(self.chat_display)
        
        # Input area
        input_layout = QHBoxLayout()
        
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Type your message here...")
        self.chat_input.returnPressed.connect(self.handle_send_message)
        self.chat_input.setMinimumHeight(40)
        input_layout.addWidget(self.chat_input)
        
        send_btn = QPushButton("Send")
        send_btn.setMinimumWidth(80)
        send_btn.setMinimumHeight(40)
        send_btn.clicked.connect(self.handle_send_message)
        send_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """)
        input_layout.addWidget(send_btn)
        
        layout.addLayout(input_layout)
        
        return tab
    
    def create_files_tab(self) -> QWidget:
        """Create file transfer tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Upload section
        upload_group = QGroupBox("Upload File")
        upload_layout = QHBoxLayout(upload_group)
        
        self.selected_file_label = QLabel("No file selected")
        self.selected_file_label.setStyleSheet("color: gray;")
        upload_layout.addWidget(self.selected_file_label)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.handle_browse_file)
        upload_layout.addWidget(browse_btn)
        
        upload_btn = QPushButton("Upload")
        upload_btn.clicked.connect(self.handle_upload_file)
        upload_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px 20px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        upload_layout.addWidget(upload_btn)
        
        layout.addWidget(upload_group)
        
        # Available files list
        files_label = QLabel("Available Files")
        files_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(files_label)
        
        self.files_list_widget = QListWidget()
        self.files_list_widget.itemDoubleClicked.connect(self.handle_download_file)
        layout.addWidget(self.files_list_widget)
        
        # Download button
        download_btn = QPushButton("Download Selected")
        download_btn.clicked.connect(self.handle_download_file)
        download_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 8px;
            }
        """)
        layout.addWidget(download_btn)
        
        # Transfer progress
        self.transfer_progress = QProgressBar()
        self.transfer_progress.setVisible(False)
        layout.addWidget(self.transfer_progress)
        
        return tab
    
    def create_media_tab(self) -> QWidget:
        """Create audio/video controls and display tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # Controls
        controls_group = QGroupBox("Media Controls")
        controls_layout = QGridLayout(controls_group)
        
        # Audio controls
        self.audio_btn = QPushButton("🎤 Start Audio")
        self.audio_btn.setMinimumHeight(50)
        self.audio_btn.clicked.connect(self.toggle_audio)
        self.audio_btn.setStyleSheet("font-size: 14px; font-weight: bold;")
        controls_layout.addWidget(self.audio_btn, 0, 0)
        
        # Video controls
        self.video_btn = QPushButton("📹 Start Video")
        self.video_btn.setMinimumHeight(50)
        self.video_btn.clicked.connect(self.toggle_video)
        self.video_btn.setStyleSheet("font-size: 14px; font-weight: bold;")
        controls_layout.addWidget(self.video_btn, 0, 1)
        
        layout.addWidget(controls_group)
        
        # Video display area
        video_label = QLabel("Video Streams")
        video_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(video_label)
        
        # Video grid (placeholder for video streams)
        self.video_container = QWidget()
        self.video_layout = QGridLayout(self.video_container)
        self.video_container.setStyleSheet("background-color: #000; border: 2px solid #ddd;")
        layout.addWidget(self.video_container, 1)
        
        # Add placeholder video frames
        self.add_placeholder_video("Local Preview")
        
        return tab
    
    def create_screen_tab(self) -> QWidget:
        """Create screen sharing tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        self.screen_share_btn = QPushButton("🖥️ Start Screen Share")
        self.screen_share_btn.setMinimumHeight(50)
        self.screen_share_btn.clicked.connect(self.toggle_screen_share)
        self.screen_share_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        controls_layout.addWidget(self.screen_share_btn)
        
        layout.addLayout(controls_layout)
        
        # Screen display area
        screen_label = QLabel("Shared Screen")
        screen_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(screen_label)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("background-color: #2b2b2b; border: 2px solid #ddd;")
        
        self.screen_display = QLabel("No screen being shared")
        self.screen_display.setAlignment(Qt.AlignCenter)
        self.screen_display.setStyleSheet("color: white; font-size: 16px;")
        self.screen_display.setMinimumSize(800, 600)
        
        scroll_area.setWidget(self.screen_display)
        layout.addWidget(scroll_area, 1)
        
        return tab
    
    def setup_status_bar(self):
        """Set up the enhanced status bar."""
        # Create enhanced status bar
        self.enhanced_status_bar = EnhancedStatusBar()
        self.enhanced_status_bar.set_error_manager(self.error_manager)
        
        # Create traditional status bar for additional info
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Add enhanced status bar as a widget
        self.status_bar.addWidget(self.enhanced_status_bar, 1)
        
        # Add separator
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setStyleSheet("color: #ccc;")
        self.status_bar.addWidget(separator)
        
        # User info
        user_label = QLabel(f"User: {self.username}")
        user_label.setStyleSheet("font-size: 10px; color: #666;")
        self.status_bar.addWidget(user_label)
        
        # Session info
        session_label = QLabel(f"Session: {self.session_id}")
        session_label.setStyleSheet("font-size: 10px; color: #666;")
        self.status_bar.addWidget(session_label)
    
    # ========================================================================
    # User Management Methods
    # ========================================================================
    
    def add_user(self, username: str, user_info: dict):
        """
        Add a user to the user list.
        
        Args:
            username: Username to add
            user_info: Dictionary with user information
        """
        if username == self.username:
            return  # Don't add self
        
        self.connected_users[username] = user_info
        
        item = QListWidgetItem(f"🟢 {username}")
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(Qt.Unchecked)
        item.setData(Qt.UserRole, username)
        self.user_list_widget.addItem(item)
        
        # Update the All/None button state
        self.update_select_all_button()
        
        logger.info(f"Added user '{username}' to user list")
    
    def remove_user(self, username: str):
        """Remove a user from the user list."""
        if username in self.connected_users:
            del self.connected_users[username]
        
        for i in range(self.user_list_widget.count()):
            item = self.user_list_widget.item(i)
            if item.data(Qt.UserRole) == username:
                self.user_list_widget.takeItem(i)
                logger.info(f"Removed user '{username}' from user list")
                break
        
        # Update the All/None button state
        self.update_select_all_button()
        
        # Also remove video display
        self.remove_user_video(username)
    
    def get_selected_users(self) -> list:
        """Get list of checked usernames."""
        selected = []
        for i in range(self.user_list_widget.count()):
            item = self.user_list_widget.item(i)
            if item.checkState() == Qt.Checked:
                selected.append(item.data(Qt.UserRole))
        return selected
    
    @Slot()
    def on_user_selection_changed(self):
        """Handle user selection changes."""
        selected = self.get_selected_users()
        logger.debug(f"Selected users: {selected}")
        
        # Update button text based on selection
        self.update_select_all_button()
    
    @Slot()
    def toggle_select_all_users(self):
        """Toggle selection of all users."""
        if self.select_all_btn.text() == "All":
            # Select all users
            for i in range(self.user_list_widget.count()):
                item = self.user_list_widget.item(i)
                item.setCheckState(Qt.Checked)
            logger.info("Selected all users")
        else:
            # Deselect all users
            for i in range(self.user_list_widget.count()):
                item = self.user_list_widget.item(i)
                item.setCheckState(Qt.Unchecked)
            logger.info("Deselected all users")
        
        # Update button appearance
        self.update_select_all_button()
    
    def update_select_all_button(self):
        """Update the All/None button based on current selection."""
        selected_count = len(self.get_selected_users())
        total_count = self.user_list_widget.count()
        
        if selected_count == 0:
            # No users selected - show "All" button
            self.select_all_btn.setText("All")
            self.select_all_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    font-size: 10px;
                    font-weight: bold;
                    border-radius: 3px;
                    padding: 2px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)
        elif selected_count == total_count:
            # All users selected - show "None" button
            self.select_all_btn.setText("None")
            self.select_all_btn.setStyleSheet("""
                QPushButton {
                    background-color: #f44336;
                    color: white;
                    font-size: 10px;
                    font-weight: bold;
                    border-radius: 3px;
                    padding: 2px;
                }
                QPushButton:hover {
                    background-color: #da190b;
                }
            """)
        else:
            # Some users selected - show "None" button (to clear selection)
            self.select_all_btn.setText("None")
            self.select_all_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FF9800;
                    color: white;
                    font-size: 10px;
                    font-weight: bold;
                    border-radius: 3px;
                    padding: 2px;
                }
                QPushButton:hover {
                    background-color: #F57C00;
                }
            """)
    
    # ========================================================================
    # Chat Methods
    # ========================================================================
    
    @Slot()
    def handle_send_message(self):
        """Handle sending a chat message."""
        message = self.chat_input.text().strip()
        if not message:
            return
        
        # Determine mode and targets based on user selection
        selected_users = self.get_selected_users()
        
        if not selected_users:
            # No users selected - broadcast to all
            mode = "broadcast"
            targets = []
        elif len(selected_users) == 1:
            # One user selected - unicast
            mode = "unicast"
            targets = selected_users
        else:
            # Multiple users selected - multicast
            mode = "multicast"
            targets = selected_users
        
        # Emit signal (will be handled by client network layer)
        self.send_chat_message.emit(message, mode, targets)
        
        # Display in local chat (echo)
        self.display_message(self.username, message, "sent")
        
        # Clear input
        self.chat_input.clear()
        logger.info(f"Sent chat message in {mode} mode to {len(targets) if targets else 'all'} users: {message[:50]}...")
    
    def display_message(self, sender: str, message: str, direction: str = "received"):
        """
        Display a chat message in the chat display.
        
        Args:
            sender: Username of sender
            message: Message text
            direction: 'sent' or 'received'
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if direction == "sent":
            html = f'<div style="text-align: right; margin: 5px;">' \
                   f'<span style="color: gray; font-size: 10px;">{timestamp}</span><br>' \
                   f'<b style="color: #2196F3;">{sender}:</b> {message}' \
                   f'</div>'
        else:
            html = f'<div style="text-align: left; margin: 5px;">' \
                   f'<span style="color: gray; font-size: 10px;">{timestamp}</span><br>' \
                   f'<b style="color: #4CAF50;">{sender}:</b> {message}' \
                   f'</div>'
        
        self.chat_display.append(html)
    
    # ========================================================================
    # File Transfer Methods
    # ========================================================================
    
    @Slot()
    def handle_browse_file(self):
        """Handle file browse button."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File to Upload")
        if file_path:
            self.selected_file_path = file_path
            self.selected_file_label.setText(os.path.basename(file_path))
            logger.info(f"Selected file: {file_path}")
    
    @Slot()
    def handle_upload_file(self):
        """Handle file upload button with enhanced error handling."""
        try:
            if not hasattr(self, 'selected_file_path'):
                self.error_manager.report_error(
                    category=ErrorCategory.USER_INPUT,
                    error_type='no_file_selected',
                    severity=ErrorSeverity.WARNING,
                    component='file_transfer'
                )
                return
            
            # Check if file still exists
            if not os.path.exists(self.selected_file_path):
                self.error_manager.report_error(
                    category=ErrorCategory.FILE_TRANSFER,
                    error_type='file_not_found',
                    severity=ErrorSeverity.ERROR,
                    component='file_transfer',
                    details=f"File not found: {self.selected_file_path}"
                )
                return
            
            # Determine mode and targets based on user selection
            selected_users = self.get_selected_users()
            
            if not selected_users:
                # No users selected - broadcast to all
                mode = "broadcast"
                targets = []
            elif len(selected_users) == 1:
                # One user selected - unicast
                mode = "unicast"
                targets = selected_users
            else:
                # Multiple users selected - multicast
                mode = "multicast"
                targets = selected_users
            
            # Update status and emit signal
            self.error_manager.update_component_status('file_transfer', 'processing', 'Starting file upload...')
            self.upload_file.emit(self.selected_file_path, mode, targets)
            
            filename = os.path.basename(self.selected_file_path)
            self.show_success_notification("Upload Started", f"Uploading {filename}...")
            logger.info(f"Uploading file: {self.selected_file_path}")
            
        except Exception as e:
            logger.error(f"Error handling file upload: {e}")
            self.error_manager.report_error(
                category=ErrorCategory.FILE_TRANSFER,
                error_type='upload_failed',
                severity=ErrorSeverity.ERROR,
                component='file_transfer',
                details=str(e)
            )
    
    @Slot()
    def handle_download_file(self):
        """Handle file download button with enhanced error handling."""
        try:
            selected_items = self.files_list_widget.selectedItems()
            if not selected_items:
                self.error_manager.report_error(
                    category=ErrorCategory.USER_INPUT,
                    error_type='no_file_selected',
                    severity=ErrorSeverity.WARNING,
                    component='file_transfer'
                )
                return
            
            file_id = selected_items[0].data(Qt.UserRole)
            if not file_id:
                self.error_manager.report_error(
                    category=ErrorCategory.FILE_TRANSFER,
                    error_type='invalid_file_id',
                    severity=ErrorSeverity.ERROR,
                    component='file_transfer'
                )
                return
            
            # Update status and emit signal
            self.error_manager.update_component_status('file_transfer', 'processing', 'Starting file download...')
            self.download_file.emit(file_id)
            
            filename = selected_items[0].text().split(' (')[0]  # Extract filename from display text
            self.show_success_notification("Download Started", f"Downloading {filename}...")
            logger.info(f"Downloading file: {file_id}")
            
        except Exception as e:
            logger.error(f"Error handling file download: {e}")
            self.error_manager.report_error(
                category=ErrorCategory.FILE_TRANSFER,
                error_type='download_failed',
                severity=ErrorSeverity.ERROR,
                component='file_transfer',
                details=str(e)
            )
    
    def add_available_file(self, file_id: str, filename: str, size: int, uploader: str):
        """Add a file to the available files list."""
        self.available_files[file_id] = {
            'filename': filename,
            'size': size,
            'uploader': uploader
        }
        
        size_mb = size / (1024 * 1024)
        item = QListWidgetItem(f"{filename} ({size_mb:.2f} MB) - from {uploader}")
        item.setData(Qt.UserRole, file_id)
        self.files_list_widget.addItem(item)
        logger.info(f"Added available file: {filename}")
    
    # ========================================================================
    # Media Methods
    # ========================================================================
    
    @Slot()
    def toggle_audio(self):
        """Toggle audio on/off with enhanced error handling."""
        try:
            if not self.audio_active:
                self.start_audio.emit()
                self.audio_active = True
                self.audio_btn.setText("🎤 Stop Audio")
                self.audio_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #f44336;
                        color: white;
                        font-size: 14px;
                        font-weight: bold;
                    }
                """)
                self.error_manager.update_component_status('audio', 'active', 'Audio streaming started')
                self.show_success_notification("Audio Started", "Audio streaming is now active")
                logger.info("Audio started")
            else:
                self.stop_audio.emit()
                self.audio_active = False
                self.audio_btn.setText("🎤 Start Audio")
                self.audio_btn.setStyleSheet("font-size: 14px; font-weight: bold;")
                self.error_manager.update_component_status('audio', 'inactive', 'Audio streaming stopped')
                logger.info("Audio stopped")
        except Exception as e:
            logger.error(f"Error toggling audio: {e}")
            self.error_manager.report_error(
                category=ErrorCategory.MEDIA,
                error_type='audio_toggle_failed',
                severity=ErrorSeverity.ERROR,
                component='audio',
                details=str(e)
            )
    
    @Slot()
    def toggle_video(self):
        """Toggle video on/off with enhanced error handling."""
        try:
            if not self.video_active:
                self.start_video.emit()
                self.video_active = True
                self.video_btn.setText("📹 Stop Video")
                self.video_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #f44336;
                        color: white;
                        font-size: 14px;
                        font-weight: bold;
                    }
                """)
                self.error_manager.update_component_status('video', 'active', 'Video streaming started')
                self.show_success_notification("Video Started", "Video streaming is now active")
                logger.info("Video started")
            else:
                self.stop_video.emit()
                self.video_active = False
                self.video_btn.setText("📹 Start Video")
                self.video_btn.setStyleSheet("font-size: 14px; font-weight: bold;")
                self.error_manager.update_component_status('video', 'inactive', 'Video streaming stopped')
                logger.info("Video stopped")
        except Exception as e:
            logger.error(f"Error toggling video: {e}")
            self.error_manager.report_error(
                category=ErrorCategory.MEDIA,
                error_type='video_toggle_failed',
                severity=ErrorSeverity.ERROR,
                component='video',
                details=str(e)
            )
    
    @Slot()
    def toggle_screen_share(self):
        """Toggle screen sharing on/off with enhanced error handling."""
        try:
            if not self.screen_share_active:
                self.start_screen_share.emit()
                self.screen_share_active = True
                self.screen_share_btn.setText("🖥️ Stop Screen Share")
                self.screen_share_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #f44336;
                        color: white;
                        font-size: 14px;
                        font-weight: bold;
                    }
                """)
                self.error_manager.update_component_status('screen_share', 'active', 'Screen sharing started')
                self.show_success_notification("Screen Share Started", "Screen sharing is now active")
                
                # Show local preview message
                self.screen_display.setText("🖥️ Screen sharing active\n\nYou are sharing your screen with other participants.\nOther users can see your screen content.\n\n(You don't see your own screen share - this is normal)")
                self.screen_display.setStyleSheet("color: green; font-size: 14px; font-weight: bold;")
                
                logger.info("Screen sharing started")
            else:
                self.stop_screen_share.emit()
                self.screen_share_active = False
                self.screen_share_btn.setText("🖥️ Start Screen Share")
                self.screen_share_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #FF9800;
                        color: white;
                        font-size: 14px;
                        font-weight: bold;
                    }
                """)
                self.error_manager.update_component_status('screen_share', 'inactive', 'Screen sharing stopped')
                
                # Reset display
                self.screen_display.setText("No screen being shared")
                self.screen_display.setStyleSheet("color: white; font-size: 16px;")
                
                logger.info("Screen sharing stopped")
        except Exception as e:
            logger.error(f"Error toggling screen share: {e}")
            self.error_manager.report_error(
                category=ErrorCategory.MEDIA,
                error_type='screen_share_toggle_failed',
                severity=ErrorSeverity.ERROR,
                component='screen_share',
                details=str(e)
            )
    
    def add_placeholder_video(self, label: str):
        """Add a placeholder video frame to the grid."""
        # Calculate grid position
        count = self.video_layout.count()
        row = count // 2
        col = count % 2
        
        frame = QLabel(label)
        frame.setAlignment(Qt.AlignCenter)
        frame.setStyleSheet("""
            QLabel {
                background-color: #333;
                color: white;
                border: 2px solid #555;
                min-height: 240px;
                font-size: 16px;
            }
        """)
        frame.setMinimumSize(320, 240)
        
        self.video_layout.addWidget(frame, row, col)
    
    def update_video_frame(self, username: str, frame_data: bytes):
        """
        Update video frame for a user.
        
        Args:
            username: Username
            frame_data: JPEG frame data
        """
        try:
            # Decode JPEG frame data
            import numpy as np
            from PySide6.QtGui import QPixmap
            
            # Convert bytes to numpy array
            nparr = np.frombuffer(frame_data, np.uint8)
            
            # Try to import cv2 for decoding
            try:
                import cv2
                # Decode JPEG
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if frame is not None:
                    # Convert BGR to RGB
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    
                    # Convert to QImage
                    height, width, channel = frame_rgb.shape
                    bytes_per_line = 3 * width
                    q_image = QImage(frame_rgb.data, width, height, bytes_per_line, QImage.Format_RGB888)
                    
                    # Convert to QPixmap and display
                    pixmap = QPixmap.fromImage(q_image)
                    self._display_user_video(username, pixmap)
                else:
                    logger.warning(f"Failed to decode video frame from {username}")
            except ImportError:
                logger.warning("OpenCV not available for video decoding")
                
        except Exception as e:
            logger.error(f"Error updating video frame for {username}: {e}")
    
    def _display_user_video(self, username: str, pixmap: QPixmap):
        """Display video frame for a user in the video grid."""
        # Find or create video label for this user
        video_label = None
        
        # Search for existing label
        for i in range(self.video_layout.count()):
            item = self.video_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if hasattr(widget, 'username') and widget.username == username:
                    video_label = widget
                    break
        
        # Create new label if not found
        if not video_label:
            video_label = QLabel()
            video_label.username = username
            video_label.setAlignment(Qt.AlignCenter)
            video_label.setStyleSheet("""
                QLabel {
                    background-color: #000;
                    border: 2px solid #555;
                    min-height: 240px;
                }
            """)
            video_label.setMinimumSize(320, 240)
            video_label.setScaledContents(True)
            
            # Add to grid
            count = self.video_layout.count()
            row = count // 2
            col = count % 2
            self.video_layout.addWidget(video_label, row, col)
            
            logger.info(f"Created video display for user {username}")
        
        # Scale pixmap to fit label while maintaining aspect ratio
        scaled_pixmap = pixmap.scaled(
            video_label.size(), 
            Qt.KeepAspectRatio, 
            Qt.SmoothTransformation
        )
        
        # Update the label
        video_label.setPixmap(scaled_pixmap)
    
    def remove_user_video(self, username: str):
        """Remove video display for a user."""
        for i in range(self.video_layout.count()):
            item = self.video_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if hasattr(widget, 'username') and widget.username == username:
                    self.video_layout.removeWidget(widget)
                    widget.deleteLater()
                    logger.info(f"Removed video display for user {username}")
                    break
    
    def update_screen_frame(self, frame_data: bytes, width: int = 0, height: int = 0):
        """
        Update shared screen display.
        
        Args:
            frame_data: JPEG screen frame data
            width: Frame width
            height: Frame height
        """
        try:
            # Reset text style in case it was showing status message
            self.screen_display.setStyleSheet("color: white; font-size: 16px;")
            
            # Decode JPEG frame data
            import numpy as np
            from PySide6.QtGui import QPixmap
            
            # Convert bytes to numpy array
            nparr = np.frombuffer(frame_data, np.uint8)
            
            # Try to import cv2 for decoding
            try:
                import cv2
                # Decode JPEG
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if frame is not None:
                    # Convert BGR to RGB
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    
                    # Convert to QImage
                    height, width, channel = frame_rgb.shape
                    bytes_per_line = 3 * width
                    q_image = QImage(frame_rgb.data, width, height, bytes_per_line, QImage.Format_RGB888)
                    
                    # Convert to QPixmap and display
                    pixmap = QPixmap.fromImage(q_image)
                    
                    # Scale pixmap to fit display while maintaining aspect ratio
                    scaled_pixmap = pixmap.scaled(
                        self.screen_display.size(), 
                        Qt.KeepAspectRatio, 
                        Qt.SmoothTransformation
                    )
                    
                    self.screen_display.setPixmap(scaled_pixmap)
                    logger.debug(f"Updated screen frame: {width}x{height}")
                else:
                    logger.warning("Failed to decode screen frame")
                    self.screen_display.setText("Failed to decode screen frame")
                    self.screen_display.setStyleSheet("color: orange; font-size: 16px;")
            except ImportError:
                logger.warning("OpenCV not available for screen frame decoding")
                self.screen_display.setText("OpenCV not available for screen display")
                self.screen_display.setStyleSheet("color: red; font-size: 16px;")
                
        except Exception as e:
            logger.error(f"Error updating screen frame: {e}")
            self.screen_display.setText(f"Error displaying screen frame: {e}")
            self.screen_display.setStyleSheet("color: red; font-size: 14px;")
    
    # ========================================================================
    # Session Methods
    # ========================================================================
    
    @Slot()
    def handle_leave_session(self):
        """Handle leave session button."""
        reply = QMessageBox.question(
            self, "Leave Session",
            "Are you sure you want to leave this session?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            logger.info(f"User '{self.username}' leaving session '{self.session_id}'")
            self.leave_session.emit()
    
    @Slot()
    def copy_session_info(self):
        """Copy session ID and server address to clipboard."""
        try:
            from PySide6.QtGui import QGuiApplication
            
            # Create formatted session info
            session_info = f"Session ID: {self.session_id}\nServer Address: {self.server_address}"
            
            # Copy to clipboard
            clipboard = QGuiApplication.clipboard()
            clipboard.setText(session_info)
            
            # Show success notification
            self.show_success_notification(
                "Session Info Copied", 
                f"Session ID and server address copied to clipboard!"
            )
            
            logger.info(f"Session info copied to clipboard: {session_info}")
            
        except Exception as e:
            logger.error(f"Error copying session info: {e}")
            self.error_manager.report_error(
                category=ErrorCategory.SYSTEM,
                error_type='clipboard_error',
                severity=ErrorSeverity.WARNING,
                component='gui',
                details=str(e)
            )
    
    def _setup_error_handling(self):
        """Setup error handling and status monitoring."""
        # Connect error manager signals
        self.error_manager.error_reported.connect(self._on_error_reported)
        self.error_manager.error_resolved.connect(self._on_error_resolved)
        
        # Initialize component status
        self.error_manager.update_component_status('network', 'disconnected', 'Not connected to server')
        self.error_manager.update_component_status('audio', 'inactive', 'Audio not active')
        self.error_manager.update_component_status('video', 'inactive', 'Video not active')
        self.error_manager.update_component_status('screen_share', 'inactive', 'Screen sharing not active')
        self.error_manager.update_component_status('file_transfer', 'idle', 'No active transfers')
        
        logger.info("Error handling and status monitoring setup complete")
    
    def _update_feature_status(self):
        """Update feature status indicators based on current state."""
        # Update audio status
        if self.audio_active:
            self.error_manager.update_component_status('audio', 'active', 'Audio streaming active')
        else:
            self.error_manager.update_component_status('audio', 'inactive', 'Audio not active')
        
        # Update video status
        if self.video_active:
            self.error_manager.update_component_status('video', 'active', 'Video streaming active')
        else:
            self.error_manager.update_component_status('video', 'inactive', 'Video not active')
        
        # Update screen share status
        if self.screen_share_active:
            self.error_manager.update_component_status('screen_share', 'active', 'Screen sharing active')
        else:
            self.error_manager.update_component_status('screen_share', 'inactive', 'Screen sharing not active')
    
    def _on_error_reported(self, error_report):
        """Handle error reports from the error manager."""
        logger.debug(f"GUI received error report: {error_report.title}")
        
        # Update button states if error affects media features
        if error_report.category == ErrorCategory.MEDIA:
            if 'audio' in error_report.message.lower():
                self._update_audio_button_error_state(True)
            elif 'video' in error_report.message.lower() or 'camera' in error_report.message.lower():
                self._update_video_button_error_state(True)
            elif 'screen' in error_report.message.lower():
                self._update_screen_share_button_error_state(True)
    
    def _on_error_resolved(self, error_id: str):
        """Handle error resolution."""
        logger.debug(f"GUI received error resolution: {error_id}")
        # Reset button states - this is a simplified approach
        # In production, you'd track which specific errors affect which buttons
        self._update_audio_button_error_state(False)
        self._update_video_button_error_state(False)
        self._update_screen_share_button_error_state(False)
    
    def _update_audio_button_error_state(self, has_error: bool):
        """Update audio button to reflect error state."""
        if has_error:
            self.audio_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ffcdd2;
                    color: #d32f2f;
                    font-size: 14px;
                    font-weight: bold;
                    border: 2px solid #d32f2f;
                }
            """)
        else:
            # Reset to normal style
            if self.audio_active:
                self.audio_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #f44336;
                        color: white;
                        font-size: 14px;
                        font-weight: bold;
                    }
                """)
            else:
                self.audio_btn.setStyleSheet("font-size: 14px; font-weight: bold;")
    
    def _update_video_button_error_state(self, has_error: bool):
        """Update video button to reflect error state."""
        if has_error:
            self.video_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ffcdd2;
                    color: #d32f2f;
                    font-size: 14px;
                    font-weight: bold;
                    border: 2px solid #d32f2f;
                }
            """)
        else:
            # Reset to normal style
            if self.video_active:
                self.video_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #f44336;
                        color: white;
                        font-size: 14px;
                        font-weight: bold;
                    }
                """)
            else:
                self.video_btn.setStyleSheet("font-size: 14px; font-weight: bold;")
    
    def _update_screen_share_button_error_state(self, has_error: bool):
        """Update screen share button to reflect error state."""
        if has_error:
            self.screen_share_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ffcdd2;
                    color: #d32f2f;
                    font-size: 14px;
                    font-weight: bold;
                    border: 2px solid #d32f2f;
                }
            """)
        else:
            # Reset to normal style
            if self.screen_share_active:
                self.screen_share_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #f44336;
                        color: white;
                        font-size: 14px;
                        font-weight: bold;
                    }
                """)
            else:
                self.screen_share_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #FF9800;
                        color: white;
                        font-size: 14px;
                        font-weight: bold;
                    }
                """)
    
    def set_connection_status(self, connected: bool):
        """Update connection status indicator."""
        if connected:
            self.error_manager.update_component_status('network', 'connected', 'Connected to server')
        else:
            self.error_manager.update_component_status('network', 'disconnected', 'Disconnected from server')
    
    def show_reconnection_status(self, message: str):
        """Show reconnection status message."""
        if message:
            if "Reconnecting" in message:
                self.error_manager.update_component_status('network', 'reconnecting', message)
            elif "failed" in message.lower():
                self.error_manager.update_component_status('network', 'error', message)
            elif "successful" in message.lower():
                self.error_manager.update_component_status('network', 'connected', message)
        
    def show_error_notification(self, title: str, message: str, 
                              category: ErrorCategory = ErrorCategory.SYSTEM,
                              severity: ErrorSeverity = ErrorSeverity.ERROR):
        """Show a user-friendly error notification."""
        error_id = self.error_manager.report_error(
            category=category,
            error_type='user_notification',
            severity=severity,
            component='gui',
            details=message
        )
        return error_id
    
    def show_success_notification(self, title: str, message: str):
        """Show a success notification."""
        notification = NotificationWidget(title, message, "info", 3000)
        notification.show_notification(self)
        self.active_notifications.append(notification)
        notification.closed.connect(lambda: self._remove_notification(notification))
    
    def _remove_notification(self, notification):
        """Remove notification from active list."""
        if notification in self.active_notifications:
            self.active_notifications.remove(notification)
        notification.deleteLater()
