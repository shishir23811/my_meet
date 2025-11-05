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
from gui.icons import (
    MICROPHONE_SVG, MICROPHONE_OFF_SVG, VIDEO_SVG, VIDEO_OFF_SVG,
    SCREEN_SHARE_SVG, SCREEN_SHARE_OFF_SVG, PHONE_HANGUP_SVG,
    USERS_SVG, CHAT_SVG, set_button_icon
)
from datetime import datetime
import os
import hashlib

logger = setup_logger(__name__)

def generate_avatar_color(username: str) -> str:
    """Generate a consistent color for a username using hash - matching reference images."""
    # Colors matching the reference images for profile boxes
    colors = [
        "#2E7D32",  # Dark Green (like Shishir Kumar in reference)
        "#1976D2",  # Blue (like CS23B2043 in reference)  
        "#7B1FA2",  # Purple (like omnamsmruf in reference)
        "#5D4037",  # Brown (like Shishir Kumar Reddy Ambala in reference)
        "#D32F2F",  # Red
        "#F57C00",  # Orange
        "#388E3C",  # Green
        "#303F9F",  # Indigo
        "#C2185B",  # Pink
        "#00796B",  # Teal
        "#455A64",  # Blue Grey
        "#8BC34A",  # Light Green
        "#FF9800",  # Amber
        "#9C27B0",  # Purple
        "#607D8B",  # Blue Grey
    ]
    
    # Use hash of username to get consistent color
    hash_object = hashlib.md5(username.encode())
    hash_hex = hash_object.hexdigest()
    color_index = int(hash_hex, 16) % len(colors)
    
    return colors[color_index]

