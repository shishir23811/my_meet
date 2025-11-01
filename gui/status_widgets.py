"""
Enhanced Status Widgets for LAN Communication Application.

Provides comprehensive status indicators, error notifications, and user feedback.
Implements non-blocking notifications and real-time status updates.
"""

from PySide6.QtWidgets import (
    QWidget, QLabel, QHBoxLayout, QVBoxLayout, QPushButton,
    QProgressBar, QFrame, QScrollArea, QListWidget, QListWidgetItem,
    QDialog, QTextEdit, QGroupBox, QGridLayout, QSystemTrayIcon,
    QMenu, QApplication
)
from PySide6.QtCore import Qt, Signal, QTimer, QPropertyAnimation, QEasingCurve, QRect
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont, QIcon
from utils.error_manager import ErrorManager, ErrorReport, ErrorSeverity, ErrorCategory
from utils.logger import setup_logger
import time

logger = setup_logger(__name__)

class StatusIndicator(QLabel):
    """
    Enhanced status indicator with color coding and animations.
    """
    
    def __init__(self, component_name: str, parent=None):
        super().__init__(parent)
        self.component_name = component_name
        self.current_status = "unknown"
        self.current_message = "Status unknown"
        
        # Setup appearance
        self.setMinimumSize(120, 24)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                border: 1px solid #ccc;
                border-radius: 12px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: bold;
            }
        """)
        
        # Animation for status changes
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(200)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        
        self.update_status("unknown", "Status unknown")
    
    def update_status(self, status: str, message: str = None):
        """Update the status indicator."""
        self.current_status = status
        self.current_message = message or status
        
        # Status color mapping
        status_colors = {
            'connected': '#4CAF50',      # Green
            'connecting': '#FF9800',     # Orange
            'disconnected': '#f44336',   # Red
            'reconnecting': '#2196F3',   # Blue
            'active': '#4CAF50',         # Green
            'inactive': '#9E9E9E',       # Gray
            'error': '#f44336',          # Red
            'warning': '#FF9800',        # Orange
            'idle': '#9E9E9E',           # Gray
            'processing': '#2196F3',     # Blue
            'unknown': '#9E9E9E'         # Gray
        }
        
        # Status icons
        status_icons = {
            'connected': '●',
            'connecting': '◐',
            'disconnected': '○',
            'reconnecting': '◑',
            'active': '●',
            'inactive': '○',
            'error': '✗',
            'warning': '⚠',
            'idle': '○',
            'processing': '◐',
            'unknown': '?'
        }
        
        color = status_colors.get(status, '#9E9E9E')
        icon = status_icons.get(status, '?')
        
        # Update text and style
        display_text = f"{icon} {self.component_name.title()}"
        self.setText(display_text)
        self.setToolTip(f"{self.component_name.title()}: {self.current_message}")
        
        self.setStyleSheet(f"""
            QLabel {{
                border: 1px solid {color};
                border-radius: 12px;
                padding: 4px 8px;
                font-size: 11px;
                font-weight: bold;
                background-color: {color}20;
                color: {color};
            }}
        """)
        
        # Animate on status change
        self._animate_update()
    
    def _animate_update(self):
        """Animate status update."""
        # Simple scale animation
        original_rect = self.geometry()
        expanded_rect = QRect(
            original_rect.x() - 2,
            original_rect.y() - 1,
            original_rect.width() + 4,
            original_rect.height() + 2
        )
        
        self.animation.setStartValue(original_rect)
        self.animation.setEndValue(expanded_rect)
        self.animation.finished.connect(lambda: self._reset_animation(original_rect))
        self.animation.start()
    
    def _reset_animation(self, original_rect):
        """Reset animation to original size."""
        self.animation.setStartValue(self.geometry())
        self.animation.setEndValue(original_rect)
        self.animation.finished.disconnect()
        self.animation.start()

class NotificationWidget(QWidget):
    """
    Non-blocking notification widget that slides in from the top.
    """
    
    closed = Signal()
    
    def __init__(self, title: str, message: str, severity: str = "info", 
                 duration: int = 5000, parent=None):
        super().__init__(parent)
        self.duration = duration
        self.severity = severity
        
        # Setup widget
        self.setFixedHeight(80)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Icon based on severity
        icon_label = QLabel()
        icon_label.setFixedSize(32, 32)
        icon_label.setAlignment(Qt.AlignCenter)
        
        severity_icons = {
            'info': '💬',
            'warning': '⚠️',
            'error': '❌',
            'critical': '🚨'
        }
        
        icon_label.setText(severity_icons.get(severity, '💬'))
        icon_label.setStyleSheet("font-size: 20px;")
        layout.addWidget(icon_label)
        
        # Text content
        text_layout = QVBoxLayout()
        
        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        text_layout.addWidget(title_label)
        
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setStyleSheet("font-size: 11px; color: #666;")
        text_layout.addWidget(message_label)
        
        layout.addLayout(text_layout, 1)
        
        # Close button
        close_btn = QPushButton("×")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background: transparent;
                font-size: 16px;
                font-weight: bold;
                color: #999;
            }
            QPushButton:hover {
                color: #333;
                background: #f0f0f0;
                border-radius: 12px;
            }
        """)
        close_btn.clicked.connect(self.close_notification)
        layout.addWidget(close_btn)
        
        # Styling based on severity
        severity_colors = {
            'info': '#E3F2FD',
            'warning': '#FFF3E0',
            'error': '#FFEBEE',
            'critical': '#FCE4EC'
        }
        
        border_colors = {
            'info': '#2196F3',
            'warning': '#FF9800',
            'error': '#f44336',
            'critical': '#E91E63'
        }
        
        bg_color = severity_colors.get(severity, '#E3F2FD')
        border_color = border_colors.get(severity, '#2196F3')
        
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {bg_color};
                border: 2px solid {border_color};
                border-radius: 8px;
            }}
        """)
        
        # Auto-close timer
        if duration > 0:
            QTimer.singleShot(duration, self.close_notification)
        
        # Slide-in animation
        self.slide_animation = QPropertyAnimation(self, b"pos")
        self.slide_animation.setDuration(300)
        self.slide_animation.setEasingCurve(QEasingCurve.OutCubic)
    
    def show_notification(self, parent_widget):
        """Show notification with slide-in animation."""
        if parent_widget:
            # Position at top of parent widget
            parent_rect = parent_widget.geometry()
            start_pos = parent_rect.topLeft()
            start_pos.setY(start_pos.y() - self.height())
            
            end_pos = parent_rect.topLeft()
            end_pos.setY(end_pos.y() + 10)
            
            self.move(start_pos)
            self.show()
            
            # Animate slide-in
            self.slide_animation.setStartValue(start_pos)
            self.slide_animation.setEndValue(end_pos)
            self.slide_animation.start()
    
    def close_notification(self):
        """Close notification with slide-out animation."""
        # Animate slide-out
        current_pos = self.pos()
        end_pos = current_pos
        end_pos.setY(current_pos.y() - self.height() - 20)
        
        self.slide_animation.setStartValue(current_pos)
        self.slide_animation.setEndValue(end_pos)
        self.slide_animation.finished.connect(self.hide)
        self.slide_animation.finished.connect(self.closed.emit)
        self.slide_animation.start()

class EnhancedStatusBar(QWidget):
    """
    Enhanced status bar with multiple component indicators and error summary.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.error_manager = None
        self.status_indicators = {}
        self.active_notifications = []
        
        # Setup layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)
        
        # Component status indicators
        self.indicators_layout = QHBoxLayout()
        layout.addLayout(self.indicators_layout)
        
        # Add default indicators
        self._create_status_indicators()
        
        # Spacer
        layout.addStretch()
        
        # Error summary
        self.error_summary_label = QLabel("No errors")
        self.error_summary_label.setStyleSheet("""
            QLabel {
                color: #666;
                font-size: 10px;
                padding: 2px 6px;
                border-radius: 3px;
                background-color: #f0f0f0;
            }
        """)
        layout.addWidget(self.error_summary_label)
        
        # Error details button
        self.error_details_btn = QPushButton("Details")
        self.error_details_btn.setFixedSize(50, 20)
        self.error_details_btn.setStyleSheet("""
            QPushButton {
                font-size: 9px;
                padding: 2px;
                border: 1px solid #ccc;
                border-radius: 3px;
                background-color: #f8f8f8;
            }
            QPushButton:hover {
                background-color: #e8e8e8;
            }
        """)
        self.error_details_btn.clicked.connect(self.show_error_details)
        self.error_details_btn.setVisible(False)
        layout.addWidget(self.error_details_btn)
        
        logger.info("EnhancedStatusBar initialized")
    
    def _create_status_indicators(self):
        """Create status indicators for different components."""
        components = ['network', 'audio', 'video', 'screen_share', 'file_transfer']
        
        for component in components:
            indicator = StatusIndicator(component)
            self.status_indicators[component] = indicator
            self.indicators_layout.addWidget(indicator)
    
    def set_error_manager(self, error_manager: ErrorManager):
        """Connect to error manager for status updates."""
        self.error_manager = error_manager
        
        # Connect signals
        error_manager.status_updated.connect(self.update_component_status)
        error_manager.error_reported.connect(self.on_error_reported)
        error_manager.error_resolved.connect(self.on_error_resolved)
        error_manager.notification_requested.connect(self.show_notification)
        
        # Initial status update
        self.update_error_summary()
    
    def update_component_status(self, component: str, status: str, message: str):
        """Update status indicator for a component."""
        if component in self.status_indicators:
            self.status_indicators[component].update_status(status, message)
            logger.debug(f"Updated status indicator: {component} -> {status}")
    
    def on_error_reported(self, error_report: ErrorReport):
        """Handle new error report."""
        self.update_error_summary()
        
        # Update component status if error affects a specific component
        if error_report.component and error_report.component in self.status_indicators:
            if error_report.severity in [ErrorSeverity.ERROR, ErrorSeverity.CRITICAL]:
                self.update_component_status(error_report.component, "error", error_report.message)
            elif error_report.severity == ErrorSeverity.WARNING:
                self.update_component_status(error_report.component, "warning", error_report.message)
    
    def on_error_resolved(self, error_id: str):
        """Handle error resolution."""
        self.update_error_summary()
    
    def update_error_summary(self):
        """Update error summary display."""
        if not self.error_manager:
            return
        
        summary = self.error_manager.get_error_summary()
        total_errors = summary['total']
        
        if total_errors == 0:
            self.error_summary_label.setText("No errors")
            self.error_summary_label.setStyleSheet("""
                QLabel {
                    color: #666;
                    font-size: 10px;
                    padding: 2px 6px;
                    border-radius: 3px;
                    background-color: #f0f0f0;
                }
            """)
            self.error_details_btn.setVisible(False)
        else:
            # Count by severity
            critical = summary['by_severity'].get('critical', 0)
            errors = summary['by_severity'].get('error', 0)
            warnings = summary['by_severity'].get('warning', 0)
            
            # Create summary text
            parts = []
            if critical > 0:
                parts.append(f"{critical} critical")
            if errors > 0:
                parts.append(f"{errors} errors")
            if warnings > 0:
                parts.append(f"{warnings} warnings")
            
            summary_text = ", ".join(parts) if parts else f"{total_errors} issues"
            self.error_summary_label.setText(summary_text)
            
            # Color based on highest severity
            if critical > 0:
                color = "#f44336"  # Red
                bg_color = "#FFEBEE"
            elif errors > 0:
                color = "#FF5722"  # Deep Orange
                bg_color = "#FFF3E0"
            else:
                color = "#FF9800"  # Orange
                bg_color = "#FFF8E1"
            
            self.error_summary_label.setStyleSheet(f"""
                QLabel {{
                    color: {color};
                    font-size: 10px;
                    font-weight: bold;
                    padding: 2px 6px;
                    border-radius: 3px;
                    background-color: {bg_color};
                    border: 1px solid {color};
                }}
            """)
            
            self.error_details_btn.setVisible(True)
    
    def show_notification(self, title: str, message: str, severity: str, duration: int):
        """Show a non-blocking notification."""
        notification = NotificationWidget(title, message, severity, duration)
        notification.closed.connect(lambda: self._remove_notification(notification))
        
        # Position notification
        notification.show_notification(self.parent())
        self.active_notifications.append(notification)
        
        # Limit number of active notifications
        if len(self.active_notifications) > 3:
            oldest = self.active_notifications.pop(0)
            oldest.close_notification()
    
    def _remove_notification(self, notification):
        """Remove notification from active list."""
        if notification in self.active_notifications:
            self.active_notifications.remove(notification)
        notification.deleteLater()
    
    def show_error_details(self):
        """Show detailed error information dialog."""
        if not self.error_manager:
            return
        
        dialog = ErrorDetailsDialog(self.error_manager, self)
        dialog.exec()

