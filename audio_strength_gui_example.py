#!/usr/bin/env python3
"""
Audio Strength Detection GUI Example

This example demonstrates the audio strength detection feature
with a real-time visual indicator and level meter.
"""

import sys
import time
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QProgressBar, QGroupBox, QGridLayout
)
from PySide6.QtCore import QTimer, Signal, QObject
from PySide6.QtGui import QFont, QPalette, QColor
from client.media_capture import MediaCaptureManager

class AudioStrengthDisplay(QWidget):
    """Widget to display audio strength with visual indicators."""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("🎤 Audio Strength Monitor")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setStyleSheet("color: #2196F3; margin: 10px;")
        layout.addWidget(title)
        
        # Current strength display
        strength_group = QGroupBox("Current Audio Level")
        strength_layout = QGridLayout(strength_group)
        
        # Strength bar
        self.strength_bar = QProgressBar()
        self.strength_bar.setRange(0, 100)
        self.strength_bar.setValue(0)
        self.strength_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4CAF50, stop:0.5 #FFC107, stop:1 #F44336);
                border-radius: 3px;
            }
        """)
        strength_layout.addWidget(QLabel("Level:"), 0, 0)
        strength_layout.addWidget(self.strength_bar, 0, 1)
        
        # Strength percentage
        self.strength_label = QLabel("0%")
        self.strength_label.setFont(QFont("Arial", 14, QFont.Bold))
        strength_layout.addWidget(QLabel("Strength:"), 1, 0)
        strength_layout.addWidget(self.strength_label, 1, 1)
        
        # Status indicator
        self.status_label = QLabel("Silent")
        self.status_label.setFont(QFont("Arial", 12))
        self.status_label.setStyleSheet("color: #666; padding: 5px;")
        strength_layout.addWidget(QLabel("Status:"), 2, 0)
        strength_layout.addWidget(self.status_label, 2, 1)
        
        layout.addWidget(strength_group)
        
        # Peak strength display
        peak_group = QGroupBox("Session Statistics")
        peak_layout = QGridLayout(peak_group)
        
        # Peak strength
        self.peak_bar = QProgressBar()
        self.peak_bar.setRange(0, 100)
        self.peak_bar.setValue(0)
        self.peak_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #FF5722;
                border-radius: 3px;
            }
        """)
        peak_layout.addWidget(QLabel("Peak Level:"), 0, 0)
        peak_layout.addWidget(self.peak_bar, 0, 1)
        
        self.peak_label = QLabel("0%")
        self.peak_label.setFont(QFont("Arial", 12))
        peak_layout.addWidget(QLabel("Peak Value:"), 1, 0)
        peak_layout.addWidget(self.peak_label, 1, 1)
        
        # Average strength
        self.avg_label = QLabel("0%")
        self.avg_label.setFont(QFont("Arial", 12))
        peak_layout.addWidget(QLabel("Average:"), 2, 0)
        peak_layout.addWidget(self.avg_label, 2, 1)
        
        layout.addWidget(peak_group)
        
        # Reset button
        self.reset_btn = QPushButton("Reset Peak")
        self.reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """)
        layout.addWidget(self.reset_btn)
    
    def update_strength(self, current: float, peak: float, average: float = 0.0, status: str = ""):
        """Update the display with new strength values."""
        # Update current strength
        current_percent = int(current * 100)
        self.strength_bar.setValue(current_percent)
        self.strength_label.setText(f"{current_percent}%")
        
        # Update peak strength
        peak_percent = int(peak * 100)
        self.peak_bar.setValue(peak_percent)
        self.peak_label.setText(f"{peak_percent}%")
        
        # Update average
        avg_percent = int(average * 100)
        self.avg_label.setText(f"{avg_percent}%")
        
        # Update status with color coding
        self.status_label.setText(status)
        if status == "Silent":
            self.status_label.setStyleSheet("color: #666; padding: 5px;")
        elif status == "Quiet":
            self.status_label.setStyleSheet("color: #4CAF50; padding: 5px;")
        elif status == "Speaking":
            self.status_label.setStyleSheet("color: #FFC107; padding: 5px; font-weight: bold;")
        elif status == "Loud":
            self.status_label.setStyleSheet("color: #F44336; padding: 5px; font-weight: bold;")

class AudioStrengthDemo(QMainWindow):
    """Main demo window for audio strength detection."""
    
    def __init__(self):
        super().__init__()
        self.media_manager = None
        self.update_timer = QTimer()
        self.setup_ui()
        self.setup_audio()
        
    def setup_ui(self):
        self.setWindowTitle("Audio Strength Detection Demo")
        self.setGeometry(100, 100, 400, 500)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Audio strength display
        self.strength_display = AudioStrengthDisplay()
        layout.addWidget(self.strength_display)
        
        # Control buttons
        controls_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("🎤 Start Audio")
        self.start_btn.clicked.connect(self.toggle_audio)
        self.start_btn.setMinimumHeight(40)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        controls_layout.addWidget(self.start_btn)
        
        layout.addLayout(controls_layout)
        
        # Connect reset button
        self.strength_display.reset_btn.clicked.connect(self.reset_peak)
        
        # Setup update timer
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(50)  # Update every 50ms for smooth display
        
    def setup_audio(self):
        """Initialize audio capture system."""
        try:
            # Create mock client for demo
            class MockClient:
                def __init__(self):
                    self.username = "demo_user"
                def send_audio_packet(self, data):
                    pass  # Don't actually send packets in demo
                def set_media_state(self, **kwargs):
                    pass
            
            mock_client = MockClient()
            self.media_manager = MediaCaptureManager(mock_client)
            
            # Set up audio strength callback
            self.media_manager.set_audio_strength_callback(self.on_strength_update)
            
        except Exception as e:
            print(f"Error setting up audio: {e}")
    
    def on_strength_update(self, current_strength: float, peak_strength: float):
        """Callback for audio strength updates."""
        # This will be called from the audio thread
        # The actual display update happens in update_display()
        pass
    
    def update_display(self):
        """Update the display with current audio strength values."""
        if not self.media_manager:
            return
        
        try:
            current = self.media_manager.get_audio_strength()
            peak = self.media_manager.get_peak_audio_strength()
            average = self.media_manager.get_average_audio_strength()
            status = self.media_manager.get_audio_strength_description()
            
            self.strength_display.update_strength(current, peak, average, status)
            
        except Exception as e:
            print(f"Error updating display: {e}")
    
    def toggle_audio(self):
        """Toggle audio capture on/off."""
        if not self.media_manager:
            return
        
        try:
            if self.media_manager.is_audio_active():
                # Stop audio
                self.media_manager.stop_audio()
                self.start_btn.setText("🎤 Start Audio")
                self.start_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #4CAF50;
                        color: white;
                        font-size: 14px;
                        font-weight: bold;
                        border-radius: 4px;
                    }
                    QPushButton:hover {
                        background-color: #45a049;
                    }
                """)
            else:
                # Start audio
                success = self.media_manager.start_audio()
                if success:
                    self.start_btn.setText("🛑 Stop Audio")
                    self.start_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #f44336;
                            color: white;
                            font-size: 14px;
                            font-weight: bold;
                            border-radius: 4px;
                        }
                        QPushButton:hover {
                            background-color: #da190b;
                        }
                    """)
                else:
                    print("Failed to start audio capture")
                    
        except Exception as e:
            print(f"Error toggling audio: {e}")
    
    def reset_peak(self):
        """Reset the peak audio strength measurement."""
        if self.media_manager:
            self.media_manager.reset_peak_audio_strength()
    
    def closeEvent(self, event):
        """Handle window close event."""
        if self.media_manager:
            self.media_manager.cleanup()
        event.accept()

def main():
    """Run the audio strength detection demo."""
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle("Fusion")
    
    # Create and show demo window
    demo = AudioStrengthDemo()
    demo.show()
    
    print("Audio Strength Detection Demo")
    print("=" * 30)
    print("Click 'Start Audio' to begin monitoring your microphone.")
    print("Speak into your microphone to see the strength levels change.")
    print("The display shows:")
    print("- Current audio level (real-time)")
    print("- Peak level reached in this session")
    print("- Average level over recent history")
    print("- Status: Silent, Quiet, Speaking, or Loud")
    print()
    print("Close the window to exit.")
    
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())