class PresentationBox(QWidget):
    """Presentation box widget for screen sharing display."""
    
    def __init__(self, username: str):
        super().__init__()
        self.username = username
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the presentation box UI."""
        self.setMinimumSize(400, 300)  # Larger minimum size for presentations
        
        # Presentation box styling with depth effect
        self.setStyleSheet("""
            PresentationBox {
                background-color: #1a1a1a;
                border: 2px solid #444;
                border-radius: 12px;
                /* Depth effect */
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #252525, stop:1 #1a1a1a);
            }
        """)
        
        # Screen display area
        self.screen_area = QLabel(self)
        self.screen_area.setAlignment(Qt.AlignCenter)
        self.screen_area.setScaledContents(True)
        self.screen_area.setStyleSheet("""
            QLabel {
                background-color: #000;
                border-radius: 10px;
                color: #666;
                font-size: 16px;
            }
        """)
        self.screen_area.setText("No screen being shared")
        
        # Title label
        self.title_label = QLabel(self)
        self.title_label.setText(f"{self.username}'s Presentation")
        self.title_label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 0.8);
                color: white;
                padding: 8px 12px;
                border-radius: 6px;
                font-weight: 600;
                font-size: 14px;
            }
        """)
        self.title_label.adjustSize()
    
    def update_size(self, width: int, height: int):
        """Update the size and position elements."""
        self.setFixedSize(width, height)
        
        # Screen area takes most of the space with small margin
        margin = 4
        self.screen_area.setGeometry(margin, margin, width - 2*margin, height - 2*margin)
        
        # Position title at top left
        self.title_label.adjustSize()
        self.title_label.move(20, 20)
    
    def set_screen_frame(self, frame_data: bytes, width: int = 0, height: int = 0):
        """Set screen frame for this presentation."""
        if not frame_data:
            self.screen_area.setText("No screen being shared")
            self.screen_area.setPixmap(QPixmap())
            return
        
        try:
            # Convert frame data to QPixmap
            pixmap = QPixmap()
            if pixmap.loadFromData(frame_data):
                # Scale pixmap to fit the screen area while maintaining aspect ratio
                scaled_pixmap = pixmap.scaled(
                    self.screen_area.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.screen_area.setPixmap(scaled_pixmap)
                self.screen_area.setText("")  # Clear text when showing screen
            else:
                self.screen_area.setText("Failed to load screen data")
                
        except Exception as e:
            logger.error(f"Error setting screen frame for {self.username}: {e}")
            self.screen_area.setText("Error displaying screen")
    
    def clear_screen(self):
        """Clear screen and show placeholder."""
        self.screen_area.setText("No screen being shared")
        self.screen_area.setPixmap(QPixmap())

class UserBox(QWidget):
    """Individual user box widget for dynamic responsive grid."""
    
    def __init__(self, username: str, is_self: bool = False):
        super().__init__()
        self.username = username
        self.is_self = is_self
        self.is_speaking = False
        self.has_video = False
        self.avatar_color = generate_avatar_color(username)
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the user box UI matching reference images."""
        # Dynamic sizing - will be set by the grid layout
        self.setMinimumSize(200, 150)  # Minimum size for readability
        
        # Create a colored background frame to ensure color shows
        self.background_frame = QFrame(self)
        self.background_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.avatar_color};
                border: 2px solid transparent;
                border-radius: 12px;
            }}
        """)
        
        # Also set the UserBox style to override any parent styles
        self.setStyleSheet(f"""
            UserBox {{
                background-color: {self.avatar_color};
                border: none;
            }}
        """)
        
        # Video area (can show video or avatar)
        self.video_area = QLabel(self)
        self.video_area.setAlignment(Qt.AlignCenter)
        self.video_area.setScaledContents(True)
        
        # Store initials for fallback
        self.initials = ''.join([name[0].upper() for name in self.username.split()[:2]])
        
        # Set initial placeholder style and content
        self._set_placeholder_mode()
        
        # Username label (positioned at bottom left corner like reference)
        self.name_label = QLabel(self)
        display_name = f"{self.username}" if not self.is_self else f"{self.username}"
        self.name_label.setText(display_name)
        self.name_label.setStyleSheet("""
            QLabel {
                background-color: transparent;
                color: white;
                padding: 4px 8px;
                font-weight: 600;
                font-size: 14px;
                border: none;
            }
        """)
        self.name_label.adjustSize()
        
        # Microphone mute icon (top right corner like reference)
        from gui.icons import create_svg_icon
        self.mic_icon = QLabel(self)
        mic_off_icon = create_svg_icon(MICROPHONE_OFF_SVG, QSize(20, 20), "white")
        self.mic_icon.setPixmap(mic_off_icon.pixmap(QSize(20, 20)))
        self.mic_icon.setFixedSize(24, 24)
        self.mic_icon.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 0.5);
                border-radius: 12px;
                padding: 2px;
            }
        """)
        
        # Set initial speaking state
        self.update_speaking_state(False)
    
    def update_speaking_state(self, is_speaking: bool):
        """Update the visual state based on speaking status."""
        self.is_speaking = is_speaking
        
        # Apply green border when speaking, maintain colored background
        if is_speaking:
            if hasattr(self, 'background_frame'):
                self.background_frame.setStyleSheet(f"""
                    QFrame {{
                        background-color: {self.avatar_color};
                        border: 4px solid #4CAF50;
                        border-radius: 12px;
                    }}
                """)
        else:
            if hasattr(self, 'background_frame'):
                self.background_frame.setStyleSheet(f"""
                    QFrame {{
                        background-color: {self.avatar_color};
                        border: 2px solid transparent;
                        border-radius: 12px;
                    }}
                """)
    
    def _set_placeholder_mode(self):
        """Set the video area to show large initial letter like reference images."""
        self.has_video = False
        
        # Get first letter of username for avatar
        initial = self.username[0].upper() if self.username else "?"
        
        # Large initial letter styling matching reference images
        self.video_area.setStyleSheet("""
            QLabel {
                background-color: transparent;
                color: white;
                font-size: 72px;
                font-weight: bold;
                text-align: center;
                border: none;
            }
        """)
        self.video_area.setText(initial)
        self.video_area.setPixmap(QPixmap())  # Clear any existing pixmap
    
    def update_size(self, width: int, height: int):
        """Update the size and position elements matching reference images."""
        self.setFixedSize(width, height)
        
        # Resize background frame to fill the entire UserBox
        if hasattr(self, 'background_frame'):
            self.background_frame.setGeometry(0, 0, width, height)
        
        if hasattr(self, 'video_area'):
            if not self.has_video:
                # Avatar mode - fill entire box with large initial letter
                self.video_area.setGeometry(0, 0, width, height)
                
                # Calculate font size based on box size (like reference images)
                font_size = min(width, height) * 0.3  # 30% of smaller dimension
                font_size = max(32, min(font_size, 120))  # Clamp between 32-120px
                
                # Get first letter for avatar
                initial = self.username[0].upper() if self.username else "?"
                
                # Update styling for large initial letter
                self.video_area.setStyleSheet(f"""
                    QLabel {{
                        background-color: transparent;
                        color: white;
                        font-size: {int(font_size)}px;
                        font-weight: bold;
                        text-align: center;
                        border: none;
                    }}
                """)
                self.video_area.setText(initial)
            else:
                # Video mode - fill the entire box completely with rounded corners
                self.video_area.setGeometry(0, 0, width, height)
        
        # Position username label at bottom left corner (like reference images)
        if hasattr(self, 'name_label'):
            self.name_label.adjustSize()
            label_height = self.name_label.height()
            # Position at bottom left corner with margin
            self.name_label.move(12, height - label_height - 12)
        
        # Position microphone icon at top right corner (like reference images)
        if hasattr(self, 'mic_icon'):
            # Position at top right corner with margin
            self.mic_icon.move(width - 24 - 8, 8)
    
    def _set_video_mode(self):
        """Set the video area to show video frames."""
        self.has_video = True
        # Video fills the entire area with rounded corners to match the box
        self.video_area.setStyleSheet("""
            QLabel {
                background-color: #000;
                border-radius: 12px;
            }
        """)
        self.video_area.setText("")  # Clear text when showing video
    
    def set_video_frame(self, frame_data: bytes):
        """Set video frame for this user."""
        if not frame_data:
            # No video data, switch to placeholder
            self._set_placeholder_mode()
            return
        
        try:
            # Convert JPEG bytes to QPixmap
            pixmap = QPixmap()
            if pixmap.loadFromData(frame_data):
                # Switch to video mode if not already
                if not self.has_video:
                    logger.info(f"UserBox {self.username} switching to video mode")
                    self._set_video_mode()
                    # Update size to ensure video area fills the box
                    self.update_size(self.width(), self.height())
                
                # Scale pixmap to fit the video area while maintaining aspect ratio
                scaled_pixmap = pixmap.scaled(
                    self.video_area.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.video_area.setPixmap(scaled_pixmap)
                logger.debug(f"Video frame set for {self.username}, pixmap size: {scaled_pixmap.size()}")
            else:
                # Failed to load image, use placeholder
                logger.warning(f"Failed to load video frame data for {self.username}")
                self._set_placeholder_mode()
                
        except Exception as e:
            logger.error(f"Error setting video frame for {self.username}: {e}")
            self._set_placeholder_mode()
    
    def clear_video(self):
        """Clear video and return to placeholder mode."""
        self._set_placeholder_mode()
    
    def update_audio_state(self, is_audio_active: bool):
        """Update microphone icon based on audio state."""
        if hasattr(self, 'mic_icon'):
            from gui.icons import create_svg_icon
            if is_audio_active:
                # Show microphone icon (audio active)
                mic_icon = create_svg_icon(MICROPHONE_SVG, QSize(20, 20), "white")
            else:
                # Show muted microphone icon (audio inactive)
                mic_icon = create_svg_icon(MICROPHONE_OFF_SVG, QSize(20, 20), "white")
            
            self.mic_icon.setPixmap(mic_icon.pixmap(QSize(20, 20)))

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
        
        # Audio strength monitoring
        self.current_audio_strength = 0.0
        self.peak_audio_strength = 0.0
        self.audio_strength_timer = QTimer()
        self.audio_strength_timer.timeout.connect(self._update_audio_strength_display)
        self.audio_strength_timer.start(50)  # Update every 50ms for smooth display
        
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
    
    def resizeEvent(self, event):
        """Handle window resize events to update grid layout."""
        super().resizeEvent(event)
        
        # Prevent infinite resize loops by checking if size actually changed significantly
        if hasattr(self, 'user_grid_layout') and hasattr(self, '_last_resize_size'):
            old_size = self._last_resize_size
            new_size = (event.size().width(), event.size().height())
            
            # Only recreate grid if size changed by more than 50 pixels in either dimension
            width_diff = abs(new_size[0] - old_size[0])
            height_diff = abs(new_size[1] - old_size[1])
            
            if width_diff > 50 or height_diff > 50:
                self._last_resize_size = new_size
                self._schedule_grid_update()
        elif hasattr(self, 'user_grid_layout'):
            # First resize event
            self._last_resize_size = (event.size().width(), event.size().height())
            self._schedule_grid_update()
    
    def setup_ui(self):
        """Set up the main user interface without left sidebar."""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Main content area (full width)
        self.main_content = self.create_unified_media_view()
        main_layout.addWidget(self.main_content, 1)
        
        # Right sidebars (initially hidden)
        self.chat_sidebar = self.create_chat_sidebar()
        self.chat_sidebar.setVisible(False)
        main_layout.addWidget(self.chat_sidebar)
        
        self.users_sidebar = self.create_users_sidebar()
        self.users_sidebar.setVisible(False)
        main_layout.addWidget(self.users_sidebar)
        
        # Status bar
        self.setup_status_bar()
    

    
    def create_center_panel(self) -> QWidget:
        """Create center panel with unified user view and sidebar for chat."""
        panel = QWidget()
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Main content area (users and presentations)
        self.main_content = self.create_unified_media_view()
        layout.addWidget(self.main_content, 1)
        
        # Chat sidebar (initially hidden)
        self.chat_sidebar = self.create_chat_sidebar()
        self.chat_sidebar.setVisible(False)
        layout.addWidget(self.chat_sidebar)
        
        return panel
    
    def create_chat_sidebar(self) -> QWidget:
        """Create chat sidebar with chat and file sharing."""
        sidebar = QWidget()
        sidebar.setFixedWidth(350)  # Fixed width sidebar
        sidebar.setStyleSheet("""
            QWidget {
                background-color: #e9ecef;
                border-left: 1px solid #ddd;
            }
        """)
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Sidebar header with close button only
        header = QWidget()
        header.setFixedHeight(40)
        header.setStyleSheet("""
            QWidget {
                background-color: #dee2e6;
                border-bottom: 1px solid #ddd;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(10, 5, 10, 5)
        
        # Spacer to push close button to the right
        header_layout.addStretch()
        
        # Close button
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                font-size: 16px;
                font-weight: bold;
                color: #495057;
                border-radius: 15px;
            }
            QPushButton:hover {
                background-color: #ced4da;
                color: #212529;
            }
        """)
        close_btn.clicked.connect(self.hide_chat_sidebar)
        header_layout.addWidget(close_btn)
        
        layout.addWidget(header)
        
        # Tab widget for chat and files
        self.sidebar_tabs = QTabWidget()
        self.sidebar_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background-color: #e9ecef;
            }
            QTabBar::tab {
                background-color: #ced4da;
                color: #495057;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #f8f9fa;
                color: #212529;
                border-bottom: 2px solid #007bff;
            }
        """)
        
        # Chat tab
        chat_tab = self.create_chat_content()
        self.sidebar_tabs.addTab(chat_tab, "Chat")
        
        # Files tab
        files_tab = self.create_files_content()
        self.sidebar_tabs.addTab(files_tab, "Files")
        
        layout.addWidget(self.sidebar_tabs)
        
        return sidebar
    
    def create_users_sidebar(self) -> QWidget:
        """Create users sidebar with active users list."""
        sidebar = QWidget()
        sidebar.setFixedWidth(300)  # Fixed width sidebar
        sidebar.setStyleSheet("""
            QWidget {
                background-color: #e9ecef;
                border-left: 1px solid #ddd;
            }
        """)
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Sidebar header with close button only
        header = QWidget()
        header.setFixedHeight(40)
        header.setStyleSheet("""
            QWidget {
                background-color: #dee2e6;
                border-bottom: 1px solid #ddd;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(10, 5, 10, 5)
        
        # Spacer to push close button to the right
        header_layout.addStretch()
        
        # Close button
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(30, 30)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                font-size: 16px;
                font-weight: bold;
                color: #495057;
                border-radius: 15px;
            }
            QPushButton:hover {
                background-color: #ced4da;
                color: #212529;
            }
        """)
        close_btn.clicked.connect(self.hide_users_sidebar)
        header_layout.addWidget(close_btn)
        
        layout.addWidget(header)
        
        # Users list content
        users_content = QWidget()
        users_layout = QVBoxLayout(users_content)
        users_layout.setContentsMargins(15, 15, 15, 15)
        users_layout.setSpacing(10)
        
        # Active users label
        users_label = QLabel("Active Users")
        users_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #212529;
                margin-bottom: 10px;
            }
        """)
        users_layout.addWidget(users_label)
        
        # Users list widget
        self.users_list_widget = QListWidget()
        self.users_list_widget.setStyleSheet("""
            QListWidget {
                background-color: #f8f9fa;
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #dee2e6;
                border-radius: 4px;
                margin: 2px 0;
                color: #212529;
            }
            QListWidget::item:hover {
                background-color: #e9ecef;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
            }
        """)
        users_layout.addWidget(self.users_list_widget)
        
        users_layout.addStretch()
        
        layout.addWidget(users_content)
        
        return sidebar
    
    def create_chat_content(self) -> QWidget:
        """Create chat content for sidebar."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Chat history
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background-color: #fff;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 10px;
                font-size: 13px;
            }
        """)
        layout.addWidget(self.chat_display)
        
        # Input area
        input_layout = QVBoxLayout()
        
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Type your message...")
        self.chat_input.returnPressed.connect(self.handle_send_message)
        self.chat_input.setMinimumHeight(35)
        self.chat_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
                font-size: 13px;
            }
        """)
        input_layout.addWidget(self.chat_input)
        
        send_btn = QPushButton("Send Message")
        send_btn.setMinimumHeight(35)
        send_btn.clicked.connect(self.handle_send_message)
        send_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                font-weight: bold;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        input_layout.addWidget(send_btn)
        
        layout.addLayout(input_layout)
        
        return widget
    
    def create_files_content(self) -> QWidget:
        """Create files content for sidebar."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Upload section
        upload_group = QGroupBox("Share File")
        upload_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ddd;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        upload_layout = QVBoxLayout(upload_group)
        
        self.selected_file_label = QLabel("No file selected")
        self.selected_file_label.setStyleSheet("color: gray; font-size: 12px;")
        upload_layout.addWidget(self.selected_file_label)
        
        browse_btn = QPushButton("Browse Files...")
        browse_btn.clicked.connect(self.handle_browse_file)
        browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #545b62;
            }
        """)
        upload_layout.addWidget(browse_btn)
        
        upload_btn = QPushButton("Share File")
        upload_btn.clicked.connect(self.handle_upload_file)
        upload_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-weight: bold;
                padding: 8px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        upload_layout.addWidget(upload_btn)
        
        layout.addWidget(upload_group)
        
        # Available files list
        files_label = QLabel("Shared Files")
        files_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(files_label)
        
        self.files_list_widget = QListWidget()
        self.files_list_widget.itemDoubleClicked.connect(self.handle_download_file)
        self.files_list_widget.setStyleSheet("""
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: #fff;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:hover {
                background-color: #f8f9fa;
            }
        """)
        layout.addWidget(self.files_list_widget)
        
        # Download button
        download_btn = QPushButton("Download Selected")
        download_btn.clicked.connect(self.handle_download_file)
        download_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                padding: 8px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        layout.addWidget(download_btn)
        
        # Transfer progress
        self.transfer_progress = QProgressBar()
        self.transfer_progress.setVisible(False)
        layout.addWidget(self.transfer_progress)
        
        return widget
    
    def create_files_tab_old(self) -> QWidget:
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
    
    def create_unified_media_view(self) -> QWidget:
        """Create unified view with all users and presentations in one area."""
        widget = QWidget()
        
        # Set dark background like Google Meet, but exclude UserBox
        widget.setStyleSheet("""
            QWidget {
                background-color: #202124;
                color: white;
            }
            UserBox {
                background-color: none;
            }
        """)
        
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Main content area with users and presentations
        self.content_area = QWidget()
        self.content_area.setStyleSheet("""
            QWidget {
                background-color: #202124;
                border: none;
            }
            UserBox {
                background-color: none;
            }
        """)
        self.content_layout = QGridLayout(self.content_area)
        # Increased spacing between profile boxes and added margins from window edges
        self.content_layout.setSpacing(15)  # Gap between profile boxes
        self.content_layout.setContentsMargins(25, 25, 25, 25)  # Margin from window edges
        
        # Initialize user and presentation management
        self.user_boxes = {}  # username -> UserBox widget
        self.presentation_boxes = {}  # username -> PresentationBox widget
        self.user_order = []  # List of usernames in display order
        self._grid_updating = False  # Flag to prevent recursive grid updates
        self._grid_update_timer = QTimer()  # Timer for debouncing grid updates
        self._grid_update_timer.setSingleShot(True)
        self._grid_update_timer.timeout.connect(self._delayed_grid_update)
        
        # Create initial empty state
        self._create_dynamic_grid()
        
        layout.addWidget(self.content_area, 1)
        
        # Bottom control bar with chat icon
        self.create_bottom_controls_with_chat(layout)
        
        return widget
    
    def create_bottom_controls_with_chat(self, parent_layout):
        """Create bottom control bar with new layout: session ID (left), controls (center), users/chat (right)."""
        controls_container = QWidget()
        controls_container.setFixedHeight(80)
        controls_container.setStyleSheet("""
            QWidget {
                background-color: #1a1a1a;
                border-top: 1px solid #333;
            }
        """)
        
        controls_layout = QHBoxLayout(controls_container)
        controls_layout.setContentsMargins(20, 15, 20, 15)
        controls_layout.setSpacing(15)
        
        # Left side - Session ID with popup
        left_layout = QHBoxLayout()
        
        # Session ID button
        self.session_btn = QPushButton(f"Session: {self.session_id}")
        self.session_btn.setStyleSheet("""
            QPushButton {
                background-color: #3c4043;
                border: none;
                border-radius: 6px;
                font-size: 12px;
                color: white;
                padding: 8px 12px;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #5f6368;
            }
            QPushButton:pressed {
                background-color: #2d2d2d;
            }
        """)
        self.session_btn.clicked.connect(self.toggle_session_info)
        left_layout.addWidget(self.session_btn)
        
        controls_layout.addLayout(left_layout)
        
        # Center spacer
        controls_layout.addStretch()
        
        # Center - main controls
        center_layout = QHBoxLayout()
        center_layout.setSpacing(15)
        
        # Audio button (initially OFF)
        self.audio_btn = QPushButton()
        self.audio_btn.setFixedSize(50, 50)
        self.audio_btn.clicked.connect(self.toggle_audio)
        # Set initial OFF state with SVG icon
        set_button_icon(self.audio_btn, MICROPHONE_SVG, False)
        center_layout.addWidget(self.audio_btn)
        
        # Video button (initially OFF)
        self.video_btn = QPushButton()
        self.video_btn.setFixedSize(50, 50)
        self.video_btn.clicked.connect(self.toggle_video)
        # Set initial OFF state with SVG icon
        set_button_icon(self.video_btn, VIDEO_SVG, False)
        center_layout.addWidget(self.video_btn)
        
        # Screen share button (initially OFF)
        self.screen_share_btn = QPushButton()
        self.screen_share_btn.setFixedSize(50, 50)
        self.screen_share_btn.clicked.connect(self.toggle_screen_share)
        # Set initial OFF state with SVG icon
        set_button_icon(self.screen_share_btn, SCREEN_SHARE_SVG, False)
        center_layout.addWidget(self.screen_share_btn)
        
        # End session button (renamed from leave)
        self.end_session_btn = QPushButton()
        self.end_session_btn.setFixedSize(50, 50)
        self.end_session_btn.clicked.connect(self.handle_leave_session)
        # Set hangup icon with red background
        from gui.icons import create_svg_icon
        hangup_icon = create_svg_icon(PHONE_HANGUP_SVG, QSize(24, 24), "white")
        self.end_session_btn.setIcon(hangup_icon)
        self.end_session_btn.setIconSize(QSize(24, 24))
        self.end_session_btn.setStyleSheet("""
            QPushButton {
                background-color: #ea4335;
                border: none;
                border-radius: 25px;
            }
            QPushButton:hover {
                background-color: #d33b2c;
            }
            QPushButton:pressed {
                background-color: #b52d20;
            }
        """)
        center_layout.addWidget(self.end_session_btn)
        
        controls_layout.addLayout(center_layout)
        
        # Right spacer
        controls_layout.addStretch()
        
        # Right side - Users and Chat buttons
        right_layout = QHBoxLayout()
        right_layout.setSpacing(10)
        
        # Users button
        self.users_btn = QPushButton()
        self.users_btn.setFixedSize(50, 50)
        self.users_btn.clicked.connect(self.toggle_users_sidebar)
        # Set users icon
        users_icon = create_svg_icon(USERS_SVG, QSize(24, 24), "white")
        self.users_btn.setIcon(users_icon)
        self.users_btn.setIconSize(QSize(24, 24))
        self.users_btn.setStyleSheet("""
            QPushButton {
                background-color: #3c4043;
                border: none;
                border-radius: 25px;
            }
            QPushButton:hover {
                background-color: #5f6368;
            }
            QPushButton:pressed {
                background-color: #2d2d2d;
            }
        """)
        right_layout.addWidget(self.users_btn)
        
        # Chat button
        self.chat_btn = QPushButton()
        self.chat_btn.setFixedSize(50, 50)
        self.chat_btn.clicked.connect(self.toggle_chat_sidebar)
        # Set chat icon
        chat_icon = create_svg_icon(CHAT_SVG, QSize(24, 24), "white")
        self.chat_btn.setIcon(chat_icon)
        self.chat_btn.setIconSize(QSize(24, 24))
        self.chat_btn.setStyleSheet("""
            QPushButton {
                background-color: #3c4043;
                border: none;
                border-radius: 25px;
            }
            QPushButton:hover {
                background-color: #5f6368;
            }
            QPushButton:pressed {
                background-color: #2d2d2d;
            }
        """)
        right_layout.addWidget(self.chat_btn)
        
        controls_layout.addLayout(right_layout)
        
        parent_layout.addWidget(controls_container)
        
        # Create session info popup (initially hidden)
        self.create_session_info_popup()
    


    
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
        Add a user to the user list and grid.
        
        Args:
            username: Username to add
            user_info: Dictionary with user information
        """
        if username == self.username:
            return  # Don't add self
        
        self.connected_users[username] = user_info
        
        # Add to user grid
        self.add_user_to_grid(username, user_info)
        
        # Update users sidebar if it exists
        if hasattr(self, 'users_list_widget'):
            self.update_users_list()
        
        # Update session details
        if hasattr(self, 'session_details'):
            self.update_session_details()
        
        logger.info(f"Added user '{username}' to user list and grid")
    
    def remove_user(self, username: str):
        """Remove a user from the user list and grid."""
        if username in self.connected_users:
            del self.connected_users[username]
        
        # Remove from user grid
        self.remove_user_from_grid(username)
        
        # Update users sidebar if it exists
        if hasattr(self, 'users_list_widget'):
            self.update_users_list()
        
        # Update session details
        if hasattr(self, 'session_details'):
            self.update_session_details()
        
        logger.info(f"Removed user '{username}' from user list and grid")
        
        # Also remove video display
        self.remove_user_video(username)
    
    def get_selected_users(self) -> list:
        """Get list of all connected users (for broadcast messaging)."""
        # Since we removed user selection, return all connected users for broadcast
        return list(self.connected_users.keys())
    

    

    
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
                self._update_audio_button_state(True)
                self.error_manager.update_component_status('audio', 'active', 'Audio streaming started')
                self.show_success_notification("Audio Started", "Audio streaming is now active")
                # Update microphone icon for self
                if self.username in self.user_boxes:
                    self.user_boxes[self.username].update_audio_state(True)
                logger.info("Audio started")
            else:
                self.stop_audio.emit()
                self.audio_active = False
                self._update_audio_button_state(False)
                self.error_manager.update_component_status('audio', 'inactive', 'Audio streaming stopped')
                # Update microphone icon for self
                if self.username in self.user_boxes:
                    self.user_boxes[self.username].update_audio_state(False)
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
                self._update_video_button_state(True)
                self.error_manager.update_component_status('video', 'active', 'Video streaming started')
                self.show_success_notification("Video Started", "Video streaming is now active")
                logger.info("Video started")
            else:
                self.stop_video.emit()
                self.video_active = False
                self._update_video_button_state(False)
                self.error_manager.update_component_status('video', 'inactive', 'Video streaming stopped')
                # Clear self video
                self.set_self_video_active(False)
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
                self._update_screen_share_button_state(True)
                self.error_manager.update_component_status('screen_share', 'active', 'Screen sharing started')
                self.show_success_notification("Screen Share Started", "Screen sharing is now active")
                
                # Add presentation box for self
                self.add_presentation_box(self.username)
                
                logger.info("Screen sharing started")
            else:
                self.stop_screen_share.emit()
                self.screen_share_active = False
                self._update_screen_share_button_state(False)
                self.error_manager.update_component_status('screen_share', 'inactive', 'Screen sharing stopped')
                
                # Remove presentation box for self
                self.remove_presentation_box(self.username)
                
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
    
    def _update_audio_button_state(self, is_active: bool):
        """Update audio button appearance based on state."""
        set_button_icon(self.audio_btn, MICROPHONE_SVG, is_active)
    
    def _update_video_button_state(self, is_active: bool):
        """Update video button appearance based on state."""
        set_button_icon(self.video_btn, VIDEO_SVG, is_active)
    
    def _update_screen_share_button_state(self, is_active: bool):
        """Update screen share button appearance based on state."""
        set_button_icon(self.screen_share_btn, SCREEN_SHARE_SVG, is_active)
    
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
    
    def update_screen_frame(self, username: str, frame_data: bytes, width: int = 0, height: int = 0):
        """
        Update screen frame for a user's presentation.
        
        Args:
            username: Username of the screen sharer
            frame_data: JPEG screen frame data
            width: Frame width
            height: Frame height
        """
        # Ensure presentation box exists for this user
        if username not in self.presentation_boxes:
            self.add_presentation_box(username)
        
        # Update the presentation box with the screen frame
        if username in self.presentation_boxes:
            self.presentation_boxes[username].set_screen_frame(frame_data, width, height)
    
    def update_screen_frame_old(self, frame_data: bytes, width: int = 0, height: int = 0):
        """
        Update shared screen display (old method for backward compatibility).
        
        Args:
            frame_data: JPEG screen frame data
            width: Frame width
            height: Frame height
        """
        # This method is kept for backward compatibility
        # New implementation uses presentation boxes
        pass
    
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
    
    def toggle_chat_sidebar(self):
        """Toggle the chat sidebar visibility."""
        if self.chat_sidebar.isVisible():
            self.hide_chat_sidebar()
        else:
            # Hide users sidebar if open
            if self.users_sidebar.isVisible():
                self.hide_users_sidebar()
            self.show_chat_sidebar()
    
    def toggle_users_sidebar(self):
        """Toggle the users sidebar visibility."""
        if self.users_sidebar.isVisible():
            self.hide_users_sidebar()
        else:
            # Hide chat sidebar if open
            if self.chat_sidebar.isVisible():
                self.hide_chat_sidebar()
            self.show_users_sidebar()
    
    def show_chat_sidebar(self):
        """Show the chat sidebar."""
        self.chat_sidebar.setVisible(True)
        self.chat_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                border: none;
                border-radius: 25px;
                font-size: 20px;
                color: white;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
        """)
    
    def hide_chat_sidebar(self):
        """Hide the chat sidebar."""
        self.chat_sidebar.setVisible(False)
        self.chat_btn.setStyleSheet("""
            QPushButton {
                background-color: #3c4043;
                border: none;
                border-radius: 25px;
                font-size: 20px;
                color: white;
            }
            QPushButton:hover {
                background-color: #5f6368;
            }
            QPushButton:pressed {
                background-color: #2d2d2d;
            }
        """)
    
    def show_users_sidebar(self):
        """Show the users sidebar."""
        self.users_sidebar.setVisible(True)
        self.users_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                border: none;
                border-radius: 25px;
                font-size: 20px;
                color: white;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
        """)
        # Update users list
        self.update_users_list()
    
    def hide_users_sidebar(self):
        """Hide the users sidebar."""
        self.users_sidebar.setVisible(False)
        self.users_btn.setStyleSheet("""
            QPushButton {
                background-color: #3c4043;
                border: none;
                border-radius: 25px;
                font-size: 20px;
                color: white;
            }
            QPushButton:hover {
                background-color: #5f6368;
            }
            QPushButton:pressed {
                background-color: #2d2d2d;
            }
        """)
    
    def create_session_info_popup(self):
        """Create session info popup widget."""
        self.session_info_popup = QWidget(self)
        self.session_info_popup.setFixedSize(250, 180)
        self.session_info_popup.setStyleSheet("""
            QWidget {
                background-color: #fff;
                border: 2px solid #ddd;
                border-radius: 8px;
            }
        """)
        self.session_info_popup.setVisible(False)
        
        layout = QVBoxLayout(self.session_info_popup)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)
        
        # Session details
        session_label = QLabel(f"Session ID: {self.session_id}")
        session_label.setStyleSheet("font-weight: bold; color: #333;")
        layout.addWidget(session_label)
        
        server_label = QLabel(f"Server IP: {self.server_address}")
        server_label.setStyleSheet("color: #666;")
        layout.addWidget(server_label)
        
        # TCP/UDP ports (will be updated when connected)
        self.tcp_port_label = QLabel("TCP Port: --")
        self.tcp_port_label.setStyleSheet("color: #666;")
        layout.addWidget(self.tcp_port_label)
        
        self.udp_port_label = QLabel("UDP Port: --")
        self.udp_port_label.setStyleSheet("color: #666;")
        layout.addWidget(self.udp_port_label)
        
        # Copy button
        copy_btn = QPushButton("📋 Copy Info")
        copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px;
                font-weight: bold;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        copy_btn.clicked.connect(self.copy_session_info)
        layout.addWidget(copy_btn)
    
    def toggle_session_info(self):
        """Toggle session info popup visibility."""
        if self.session_info_popup.isVisible():
            self.session_info_popup.setVisible(False)
        else:
            # Position popup above session button
            session_btn_pos = self.session_btn.mapToGlobal(self.session_btn.rect().topLeft())
            popup_x = session_btn_pos.x()
            popup_y = session_btn_pos.y() - self.session_info_popup.height() - 10
            
            # Convert to parent widget coordinates
            parent_pos = self.mapFromGlobal(session_btn_pos)
            popup_x = parent_pos.x()
            popup_y = parent_pos.y() - self.session_info_popup.height() - 10
            
            self.session_info_popup.move(popup_x, popup_y)
            self.session_info_popup.setVisible(True)
            self.session_info_popup.raise_()
    
    def update_session_details(self):
        """Update session details in users sidebar."""
        if hasattr(self, 'session_details'):
            details_text = f"""Session ID: {self.session_id}
