"""
Error Manager for LAN Communication Application.

Provides centralized error handling, notification management, and user feedback.
Implements non-blocking error notifications and comprehensive error categorization.
"""

import time
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional, Callable, Dict, Any
from PySide6.QtCore import QObject, Signal, QTimer
from utils.logger import setup_logger

logger = setup_logger(__name__)

class ErrorSeverity(Enum):
    """Error severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    """Error categories for better organization."""
    NETWORK = "network"
    MEDIA = "media"
    FILE_TRANSFER = "file_transfer"
    AUTHENTICATION = "authentication"
    DEVICE = "device"
    SYSTEM = "system"
    USER_INPUT = "user_input"

@dataclass
class ErrorReport:
    """Represents an error report with context and metadata."""
    id: str
    category: ErrorCategory
    severity: ErrorSeverity
    title: str
    message: str
    details: Optional[str] = None
    timestamp: float = None
    component: Optional[str] = None
    user_action: Optional[str] = None  # Suggested user action
    auto_retry: bool = False
    retry_count: int = 0
    max_retries: int = 3
    context: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
        if self.context is None:
            self.context = {}

class ErrorManager(QObject):
    """
    Centralized error management system.
    
    Features:
    - Non-blocking error notifications
    - Error categorization and severity levels
    - Automatic retry mechanisms
    - User-friendly error messages
    - Error history and analytics
    """
    
    # Signals for GUI updates
    error_reported = Signal(ErrorReport)  # New error reported
    error_resolved = Signal(str)  # Error resolved (by ID)
    status_updated = Signal(str, str, str)  # component, status, message
    notification_requested = Signal(str, str, str, int)  # title, message, severity, duration
    
    def __init__(self):
        super().__init__()
        self.errors: Dict[str, ErrorReport] = {}
        self.error_history: List[ErrorReport] = []
        self.max_history_size = 100
        self.error_counter = 0
        
        # Component status tracking
        self.component_status: Dict[str, Dict[str, Any]] = {
            'network': {'status': 'disconnected', 'message': 'Not connected', 'last_update': time.time()},
            'audio': {'status': 'inactive', 'message': 'Audio not active', 'last_update': time.time()},
            'video': {'status': 'inactive', 'message': 'Video not active', 'last_update': time.time()},
            'screen_share': {'status': 'inactive', 'message': 'Screen sharing not active', 'last_update': time.time()},
            'file_transfer': {'status': 'idle', 'message': 'No active transfers', 'last_update': time.time()}
        }
        
        # Error message templates
        self.error_templates = {
            # Network errors
            (ErrorCategory.NETWORK, 'connection_failed'): {
                'title': 'Connection Failed',
                'message': 'Unable to connect to the server.',
                'user_action': 'Check your network connection and server address.',
                'auto_retry': True
            },
            (ErrorCategory.NETWORK, 'connection_lost'): {
                'title': 'Connection Lost',
                'message': 'Connection to the server was lost.',
                'user_action': 'Attempting to reconnect automatically...',
                'auto_retry': True
            },
            (ErrorCategory.NETWORK, 'auth_failed'): {
                'title': 'Authentication Failed',
                'message': 'Unable to authenticate with the server.',
                'user_action': 'Check your username and session ID.',
                'auto_retry': False
            },
            (ErrorCategory.NETWORK, 'server_unavailable'): {
                'title': 'Server Unavailable',
                'message': 'The server is not responding.',
                'user_action': 'Check if the server is running and accessible.',
                'auto_retry': True
            },
            (ErrorCategory.NETWORK, 'media_quality_degraded'): {
                'title': 'Media Quality Degraded',
                'message': 'Media quality reduced due to network conditions.',
                'user_action': 'Check network connection for better performance.',
                'auto_retry': False
            },
            (ErrorCategory.NETWORK, 'reconnection_failed'): {
                'title': 'Reconnection Failed',
                'message': 'Unable to reconnect to the server.',
                'user_action': 'Check network connection and try manual reconnection.',
                'auto_retry': True
            },
            
            # Media errors
            (ErrorCategory.MEDIA, 'audio_device_not_found'): {
                'title': 'Audio Device Not Found',
                'message': 'No audio input device detected.',
                'user_action': 'Check your microphone connection and permissions.',
                'auto_retry': False
            },
            (ErrorCategory.MEDIA, 'video_device_not_found'): {
                'title': 'Camera Not Found',
                'message': 'No camera device detected.',
                'user_action': 'Check your camera connection and permissions.',
                'auto_retry': False
            },
            (ErrorCategory.MEDIA, 'audio_permission_denied'): {
                'title': 'Audio Permission Denied',
                'message': 'Permission to access microphone was denied.',
                'user_action': 'Grant microphone permissions in system settings.',
                'auto_retry': False
            },
            (ErrorCategory.MEDIA, 'video_permission_denied'): {
                'title': 'Camera Permission Denied',
                'message': 'Permission to access camera was denied.',
                'user_action': 'Grant camera permissions in system settings.',
                'auto_retry': False
            },
            (ErrorCategory.MEDIA, 'screen_capture_failed'): {
                'title': 'Screen Capture Failed',
                'message': 'Unable to capture screen content.',
                'user_action': 'Grant screen recording permissions in system settings.',
                'auto_retry': False
            },
            (ErrorCategory.MEDIA, 'stream_restore_failed'): {
                'title': 'Stream Recovery Failed',
                'message': 'Unable to restore media stream after reconnection.',
                'user_action': 'Try manually restarting the media feature.',
                'auto_retry': False
            },
            (ErrorCategory.MEDIA, 'stream_transmission_error'): {
                'title': 'Media Transmission Error',
                'message': 'Persistent errors sending media data.',
                'user_action': 'Check network connection and media device.',
                'auto_retry': True
            },
            
            # File transfer errors
            (ErrorCategory.FILE_TRANSFER, 'file_not_found'): {
                'title': 'File Not Found',
                'message': 'The selected file could not be found.',
                'user_action': 'Check if the file exists and is accessible.',
                'auto_retry': False
            },
            (ErrorCategory.FILE_TRANSFER, 'insufficient_space'): {
                'title': 'Insufficient Disk Space',
                'message': 'Not enough disk space to complete the transfer.',
                'user_action': 'Free up disk space and try again.',
                'auto_retry': False
            },
            (ErrorCategory.FILE_TRANSFER, 'permission_denied'): {
                'title': 'File Permission Denied',
                'message': 'Permission denied accessing the file.',
                'user_action': 'Check file permissions and try again.',
                'auto_retry': False
            },
            (ErrorCategory.FILE_TRANSFER, 'transfer_interrupted'): {
                'title': 'Transfer Interrupted',
                'message': 'File transfer was interrupted.',
                'user_action': 'Transfer will resume automatically.',
                'auto_retry': True
            },
            
            # Device errors
            (ErrorCategory.DEVICE, 'device_disconnected'): {
                'title': 'Device Disconnected',
                'message': 'A media device was disconnected during use.',
                'user_action': 'Reconnect the device to continue.',
                'auto_retry': True
            },
            (ErrorCategory.DEVICE, 'device_busy'): {
                'title': 'Device Busy',
                'message': 'The device is being used by another application.',
                'user_action': 'Close other applications using the device.',
                'auto_retry': True
            }
        }
        
        logger.info("ErrorManager initialized")
    
    def report_error(self, category: ErrorCategory, error_type: str, 
                    severity: ErrorSeverity = ErrorSeverity.ERROR,
                    component: Optional[str] = None, 
                    details: Optional[str] = None,
                    context: Optional[Dict[str, Any]] = None) -> str:
        """
        Report an error with automatic message generation.
        
        Args:
            category: Error category
            error_type: Specific error type
            severity: Error severity level
            component: Component that generated the error
            details: Additional error details
            context: Additional context information
            
        Returns:
            Error ID for tracking
        """
        self.error_counter += 1
        error_id = f"err_{self.error_counter}_{int(time.time())}"
        
        # Get error template
        template_key = (category, error_type)
        template = self.error_templates.get(template_key, {
            'title': f'{category.value.title()} Error',
            'message': f'An error occurred in {component or "the system"}.',
            'user_action': 'Please try again or contact support.',
            'auto_retry': False
        })
        
        # Create error report
        error_report = ErrorReport(
            id=error_id,
            category=category,
            severity=severity,
            title=template['title'],
            message=template['message'],
            details=details,
            component=component,
            user_action=template['user_action'],
            auto_retry=template['auto_retry'],
            context=context or {}
        )
        
        # Store error
        self.errors[error_id] = error_report
        self.error_history.append(error_report)
        
        # Trim history if needed
        if len(self.error_history) > self.max_history_size:
            self.error_history = self.error_history[-self.max_history_size:]
        
        # Log error
        log_level = {
            ErrorSeverity.INFO: logger.info,
            ErrorSeverity.WARNING: logger.warning,
            ErrorSeverity.ERROR: logger.error,
            ErrorSeverity.CRITICAL: logger.critical
        }[severity]
        
        log_level(f"Error reported [{error_id}]: {error_report.title} - {error_report.message}")
        if details:
            log_level(f"Error details [{error_id}]: {details}")
        
        # Emit signals
        self.error_reported.emit(error_report)
        
        # Send notification for user-facing errors
        if severity in [ErrorSeverity.WARNING, ErrorSeverity.ERROR, ErrorSeverity.CRITICAL]:
            duration = {
                ErrorSeverity.WARNING: 3000,
                ErrorSeverity.ERROR: 5000,
                ErrorSeverity.CRITICAL: 8000
            }[severity]
            
            self.notification_requested.emit(
                error_report.title,
                error_report.message,
                severity.value,
                duration
            )
        
        return error_id
    
    def resolve_error(self, error_id: str, resolution_message: Optional[str] = None):
        """
        Mark an error as resolved.
        
        Args:
            error_id: Error ID to resolve
            resolution_message: Optional resolution message
        """
        if error_id in self.errors:
            error_report = self.errors[error_id]
            del self.errors[error_id]
            
            logger.info(f"Error resolved [{error_id}]: {error_report.title}")
            if resolution_message:
                logger.info(f"Resolution [{error_id}]: {resolution_message}")
            
            self.error_resolved.emit(error_id)
    
    def update_component_status(self, component: str, status: str, 
                              message: Optional[str] = None):
        """
        Update the status of a system component.
        
        Args:
            component: Component name (network, audio, video, etc.)
            status: New status
            message: Optional status message
        """
        if component not in self.component_status:
            self.component_status[component] = {}
        
        self.component_status[component].update({
            'status': status,
            'message': message or status,
            'last_update': time.time()
        })
        
        logger.debug(f"Component status updated: {component} -> {status}")
        self.status_updated.emit(component, status, message or status)
    
    def get_component_status(self, component: str) -> Dict[str, Any]:
        """Get current status of a component."""
        return self.component_status.get(component, {
            'status': 'unknown',
            'message': 'Status unknown',
            'last_update': 0
        })
    
    def get_active_errors(self) -> List[ErrorReport]:
        """Get list of currently active errors."""
        return list(self.errors.values())
    
    def get_error_history(self, limit: Optional[int] = None) -> List[ErrorReport]:
        """Get error history."""
        if limit:
            return self.error_history[-limit:]
        return self.error_history.copy()
    
    def clear_errors(self, category: Optional[ErrorCategory] = None):
        """
        Clear errors, optionally filtered by category.
        
        Args:
            category: If specified, only clear errors of this category
        """
        if category:
            to_remove = [eid for eid, err in self.errors.items() if err.category == category]
            for eid in to_remove:
                del self.errors[eid]
            logger.info(f"Cleared {len(to_remove)} errors in category {category.value}")
        else:
            count = len(self.errors)
            self.errors.clear()
            logger.info(f"Cleared all {count} active errors")
    
    def get_error_summary(self) -> Dict[str, int]:
        """Get summary of errors by category and severity."""
        summary = {
            'total': len(self.errors),
            'by_category': {},
            'by_severity': {}
        }
        
        for error in self.errors.values():
            # Count by category
            cat = error.category.value
            summary['by_category'][cat] = summary['by_category'].get(cat, 0) + 1
            
            # Count by severity
            sev = error.severity.value
            summary['by_severity'][sev] = summary['by_severity'].get(sev, 0) + 1
        
        return summary

# Global error manager instance
error_manager = ErrorManager()