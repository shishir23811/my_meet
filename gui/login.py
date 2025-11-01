"""
LoginWindow for LAN Communication Application.
Provides sign in and sign up functionality with profile management.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QTabWidget, QCheckBox, QMessageBox, QFrame
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont
from utils.logger import setup_logger
from utils.profiles import profile_manager
from utils.config import config

logger = setup_logger(__name__)

class LoginWindow(QWidget):
    """
    Login window with Sign In and Sign Up tabs.
    Emits login_successful signal when authentication succeeds.
    """
    
    # Signal emitted when user successfully logs in
    login_successful = Signal(str)  # username
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LAN Communicator - Login")
        self.resize(400, 500)
        self.setup_ui()
        self.load_remember_me()
        logger.info("LoginWindow initialized")
    
    def setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # App title
        title = QLabel("LAN Communicator")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        subtitle = QLabel("Local Area Network Communication System")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: gray;")
        layout.addWidget(subtitle)
        
        # Tab widget for Sign In / Sign Up
        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self.create_signin_tab(), "Sign In")
        self.tab_widget.addTab(self.create_signup_tab(), "Sign Up")
        layout.addWidget(self.tab_widget)
        
        layout.addStretch()
    
    def create_signin_tab(self) -> QWidget:
        """Create the Sign In tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Username field
        layout.addWidget(QLabel("Username:"))
        self.signin_username = QLineEdit()
        self.signin_username.setPlaceholderText("Enter your username")
        self.signin_username.returnPressed.connect(self.handle_signin)
        layout.addWidget(self.signin_username)
        
        # Password field
        layout.addWidget(QLabel("Password:"))
        self.signin_password = QLineEdit()
        self.signin_password.setPlaceholderText("Enter your password")
        self.signin_password.setEchoMode(QLineEdit.Password)
        self.signin_password.returnPressed.connect(self.handle_signin)
        layout.addWidget(self.signin_password)
        
        # Remember me checkbox
        self.remember_me_checkbox = QCheckBox("Remember me")
        layout.addWidget(self.remember_me_checkbox)
        
        # Sign in button
        signin_btn = QPushButton("Sign In")
        signin_btn.setMinimumHeight(40)
        signin_btn.clicked.connect(self.handle_signin)
        layout.addWidget(signin_btn)
        
        # Forgot password placeholder
        forgot_password_btn = QPushButton("Forgot Password?")
        forgot_password_btn.setFlat(True)
        forgot_password_btn.setStyleSheet("text-decoration: underline; color: blue;")
        forgot_password_btn.clicked.connect(self.handle_forgot_password)
        layout.addWidget(forgot_password_btn)
        
        layout.addStretch()
        return tab
    
    def create_signup_tab(self) -> QWidget:
        """Create the Sign Up tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Username field
        layout.addWidget(QLabel("Username:"))
        self.signup_username = QLineEdit()
        self.signup_username.setPlaceholderText("Choose a username")
        layout.addWidget(self.signup_username)
        
        # Display name field
        layout.addWidget(QLabel("Display Name:"))
        self.signup_display_name = QLineEdit()
        self.signup_display_name.setPlaceholderText("Your display name")
        layout.addWidget(self.signup_display_name)
        
        # Password field
        layout.addWidget(QLabel("Password:"))
        self.signup_password = QLineEdit()
        self.signup_password.setPlaceholderText("Choose a password")
        self.signup_password.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.signup_password)
        
        # Confirm password field
        layout.addWidget(QLabel("Confirm Password:"))
        self.signup_confirm_password = QLineEdit()
        self.signup_confirm_password.setPlaceholderText("Confirm your password")
        self.signup_confirm_password.setEchoMode(QLineEdit.Password)
        self.signup_confirm_password.returnPressed.connect(self.handle_signup)
        layout.addWidget(self.signup_confirm_password)
        
        # Sign up button
        signup_btn = QPushButton("Sign Up")
        signup_btn.setMinimumHeight(40)
        signup_btn.clicked.connect(self.handle_signup)
        layout.addWidget(signup_btn)
        
        layout.addStretch()
        return tab
    
    def handle_signin(self):
        """Handle sign in button click."""
        username = self.signin_username.text().strip()
        password = self.signin_password.text()
        
        if not username or not password:
            QMessageBox.warning(self, "Input Error", "Please enter both username and password.")
            return
        
        # Authenticate user
        if profile_manager.authenticate(username, password):
            logger.info(f"User '{username}' signed in successfully")
            
            # Save remember me preference
            config.set('ui.remember_me', self.remember_me_checkbox.isChecked())
            if self.remember_me_checkbox.isChecked():
                config.set('ui.last_username', username)
            else:
                config.set('ui.last_username', '')
            config.save()
            
            # Emit success signal
            self.login_successful.emit(username)
        else:
            QMessageBox.critical(self, "Authentication Failed", 
                               "Invalid username or password.")
            logger.warning(f"Failed sign in attempt for user '{username}'")
    
    def handle_signup(self):
        """Handle sign up button click."""
        username = self.signup_username.text().strip()
        display_name = self.signup_display_name.text().strip()
        password = self.signup_password.text()
        confirm_password = self.signup_confirm_password.text()
        
        # Validation
        if not username or not display_name or not password:
            QMessageBox.warning(self, "Input Error", 
                              "Please fill in all fields.")
            return
        
        if len(username) < 3:
            QMessageBox.warning(self, "Input Error", 
                              "Username must be at least 3 characters long.")
            return
        
        if len(password) < 6:
            QMessageBox.warning(self, "Input Error", 
                              "Password must be at least 6 characters long.")
            return
        
        if password != confirm_password:
            QMessageBox.warning(self, "Input Error", 
                              "Passwords do not match.")
            return
        
        # Create profile
        if profile_manager.create_profile(username, display_name, password):
            QMessageBox.information(self, "Success", 
                                  f"Account created successfully!\nYou can now sign in as '{username}'.")
            logger.info(f"New user '{username}' registered")
            
            # Switch to sign in tab and populate username
            self.tab_widget.setCurrentIndex(0)
            self.signin_username.setText(username)
            self.signin_password.setFocus()
            
            # Clear signup fields
            self.signup_username.clear()
            self.signup_display_name.clear()
            self.signup_password.clear()
            self.signup_confirm_password.clear()
        else:
            QMessageBox.critical(self, "Registration Failed", 
                               f"Username '{username}' already exists.")
            logger.warning(f"Failed registration attempt for username '{username}'")
    
    def handle_forgot_password(self):
        """Handle forgot password button click (placeholder)."""
        QMessageBox.information(self, "Forgot Password", 
                              "Password recovery is not implemented in this demo version.\n\n"
                              "In a production system, this would:\n"
                              "- Send a recovery email or SMS\n"
                              "- Generate a temporary reset token\n"
                              "- Allow password reset via secure link")
        logger.info("Forgot password clicked (placeholder)")
    
    def load_remember_me(self):
        """Load remember me preference from config."""
        remember_me = config.get('ui.remember_me', False)
        last_username = config.get('ui.last_username', '')
        
        if remember_me and last_username:
            self.signin_username.setText(last_username)
            self.remember_me_checkbox.setChecked(True)
            self.signin_password.setFocus()
            logger.info(f"Loaded remembered username: {last_username}")