Server: {self.server_address}
Role: {'Host' if self.is_host else 'Participant'}
Users: {len(self.connected_users) + 1}"""
            self.session_details.setText(details_text)
    
    def update_users_list(self):
        """Update the users list in the sidebar."""
        if hasattr(self, 'users_list_widget'):
            self.users_list_widget.clear()
            
            # Add self first
            self_item = QListWidgetItem(f"👤 {self.username} (You)")
            self_item.setData(Qt.UserRole, self.username)
            self.users_list_widget.addItem(self_item)
            
            # Add other users
            for username in self.connected_users:
                user_item = QListWidgetItem(f"👤 {username}")
                user_item.setData(Qt.UserRole, username)
                self.users_list_widget.addItem(user_item)
    
    @Slot()
    def copy_session_info(self):
        """Copy session ID and server address to clipboard."""
        try:
            from PySide6.QtGui import QGuiApplication
            
            # Get port information if available
            tcp_port = "Unknown"
            udp_port = "Unknown"
            if hasattr(self, 'media_manager') and self.media_manager:
                # Try to get port info from client
                if hasattr(self.media_manager, 'client'):
                    tcp_port = getattr(self.media_manager.client, 'tcp_port', 'Unknown')
                    udp_port = getattr(self.media_manager.client, 'udp_port', 'Unknown')
            
            # Create formatted session info
            session_info = f"""Session ID: {self.session_id}