class ErrorDetailsDialog(QDialog):
    """
    Dialog showing detailed error information and history.
    """
    
    def __init__(self, error_manager: ErrorManager, parent=None):
        super().__init__(parent)
        self.error_manager = error_manager
        
        self.setWindowTitle("Error Details")
        self.setModal(True)
        self.resize(600, 400)
        
        # Layout
        layout = QVBoxLayout(self)
        
        # Active errors
        active_group = QGroupBox("Active Errors")
        active_layout = QVBoxLayout(active_group)
        
        self.active_errors_list = QListWidget()
        active_layout.addWidget(self.active_errors_list)
        
        # Clear button
        clear_btn = QPushButton("Clear All Errors")
        clear_btn.clicked.connect(self.clear_all_errors)
        active_layout.addWidget(clear_btn)
        
        layout.addWidget(active_group)
        
        # Error history
        history_group = QGroupBox("Recent Error History")
        history_layout = QVBoxLayout(history_group)
        
        self.history_list = QListWidget()
        history_layout.addWidget(self.history_list)
        
        layout.addWidget(history_group)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
        # Populate data
        self.refresh_data()
    
    def refresh_data(self):
        """Refresh error data in the dialog."""
        # Clear lists
        self.active_errors_list.clear()
        self.history_list.clear()
        
        # Active errors
        active_errors = self.error_manager.get_active_errors()
        for error in active_errors:
            item_text = f"[{error.severity.value.upper()}] {error.title}: {error.message}"
            if error.component:
                item_text += f" ({error.component})"
            
            item = QListWidgetItem(item_text)
            
            # Color based on severity
            if error.severity == ErrorSeverity.CRITICAL:
                item.setBackground(QColor("#FFEBEE"))
            elif error.severity == ErrorSeverity.ERROR:
                item.setBackground(QColor("#FFF3E0"))
            elif error.severity == ErrorSeverity.WARNING:
                item.setBackground(QColor("#FFF8E1"))
            
            self.active_errors_list.addItem(item)
        
        # Error history (last 20)
        history = self.error_manager.get_error_history(20)
        for error in reversed(history):  # Most recent first
            timestamp = time.strftime("%H:%M:%S", time.localtime(error.timestamp))
            item_text = f"[{timestamp}] [{error.severity.value.upper()}] {error.title}"
            
            item = QListWidgetItem(item_text)
            item.setToolTip(f"{error.message}\nDetails: {error.details or 'None'}")
            
            self.history_list.addItem(item)
    
    def clear_all_errors(self):
        """Clear all active errors."""
        self.error_manager.clear_errors()
        self.refresh_data()