Server IP: {self.server_address}
TCP Port: {tcp_port}
UDP Port: {udp_port}
Role: {'Host' if self.is_host else 'Participant'}"""
            
            # Copy to clipboard
            clipboard = QGuiApplication.clipboard()
            clipboard.setText(session_info)
            
            # Hide session popup if visible
            if hasattr(self, 'session_info_popup'):
                self.session_info_popup.setVisible(False)
            
            # Show success notification
            self.show_success_notification(
                "Session Info Copied", 
                f"Session information copied to clipboard!"
            )
            
            logger.info(f"Session info copied to clipboard")
            
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
    # ========================================================================
    # Audio Strength Monitoring Methods
    # ========================================================================
    
    def set_media_manager(self, media_manager):
        """
        Set the media manager reference for audio strength monitoring.
        
        Args:
            media_manager: MediaCaptureManager instance
        """
        self.media_manager = media_manager
        if media_manager:
            # Set up audio strength callback
            media_manager.set_audio_strength_callback(self._on_audio_strength_update)
            logger.info("Audio strength monitoring connected to media manager")
    
    def _on_audio_strength_update(self, current_strength: float, peak_strength: float):
        """
        Callback for audio strength updates from media manager.
        
        Args:
            current_strength: Current audio strength (0.0 to 1.0)
            peak_strength: Peak audio strength (0.0 to 1.0)
        """
        # Store values for display update
        self.current_audio_strength = current_strength
        self.peak_audio_strength = peak_strength
    
    def _update_audio_strength_display(self):
        """Update the user grid based on speaking status."""
        try:
            # Check if user is speaking
            is_speaking = False
            if hasattr(self, 'media_manager') and self.media_manager:
                is_speaking = self.media_manager.is_user_speaking()
            
            # Update self speaking state in grid (visual only - no grid refresh needed)
            if self.username in self.user_boxes:
                self.user_boxes[self.username].update_speaking_state(is_speaking)
            
            # Note: No grid refresh needed for speaking state changes
            # Speaking state only affects visual appearance (green border), not layout
                
        except Exception as e:
            logger.error(f"Error updating audio strength display: {e}")
    
    def reset_peak_audio_strength(self):
        """Reset the peak audio strength measurement."""
        if hasattr(self, 'media_manager') and self.media_manager:
            self.media_manager.reset_peak_audio_strength()
            logger.info("Peak audio strength reset")

    # ========================================================================
    # Google Meet-Style User Grid Methods
    # ========================================================================
    
    def _calculate_optimal_grid(self, user_count: int) -> tuple:
        """Calculate optimal grid dimensions based on user count."""
        if user_count == 0:
            return (1, 1)
        elif user_count == 1:
            return (1, 1)  # Single user takes full space
        elif user_count == 2:
            return (1, 2)  # Two users side by side
        elif user_count <= 4:
            return (2, 2)  # 2x2 grid for 3-4 users
        elif user_count <= 6:
            return (2, 3)  # 2x3 grid for 5-6 users
        elif user_count <= 9:
            return (3, 3)  # 3x3 grid for 7-9 users
        elif user_count <= 12:
            return (3, 4)  # 3x4 grid for 10-12 users
        else:
            return (4, 4)  # 4x4 grid for more users
    
    def _create_dynamic_grid(self):
        """Create dynamic grid layout based on current user count."""
        # Prevent recursive grid updates
        if self._grid_updating:
            return
        
        self._grid_updating = True
        
        try:
            # Clear existing layout
            for i in reversed(range(self.content_layout.count())):
                widget = self.content_layout.itemAt(i).widget()
                if widget:
                    widget.setParent(None)
            
            # Get all users (always show all users in session)
            all_users = []
            
            # Always add self first
            all_users.append(self.username)
            
            # Add other users
            all_users.extend(self.user_order)
            
            user_count = len(all_users)
            
            if user_count == 0:
                # Show welcome message when no users and no active media
                welcome_label = QLabel("🎉 Welcome to LAN Communicator!\n\nClick the video or audio button below to start.\nYou'll see yourself here, and others will appear as they join.")
                welcome_label.setAlignment(Qt.AlignCenter)
                welcome_label.setStyleSheet("""
                    QLabel {
                        font-size: 18px;
                        color: #666;
                        padding: 40px;
                        background-color: #f8f9fa;
                        border: 2px dashed #ddd;
                        border-radius: 15px;
                    }
                """)
                self.content_layout.addWidget(welcome_label, 0, 0)
                return
            
            # Calculate optimal grid dimensions for users and presentations
            total_items = user_count + len(self.presentation_boxes)
            rows, cols = self._calculate_optimal_grid(total_items)
            
            current_position = 0
            
            # Add users to grid first
            for i, username in enumerate(all_users):
                if current_position >= rows * cols:
                    break  # Don't exceed grid capacity
                
                row = current_position // cols
                col = current_position % cols
                
                # Create or get user box
                if username not in self.user_boxes:
                    is_self = (username == self.username)
                    self.user_boxes[username] = UserBox(username, is_self=is_self)
                
                user_box = self.user_boxes[username]
                
                # Set dynamic size based on grid dimensions and available space
                self._resize_user_box(user_box, rows, cols, total_items)
                
                self.content_layout.addWidget(user_box, row, col)
                current_position += 1
            
            # Add presentation boxes
            for username, presentation_box in self.presentation_boxes.items():
                if current_position >= rows * cols:
                    break  # Don't exceed grid capacity
                
                row = current_position // cols
                col = current_position % cols
                
                # Set dynamic size for presentation box
                self._resize_presentation_box(presentation_box, rows, cols, total_items)
                
                self.content_layout.addWidget(presentation_box, row, col)
                current_position += 1
            
            # Set grid layout properties for optimal spacing
            for i in range(rows):
                self.content_layout.setRowStretch(i, 1)
            for j in range(cols):
                self.content_layout.setColumnStretch(j, 1)
                
        finally:
            # Always reset the flag to allow future updates
            self._grid_updating = False
    
    def _delayed_grid_update(self):
        """Delayed grid update to prevent rapid successive updates."""
        if not self._grid_updating:
            self._create_dynamic_grid()
    
    def _schedule_grid_update(self):
        """Schedule a debounced grid update."""
        # Stop any existing timer and start a new one
        self._grid_update_timer.stop()
        self._grid_update_timer.start(50)  # 50ms debounce delay
    
    def _resize_user_box(self, user_box: UserBox, rows: int, cols: int, total_items: int):
        """Dynamically resize user box based on grid layout."""
        # Get the actual available space from the content area
        content_widget = self.content_area
        available_width = content_widget.width() if content_widget.width() > 0 else 800
        available_height = content_widget.height() if content_widget.height() > 0 else 600
        
        # Account for margins and spacing
        margin = 20
        spacing = 10
        
        # Calculate size per box
        box_width = (available_width - margin - (cols - 1) * spacing) // cols
        box_height = (available_height - margin - (rows - 1) * spacing) // rows
        
        # Ensure minimum readable size
        box_width = max(box_width, 200)
        box_height = max(box_height, 150)
        
        # For single item, make it larger and more cinematic
        if total_items == 1:
            box_width = min(available_width - margin, 700)
            box_height = min(available_height - margin, 500)
        
        # Use the new update_size method
        user_box.update_size(box_width, box_height)
    
    def _resize_presentation_box(self, presentation_box: PresentationBox, rows: int, cols: int, total_items: int):
        """Dynamically resize presentation box based on grid layout."""
        # Get the actual available space from the content area
        content_widget = self.content_area
        available_width = content_widget.width() if content_widget.width() > 0 else 800
        available_height = content_widget.height() if content_widget.height() > 0 else 600
        
        # Account for margins and spacing
        margin = 20
        spacing = 10
        
        # Calculate size per box
        box_width = (available_width - margin - (cols - 1) * spacing) // cols
        box_height = (available_height - margin - (rows - 1) * spacing) // rows
        
        # Ensure minimum readable size for presentations (larger than user boxes)
        box_width = max(box_width, 300)
        box_height = max(box_height, 200)
        
        # For single item, make it larger
        if total_items == 1:
            box_width = min(available_width - margin, 900)
            box_height = min(available_height - margin, 600)
        
        presentation_box.update_size(box_width, box_height)
    
    def add_user_to_grid(self, username: str, user_info: dict = None):
        """Add a user to the dynamic grid system."""
        if username == self.username:
            # Self is handled automatically in _create_dynamic_grid based on media state
            self._schedule_grid_update()
            return
        
        if username not in self.user_order:
            # Add to user order (new users go to the end)
            self.user_order.append(username)
            
            # Schedule grid update with debouncing
            self._schedule_grid_update()
            
            logger.info(f"Added user '{username}' to dynamic grid")
    
    def remove_user_from_grid(self, username: str):
        """Remove a user from the dynamic grid system."""
        # Remove from user order
        if username in self.user_order:
            self.user_order.remove(username)
        
        # Remove widget if it exists
        if username in self.user_boxes:
            user_box = self.user_boxes.pop(username)
            user_box.setParent(None)
        
        # Schedule grid update with debouncing
        self._schedule_grid_update()
        
        logger.info(f"Removed user '{username}' from dynamic grid")
    
    def add_presentation_box(self, username: str):
        """Add a presentation box for screen sharing."""
        if username not in self.presentation_boxes:
            self.presentation_boxes[username] = PresentationBox(username)
            self._schedule_grid_update()
            logger.info(f"Added presentation box for '{username}'")
    
    def remove_presentation_box(self, username: str):
        """Remove a presentation box."""
        if username in self.presentation_boxes:
            presentation_box = self.presentation_boxes.pop(username)
            presentation_box.setParent(None)
            self._schedule_grid_update()
            logger.info(f"Removed presentation box for '{username}'")
    
    def _update_page_navigation(self):
        """Update page navigation visibility and state."""
        total_users = len(self.user_order)
        if self.audio_active or self.video_active:
            total_users += 1  # Include self when media is active
        
        # For now, disable pagination since we're using dynamic grid
        # In the future, this could be used for very large groups (>16 users)
        if hasattr(self, 'prev_page_btn'):
            self.prev_page_btn.setVisible(False)
        if hasattr(self, 'next_page_btn'):
            self.next_page_btn.setVisible(False)
        if hasattr(self, 'page_label'):
            self.page_label.setVisible(False)
    
    def update_user_speaking_state(self, username: str, is_speaking: bool):
        """Update speaking state for a user."""
        if username in self.user_boxes:
            user_box = self.user_boxes[username]
            user_box.update_speaking_state(is_speaking)
            
            # Only move speaking user to front for large groups (>9 users)
            # For small groups, avoid unnecessary grid refreshes
            total_users = len(self.user_order) + (1 if self.audio_active or self.video_active else 0)
            if is_speaking and total_users > 9 and username not in self._get_current_page_users():
                self._move_user_to_front(username)
    
    def _move_user_to_front(self, username: str):
        """Move a speaking user to the front of the grid."""
        if username in self.user_order:
            # Remove from current position
            self.user_order.remove(username)
            # Add to front
            self.user_order.insert(0, username)
            
            # Go to first page to show the speaking user
            self.current_page = 0
            self._refresh_grid()
            
            logger.info(f"Moved speaking user '{username}' to front")
    
    def _get_current_page_users(self) -> list:
        """Get list of users on current page."""
        start_idx = self.current_page * self.users_per_page
        end_idx = start_idx + self.users_per_page
        return self.user_order[start_idx:end_idx]
    
    def _refresh_grid(self):
        """Refresh the dynamic grid display."""
        # Simply recreate the dynamic grid
        self._create_dynamic_grid()
        
        # Update page navigation (if still needed for very large groups)
        self._update_page_navigation()
        self._update_page_navigation()
    
    def _update_page_navigation(self):
        """Update page navigation buttons and label."""
        total_users = len(self.user_order)
        if self.audio_active:
            total_users += 1  # Include self
        
        total_pages = max(1, (total_users + self.users_per_page - 1) // self.users_per_page)
        
        # Update label
        self.page_label.setText(f"Page {self.current_page + 1} of {total_pages}")
        
        # Update button states
        self.prev_page_btn.setEnabled(self.current_page > 0)
        self.next_page_btn.setEnabled(self.current_page < total_pages - 1)
    
    def previous_page(self):
        """Go to previous page."""
        if self.current_page > 0:
            self.current_page -= 1
            self._refresh_grid()
    
    def next_page(self):
        """Go to next page."""
        total_users = len(self.user_order)
        if self.audio_active:
            total_users += 1
        total_pages = max(1, (total_users + self.users_per_page - 1) // self.users_per_page)
        
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self._refresh_grid()   
 # ========================================================================
    # Video Management Methods
    # ========================================================================
    
    def update_user_video_frame(self, username: str, frame_data: bytes):
        """Update video frame for a specific user."""
        logger.info(f"🎬 GUI: update_user_video_frame called for {username}, {len(frame_data)} bytes")
        if username in self.user_boxes:
            logger.info(f"🎬 GUI: Found user box for {username}, calling set_video_frame")
            self.user_boxes[username].set_video_frame(frame_data)
        else:
            logger.warning(f"No user box found for {username}")
            # Try to create the user box if it doesn't exist
            if username == self.username and (self.audio_active or self.video_active):
                logger.info(f"Creating user box for self ({username}) since media is active")
                self._create_dynamic_grid()
    
    def clear_user_video(self, username: str):
        """Clear video for a specific user (return to initials)."""
        if username in self.user_boxes:
            self.user_boxes[username].clear_video()
    
    def set_self_video_active(self, active: bool):
        """Set video active state for self."""
        if self.username in self.user_boxes:
            if not active:
                self.user_boxes[self.username].clear_video()
    
    def update_video_frame(self, username: str, video_data: bytes):
        """Handle received video frame (called from app.py)."""
        logger.info(f"🎬 GUI: update_video_frame called for {username}, {len(video_data)} bytes")
        self.update_user_video_frame(username, video_data)
    
    def update_user_audio_state(self, username: str, is_speaking: bool):
        """Update audio speaking state for a user."""
        if username in self.user_boxes:
            self.user_boxes[username].update_speaking_state(is_speaking)
            logger.debug(f"Updated speaking state for {username}: {is_speaking}")
    
    def handle_audio_data_received(self, username: str, audio_data: bytes):
        """Handle received audio data and detect speaking."""
        logger.info(f"🎵 GUI: handle_audio_data_received called for {username}, {len(audio_data)} bytes")
        # For now, we'll assume any audio data means the user is speaking
        # In a more sophisticated implementation, we would analyze the audio level
        if username in self.user_boxes:
            # Simple speaking detection: if we receive audio data, user is speaking
            # This will be updated when we receive the next audio packet or after a timeout
            self.user_boxes[username].update_speaking_state(True)
            
            # Set a timer to reset speaking state after a short delay
            if not hasattr(self, 'speaking_timers'):
                self.speaking_timers = {}
            
            # Cancel existing timer for this user
            if username in self.speaking_timers:
                self.speaking_timers[username].stop()
            
            # Create new timer to reset speaking state
            timer = QTimer()
            timer.setSingleShot(True)
            timer.timeout.connect(lambda: self._reset_speaking_state(username))
            timer.start(500)  # Reset after 500ms of no audio
            self.speaking_timers[username] = timer
    
    def _reset_speaking_state(self, username: str):
        """Reset speaking state for a user."""
        if username in self.user_boxes:
            self.user_boxes[username].update_speaking_state(False)
            logger.debug(f"Reset speaking state for {username}")
        
        # Clean up timer
        if hasattr(self, 'speaking_timers') and username in self.speaking_timers:
            del self.speaking_timers[username]