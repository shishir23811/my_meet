"""
Real media capture implementation for LAN Communication Application.

Replaces MediaCaptureStub with functional audio/video capture using:
- sounddevice for cross-platform audio capture
- opencv-python for camera capture
- mss for screen capture
"""

import threading
import time
import numpy as np
from typing import Optional, Callable, Dict
from collections import deque
from utils.logger import setup_logger

logger = setup_logger(__name__)

# ============================================================================
# Audio Capture Implementation
# ============================================================================

class AudioCapture:
    """
    Real audio capture using sounddevice library.
    
    Captures audio from microphone and sends via LANClient UDP packets.
    Handles device detection, error recovery, and resource cleanup.
    """
    
    def __init__(self, client):
        """Initialize audio capture with client reference."""
        self.client = client
        self.is_active = False
        self.capture_thread: Optional[threading.Thread] = None
        self.error_message = ""
        
        # Audio settings
        self.sample_rate = 44100  # Standard CD quality
        self.channels = 2  # Stereo
        self.dtype = np.int16  # 16-bit PCM
        self.frame_duration = 0.02  # 20ms frames
        self.frames_per_buffer = int(self.sample_rate * self.frame_duration)
        
        # Try to import sounddevice
        try:
            import sounddevice as sd
            self.sd = sd
            self._detect_devices()
            logger.info("AudioCapture initialized successfully")
        except ImportError as e:
            self.sd = None
            self.error_message = "sounddevice library not available"
            logger.error(f"Failed to import sounddevice: {e}")
        except Exception as e:
            self.sd = None
            self.error_message = f"Audio system initialization failed: {e}"
            logger.error(f"Audio initialization error: {e}")
    
    def _detect_devices(self):
        """Detect available audio input devices."""
        if not self.sd:
            return
        
        try:
            devices = self.sd.query_devices()
            input_devices = [d for d in devices if d['max_input_channels'] > 0]
            
            if input_devices:
                # Use default input device
                self.input_device = None  # None means default
                logger.info(f"Found {len(input_devices)} audio input devices")
                logger.info(f"Using default input device")
            else:
                self.input_device = None
                self.error_message = "No audio input devices found"
                logger.warning("No audio input devices detected")
                
        except Exception as e:
            self.error_message = f"Device detection failed: {e}"
            logger.error(f"Audio device detection error: {e}")
    
    def start_capture(self) -> bool:
        """
        Start audio capture.
        
        Returns:
            True if capture started successfully, False otherwise
        """
        if not self.sd:
            self.error_message = "sounddevice not available"
            return False
        
        if self.is_active:
            logger.warning("Audio capture already active")
            return True
        
        try:
            # Test audio device access
            self.sd.check_input_settings(
                device=self.input_device,
                channels=self.channels,
                samplerate=self.sample_rate,
                dtype=self.dtype
            )
            
            self.is_active = True
            self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.capture_thread.start()
            
            logger.info("Audio capture started successfully")
            return True
            
        except Exception as e:
            self.error_message = f"Failed to start audio capture: {e}"
            logger.error(f"Audio capture start error: {e}")
            return False
    
    def stop_capture(self):
        """Stop audio capture and cleanup resources."""
        if not self.is_active:
            return
        
        logger.info("Stopping audio capture...")
        self.is_active = False
        
        # Wait for capture thread to finish
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=2.0)
        
        self.capture_thread = None
        logger.info("Audio capture stopped")
    
    def _capture_loop(self):
        """Main audio capture loop running in separate thread."""
        logger.info("Audio capture loop started")
        
        try:
            with self.sd.InputStream(
                device=self.input_device,
                channels=self.channels,
                samplerate=self.sample_rate,
                dtype=self.dtype,
                blocksize=self.frames_per_buffer,
                callback=self._audio_callback
            ):
                while self.is_active:
                    time.sleep(0.1)  # Small sleep to prevent busy waiting
                    
        except Exception as e:
            logger.error(f"Audio capture loop error: {e}")
            self.error_message = f"Audio capture failed: {e}"
            self.is_active = False
        
        logger.info("Audio capture loop stopped")
    
    def _audio_callback(self, indata, frames, time_info, status):
        """Callback function called by sounddevice for each audio frame."""
        if status:
            logger.warning(f"Audio callback status: {status}")
        
        if not self.is_active:
            return
        
        try:
            # Convert to bytes for UDP transmission
            audio_bytes = indata.tobytes()
            
            # Send via client UDP
            if self.client and hasattr(self.client, 'send_audio_packet'):
                self.client.send_audio_packet(audio_bytes)
                
        except Exception as e:
            logger.error(f"Audio callback error: {e}")
    
    def get_error_message(self) -> str:
        """Get last error message."""
        return self.error_message


# ============================================================================
# Audio Playback Implementation
# ============================================================================

class AudioPlayback:
    """
    Audio playback for received UDP audio packets.
    
    Handles multiple audio streams with basic mixing.
    """
    
    def __init__(self):
        """Initialize audio playback."""
        self.is_active = False
        self.playback_thread: Optional[threading.Thread] = None
        self.error_message = ""
        
        # Audio settings (must match capture settings)
        self.sample_rate = 44100
        self.channels = 2
        self.dtype = np.int16
        self.frame_duration = 0.02  # 20ms frames
        self.frames_per_buffer = int(self.sample_rate * self.frame_duration)
        
        # Audio stream buffers for different users
        self.audio_streams: Dict[str, deque] = {}
        self.streams_lock = threading.Lock()
        
        # Try to import sounddevice
        try:
            import sounddevice as sd
            self.sd = sd
            self._detect_output_devices()
            logger.info("AudioPlayback initialized successfully")
        except ImportError as e:
            self.sd = None
            self.error_message = "sounddevice library not available"
            logger.error(f"Failed to import sounddevice: {e}")
        except Exception as e:
            self.sd = None
            self.error_message = f"Audio playback initialization failed: {e}"
            logger.error(f"Audio playback initialization error: {e}")
    
    def _detect_output_devices(self):
        """Detect available audio output devices."""
        if not self.sd:
            return
        
        try:
            devices = self.sd.query_devices()
            output_devices = [d for d in devices if d['max_output_channels'] > 0]
            
            if output_devices:
                # Use default output device
                self.output_device = None  # None means default
                logger.info(f"Found {len(output_devices)} audio output devices")
                logger.info(f"Using default output device")
            else:
                self.output_device = None
                self.error_message = "No audio output devices found"
                logger.warning("No audio output devices detected")
                
        except Exception as e:
            self.error_message = f"Output device detection failed: {e}"
            logger.error(f"Audio output device detection error: {e}")
    
    def start_playback(self) -> bool:
        """
        Start audio playback.
        
        Returns:
            True if playback started successfully, False otherwise
        """
        if not self.sd:
            self.error_message = "sounddevice not available"
            return False
        
        if self.is_active:
            logger.warning("Audio playback already active")
            return True
        
        try:
            # Test audio device access
            self.sd.check_output_settings(
                device=self.output_device,
                channels=self.channels,
                samplerate=self.sample_rate,
                dtype=self.dtype
            )
            
            self.is_active = True
            self.playback_thread = threading.Thread(target=self._playback_loop, daemon=True)
            self.playback_thread.start()
            
            logger.info("Audio playback started successfully")
            return True
            
        except Exception as e:
            self.error_message = f"Failed to start audio playback: {e}"
            logger.error(f"Audio playback start error: {e}")
            return False
    
    def stop_playback(self):
        """Stop audio playback and cleanup resources."""
        if not self.is_active:
            return
        
        logger.info("Stopping audio playback...")
        self.is_active = False
        
        # Wait for playback thread to finish
        if self.playback_thread and self.playback_thread.is_alive():
            self.playback_thread.join(timeout=2.0)
        
        self.playback_thread = None
        
        # Clear audio streams
        with self.streams_lock:
            self.audio_streams.clear()
        
        logger.info("Audio playback stopped")
    
    def add_audio_data(self, username: str, audio_data: bytes):
        """
        Add received audio data for a user.
        
        Args:
            username: Username of the audio sender
            audio_data: Raw PCM audio data
        """
        if not self.is_active:
            return
        
        try:
            # Convert bytes to numpy array
            audio_array = np.frombuffer(audio_data, dtype=self.dtype)
            
            with self.streams_lock:
                # Create stream buffer if it doesn't exist
                if username not in self.audio_streams:
                    self.audio_streams[username] = deque(maxlen=10)  # Buffer up to 10 frames
                
                # Add audio data to user's stream
                self.audio_streams[username].append(audio_array)
                
        except Exception as e:
            logger.error(f"Error adding audio data for {username}: {e}")
    
    def _playback_loop(self):
        """Main audio playback loop running in separate thread."""
        logger.info("Audio playback loop started")
        
        try:
            with self.sd.OutputStream(
                device=self.output_device,
                channels=self.channels,
                samplerate=self.sample_rate,
                dtype=self.dtype,
                blocksize=self.frames_per_buffer,
                callback=self._audio_playback_callback
            ):
                while self.is_active:
                    time.sleep(0.1)  # Small sleep to prevent busy waiting
                    
        except Exception as e:
            logger.error(f"Audio playback loop error: {e}")
            self.error_message = f"Audio playback failed: {e}"
            self.is_active = False
        
        logger.info("Audio playback loop stopped")
    
    def _audio_playback_callback(self, outdata, frames, time_info, status):
        """Callback function called by sounddevice for audio playback."""
        if status:
            logger.warning(f"Audio playback callback status: {status}")
        
        if not self.is_active:
            outdata.fill(0)
            return
        
        try:
            # Initialize output buffer
            mixed_audio = np.zeros((frames, self.channels), dtype=self.dtype)
            active_streams = 0
            
            with self.streams_lock:
                # Mix audio from all active streams
                for username, stream_buffer in list(self.audio_streams.items()):
                    if stream_buffer:
                        try:
                            # Get audio data from buffer
                            audio_data = stream_buffer.popleft()
                            
                            # Ensure correct shape
                            if len(audio_data) == frames * self.channels:
                                audio_data = audio_data.reshape((frames, self.channels))
                                
                                # Simple mixing - add and clip
                                mixed_audio = mixed_audio.astype(np.int32) + audio_data.astype(np.int32)
                                active_streams += 1
                                
                        except Exception as e:
                            logger.error(f"Error processing audio for {username}: {e}")
                
                # Remove empty streams
                self.audio_streams = {k: v for k, v in self.audio_streams.items() if v}
            
            # Normalize mixed audio if multiple streams
            if active_streams > 1:
                mixed_audio = np.clip(mixed_audio // active_streams, -32768, 32767)
            
            # Convert back to int16 and copy to output
            outdata[:] = mixed_audio.astype(self.dtype)
            
        except Exception as e:
            logger.error(f"Audio playback callback error: {e}")
            outdata.fill(0)
    
    def get_error_message(self) -> str:
        """Get last error message."""
        return self.error_message


# ============================================================================
# Video Capture Implementation
# ============================================================================

class VideoCapture:
    """
    Real video capture using OpenCV.
    
    Captures video from camera and sends via LANClient UDP packets.
    Includes fallback test pattern generation when no camera available.
    """
    
    def __init__(self, client):
        """Initialize video capture with client reference."""
        self.client = client
        self.is_active = False
        self.capture_thread: Optional[threading.Thread] = None
        self.error_message = ""
        self.camera = None
        
        # Video settings
        self.width = 640
        self.height = 480
        self.fps = 15  # Conservative frame rate for reliability
        self.frame_interval = 1.0 / self.fps
        
        # Try to import OpenCV
        try:
            import cv2
            self.cv2 = cv2
            self._detect_cameras()
            logger.info("VideoCapture initialized successfully")
        except ImportError as e:
            self.cv2 = None
            self.error_message = "opencv-python library not available"
            logger.error(f"Failed to import cv2: {e}")
    
    def _detect_cameras(self):
        """Detect available camera devices."""
        if not self.cv2:
            return
        
        self.camera_index = 0  # Default to first camera
        
        # Try to find working camera
        for i in range(3):  # Check first 3 camera indices
            try:
                cap = self.cv2.VideoCapture(i)
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        self.camera_index = i
                        logger.info(f"Found working camera at index {i}")
                        cap.release()
                        return
                cap.release()
            except Exception as e:
                logger.debug(f"Camera {i} test failed: {e}")
        
        # No working camera found
        self.camera_index = None
        self.error_message = "No working camera found"
        logger.warning("No working cameras detected")
    
    def start_capture(self) -> bool:
        """
        Start video capture.
        
        Returns:
            True if capture started successfully, False otherwise
        """
        if not self.cv2:
            self.error_message = "OpenCV not available"
            return False
        
        if self.is_active:
            logger.warning("Video capture already active")
            return True
        
        try:
            # Try to open camera
            if self.camera_index is not None:
                self.camera = self.cv2.VideoCapture(self.camera_index)
                if not self.camera.isOpened():
                    self.camera = None
                    self.error_message = "Failed to open camera"
                    logger.warning("Camera failed to open, will use test pattern")
                else:
                    # Configure camera
                    self.camera.set(self.cv2.CAP_PROP_FRAME_WIDTH, self.width)
                    self.camera.set(self.cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                    self.camera.set(self.cv2.CAP_PROP_FPS, self.fps)
                    logger.info(f"Camera opened successfully: {self.width}x{self.height}@{self.fps}fps")
            
            self.is_active = True
            self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.capture_thread.start()
            
            logger.info("Video capture started")
            return True
            
        except Exception as e:
            self.error_message = f"Failed to start video capture: {e}"
            logger.error(f"Video capture start error: {e}")
            return False
    
    def stop_capture(self):
        """Stop video capture and cleanup resources."""
        if not self.is_active:
            return
        
        logger.info("Stopping video capture...")
        self.is_active = False
        
        # Wait for capture thread to finish
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=2.0)
        
        # Release camera
        if self.camera:
            self.camera.release()
            self.camera = None
        
        self.capture_thread = None
        logger.info("Video capture stopped")
    
    def _capture_loop(self):
        """Main video capture loop running in separate thread."""
        logger.info("Video capture loop started")
        
        frame_count = 0
        last_frame_time = time.time()
        
        try:
            while self.is_active:
                current_time = time.time()
                
                # Control frame rate
                if current_time - last_frame_time < self.frame_interval:
                    time.sleep(0.01)
                    continue
                
                # Capture frame
                frame = self._capture_frame(frame_count)
                if frame is not None:
                    # Encode as JPEG
                    success, jpeg_data = self.cv2.imencode('.jpg', frame, [self.cv2.IMWRITE_JPEG_QUALITY, 80])
                    
                    if success:
                        # Send via client UDP
                        if self.client and hasattr(self.client, 'send_video_packet'):
                            self.client.send_video_packet(jpeg_data.tobytes())
                
                last_frame_time = current_time
                frame_count += 1
                
        except Exception as e:
            logger.error(f"Video capture loop error: {e}")
            self.error_message = f"Video capture failed: {e}"
            self.is_active = False
        
        logger.info("Video capture loop stopped")
    
    def _capture_frame(self, frame_count: int):
        """Capture a single frame from camera or generate test pattern."""
        if self.camera and self.camera.isOpened():
            # Try to read from camera
            ret, frame = self.camera.read()
            if ret and frame is not None:
                # Resize if needed
                if frame.shape[1] != self.width or frame.shape[0] != self.height:
                    frame = self.cv2.resize(frame, (self.width, self.height))
                return frame
            else:
                logger.warning("Failed to read from camera, switching to test pattern")
                # Camera failed, release it
                self.camera.release()
                self.camera = None
        
        # Generate test pattern
        return self._generate_test_pattern(frame_count)
    
    def _generate_test_pattern(self, frame_count: int):
        """Generate a test pattern when no camera is available."""
        if not self.cv2:
            return None
        
        # Create a simple animated test pattern
        import numpy as np
        
        # Create base pattern
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
        # Add moving gradient
        offset = (frame_count * 2) % self.width
        for x in range(self.width):
            color_val = int(128 + 127 * np.sin(2 * np.pi * (x + offset) / self.width))
            frame[:, x] = [color_val, 100, 200 - color_val]
        
        # Add text
        text = f"Test Pattern - Frame {frame_count}"
        font = self.cv2.FONT_HERSHEY_SIMPLEX
        text_size = self.cv2.getTextSize(text, font, 0.7, 2)[0]
        text_x = (self.width - text_size[0]) // 2
        text_y = (self.height + text_size[1]) // 2
        
        self.cv2.putText(frame, text, (text_x, text_y), font, 0.7, (255, 255, 255), 2)
        
        return frame
    
    def set_resolution(self, width: int, height: int) -> bool:
        """Set video resolution."""
        self.width = width
        self.height = height
        
        if self.camera and self.camera.isOpened():
            self.camera.set(self.cv2.CAP_PROP_FRAME_WIDTH, width)
            self.camera.set(self.cv2.CAP_PROP_FRAME_HEIGHT, height)
        
        logger.info(f"Video resolution set to {width}x{height}")
        return True
    
    def get_error_message(self) -> str:
        """Get last error message."""
        return self.error_message


# ============================================================================
# Screen Capture Implementation
# ============================================================================

class ScreenCapture:
    """
    Cross-platform screen capture using mss library.
    
    Captures screen content and sends via TCP control channel.
    """
    
    def __init__(self, client):
        """Initialize screen capture with client reference."""
        self.client = client
        self.is_sharing = False
        self.capture_thread: Optional[threading.Thread] = None
        self.error_message = ""
        
        # Screen capture settings
        self.capture_interval = 2.0  # 2 seconds between captures for reliability
        self.jpeg_quality = 70  # Balance between quality and size
        
        # Try to import mss
        try:
            import mss
            self.mss = mss
            logger.info("ScreenCapture initialized successfully")
        except ImportError as e:
            self.mss = None
            self.error_message = "mss library not available"
            logger.error(f"Failed to import mss: {e}")
    
    def start_sharing(self) -> bool:
        """
        Start screen sharing.
        
        Returns:
            True if sharing started successfully, False otherwise
        """
        if not self.mss:
            self.error_message = "mss library not available"
            return False
        
        if self.is_sharing:
            logger.warning("Screen sharing already active")
            return True
        
        try:
            # Test screen capture
            with self.mss.mss() as sct:
                monitor = sct.monitors[1]  # Primary monitor
                screenshot = sct.grab(monitor)
                if screenshot:
                    logger.info(f"Screen capture test successful: {screenshot.width}x{screenshot.height}")
                else:
                    self.error_message = "Screen capture test failed"
                    return False
            
            self.is_sharing = True
            self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.capture_thread.start()
            
            logger.info("Screen sharing started")
            return True
            
        except Exception as e:
            self.error_message = f"Failed to start screen sharing: {e}"
            logger.error(f"Screen sharing start error: {e}")
            return False
    
    def stop_sharing(self):
        """Stop screen sharing."""
        if not self.is_sharing:
            return
        
        logger.info("Stopping screen sharing...")
        self.is_sharing = False
        
        # Wait for capture thread to finish
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=3.0)
        
        self.capture_thread = None
        logger.info("Screen sharing stopped")
    
    def _capture_loop(self):
        """Main screen capture loop running in separate thread."""
        logger.info("Screen capture loop started")
        
        try:
            with self.mss.mss() as sct:
                monitor = sct.monitors[1]  # Primary monitor
                
                while self.is_sharing:
                    try:
                        # Capture screen
                        screenshot = sct.grab(monitor)
                        
                        # Convert to JPEG
                        jpeg_data = self.capture_screen()
                        
                        if jpeg_data and self.client:
                            # Send via TCP control channel
                            screen_frame_msg = {
                                "type": "screen_frame",
                                "from_user": self.client.username,
                                "frame_data": jpeg_data.hex(),  # Convert to hex for JSON
                                "width": screenshot.width,
                                "height": screenshot.height,
                                "timestamp": int(time.time() * 1000)
                            }
                            self.client._send_tcp_message(screen_frame_msg)
                            logger.debug(f"Sent screen frame: {len(jpeg_data)} bytes")
                        
                        # Wait for next capture
                        time.sleep(self.capture_interval)
                        
                    except Exception as e:
                        logger.error(f"Screen capture frame error: {e}")
                        time.sleep(1.0)  # Wait before retry
                        
        except Exception as e:
            logger.error(f"Screen capture loop error: {e}")
            self.error_message = f"Screen capture failed: {e}"
            self.is_sharing = False
        
        logger.info("Screen capture loop stopped")
    
    def capture_screen(self) -> bytes:
        """
        Capture current screen as JPEG data.
        
        Returns:
            JPEG image data as bytes, or empty bytes if capture fails
        """
        if not self.mss:
            return b''
        
        try:
            with self.mss.mss() as sct:
                monitor = sct.monitors[1]  # Primary monitor
                screenshot = sct.grab(monitor)
                
                # Convert to PIL Image for JPEG encoding
                from PIL import Image
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                
                # Save as JPEG to bytes
                import io
                jpeg_buffer = io.BytesIO()
                img.save(jpeg_buffer, format='JPEG', quality=self.jpeg_quality)
                
                return jpeg_buffer.getvalue()
                
        except Exception as e:
            logger.error(f"Screen capture error: {e}")
            self.error_message = f"Screen capture failed: {e}"
            return b''
    
    def get_error_message(self) -> str:
        """Get last error message."""
        return self.error_message


# ============================================================================
# Enhanced Media Capture Manager
# ============================================================================

class MediaCaptureManager:
    """
    Enhanced media capture manager replacing MediaCaptureStub.
    
    Manages audio, video, and screen capture with comprehensive error handling.
    """
    
    def __init__(self, client):
        """Initialize media capture manager."""
        self.client = client
        
        # Initialize capture components
        self.audio_capture = AudioCapture(client)
        self.video_capture = VideoCapture(client)
        self.screen_capture = ScreenCapture(client)
        
        # Initialize playback components
        self.audio_playback = AudioPlayback()
        
        # Network recovery state
        self.recovery_in_progress = False
        self.last_recovery_attempt = 0
        self.recovery_cooldown = 5.0  # seconds
        
        # Set media manager reference in client for recovery
        if hasattr(client, 'set_media_manager'):
            client.set_media_manager(self)
        
        logger.info("MediaCaptureManager initialized")
    
    # Audio methods
    def start_audio(self) -> bool:
        """Start audio capture and playback."""
        # Start playback first
        playback_success = self.audio_playback.start_playback()
        if not playback_success:
            logger.warning("Audio playback failed to start, continuing with capture only")
        
        # Start capture
        capture_success = self.audio_capture.start_capture()
        
        # Update session state
        if capture_success and hasattr(self.client, 'set_media_state'):
            self.client.set_media_state(audio_active=True)
        
        return capture_success  # Return capture success as primary indicator
    
    def stop_audio(self):
        """Stop audio capture and playback."""
        self.audio_capture.stop_capture()
        self.audio_playback.stop_playback()
        
        # Update session state
        if hasattr(self.client, 'set_media_state'):
            self.client.set_media_state(audio_active=False)
    
    def is_audio_active(self) -> bool:
        """Check if audio capture is active."""
        return self.audio_capture.is_active
    
    def process_received_audio(self, username: str, audio_data: bytes):
        """Process received audio data from another user."""
        if self.audio_playback:
            self.audio_playback.add_audio_data(username, audio_data)
    
    # Video methods
    def start_video(self) -> bool:
        """Start video capture."""
        success = self.video_capture.start_capture()
        
        # Update session state
        if success and hasattr(self.client, 'set_media_state'):
            self.client.set_media_state(video_active=True)
        
        return success
    
    def stop_video(self):
        """Stop video capture."""
        self.video_capture.stop_capture()
        
        # Update session state
        if hasattr(self.client, 'set_media_state'):
            self.client.set_media_state(video_active=False)
    
    def is_video_active(self) -> bool:
        """Check if video capture is active."""
        return self.video_capture.is_active
    
    # Screen sharing methods
    def start_screen_share(self) -> bool:
        """Start screen sharing."""
        success = self.screen_capture.start_sharing()
        
        # Update session state
        if success and hasattr(self.client, 'set_media_state'):
            self.client.set_media_state(screen_sharing=True)
        
        return success
    
    def stop_screen_share(self):
        """Stop screen sharing."""
        self.screen_capture.stop_sharing()
        
        # Update session state
        if hasattr(self.client, 'set_media_state'):
            self.client.set_media_state(screen_sharing=False)
    
    def is_screen_sharing(self) -> bool:
        """Check if screen sharing is active."""
        return self.screen_capture.is_sharing
    
    # Error reporting
    def get_audio_error(self) -> str:
        """Get audio capture error message."""
        return self.audio_capture.get_error_message()
    
    def get_video_error(self) -> str:
        """Get video capture error message."""
        return self.video_capture.get_error_message()
    
    def get_screen_error(self) -> str:
        """Get screen capture error message."""
        return self.screen_capture.get_error_message()
    
    def cleanup(self):
        """Cleanup all media capture resources."""
        logger.info("Cleaning up media capture resources...")
        self.stop_audio()
        self.stop_video()
        self.stop_screen_share()
        logger.info("Media capture cleanup complete")
    
    def get_playback_error(self) -> str:
        """Get audio playback error message."""
        return self.audio_playback.get_error_message() if self.audio_playback else ""
    
    def handle_network_interruption(self):
        """Handle network interruption for media streams."""
        try:
            logger.info("Handling network interruption for media streams...")
            
            # Pause media streams but don't fully stop them
            if self.is_audio_active():
                logger.info("Pausing audio capture due to network interruption")
                # Don't stop completely, just pause transmission
                
            if self.is_video_active():
                logger.info("Pausing video capture due to network interruption")
                # Don't stop completely, just pause transmission
                
            if self.is_screen_sharing():
                logger.info("Pausing screen sharing due to network interruption")
                # Don't stop completely, just pause transmission
                
        except Exception as e:
            logger.error(f"Error handling network interruption: {e}")
    
    def handle_network_recovery(self):
        """Handle network recovery for media streams."""
        try:
            current_time = time.time()
            
            # Check recovery cooldown
            if self.recovery_in_progress or (current_time - self.last_recovery_attempt) < self.recovery_cooldown:
                logger.debug("Media recovery already in progress or in cooldown period")
                return
            
            self.recovery_in_progress = True
            self.last_recovery_attempt = current_time
            
            logger.info("Handling network recovery for media streams...")
            
            # Check network quality before attempting recovery
            if hasattr(self.client, 'get_network_quality'):
                network_quality = self.client.get_network_quality()
                if network_quality < 0.3:
                    logger.info("Network quality too poor for media recovery, waiting...")
                    self.recovery_in_progress = False
                    return
            
            # Attempt to recover active streams
            recovery_success = True
            
            # Get current media state from client session
            if hasattr(self.client, 'session_state'):
                media_state = self.client.session_state.get('media_state', {})
                
                if media_state.get('audio_active', False) and not self.is_audio_active():
                    logger.info("Attempting to recover audio stream...")
                    if not self._recover_audio_stream():
                        recovery_success = False
                
                if media_state.get('video_active', False) and not self.is_video_active():
                    logger.info("Attempting to recover video stream...")
                    if not self._recover_video_stream():
                        recovery_success = False
                
                if media_state.get('screen_sharing', False) and not self.is_screen_sharing():
                    logger.info("Attempting to recover screen sharing...")
                    if not self._recover_screen_share():
                        recovery_success = False
            
            if recovery_success:
                logger.info("Media stream recovery completed successfully")
            else:
                logger.warning("Some media streams could not be recovered")
            
            self.recovery_in_progress = False
            
        except Exception as e:
            logger.error(f"Error during network recovery: {e}")
            self.recovery_in_progress = False
    
    def _recover_audio_stream(self) -> bool:
        """Recover audio stream after network interruption."""
        try:
            # Check if audio devices are still available
            if hasattr(self.audio_capture, '_detect_devices'):
                self.audio_capture._detect_devices()
            
            # Restart audio capture
            success = self.audio_capture.start_capture()
            if success:
                # Also restart playback if it was stopped
                if not self.audio_playback.is_active:
                    self.audio_playback.start_playback()
                logger.info("Audio stream recovered successfully")
                return True
            else:
                logger.warning("Failed to recover audio stream")
                return False
                
        except Exception as e:
            logger.error(f"Error recovering audio stream: {e}")
            return False
    
    def _recover_video_stream(self) -> bool:
        """Recover video stream after network interruption."""
        try:
            # Check if camera is still available
            if hasattr(self.video_capture, '_detect_cameras'):
                self.video_capture._detect_cameras()
            
            # Restart video capture
            success = self.video_capture.start_capture()
            if success:
                logger.info("Video stream recovered successfully")
                return True
            else:
                logger.warning("Failed to recover video stream")
                return False
                
        except Exception as e:
            logger.error(f"Error recovering video stream: {e}")
            return False
    
    def _recover_screen_share(self) -> bool:
        """Recover screen sharing after network interruption."""
        try:
            # Restart screen sharing
            success = self.screen_capture.start_sharing()
            if success:
                logger.info("Screen sharing recovered successfully")
                return True
            else:
                logger.warning("Failed to recover screen sharing")
                return False
                
        except Exception as e:
            logger.error(f"Error recovering screen sharing: {e}")
            return False
    
    def check_media_health(self) -> dict:
        """
        Check the health of all media streams.
        
        Returns:
            Dictionary with health status of each media type
        """
        health_status = {
            'audio': {
                'active': self.is_audio_active(),
                'error': self.get_audio_error(),
                'healthy': self.is_audio_active() and not self.get_audio_error()
            },
            'video': {
                'active': self.is_video_active(),
                'error': self.get_video_error(),
                'healthy': self.is_video_active() and not self.get_video_error()
            },
            'screen_share': {
                'active': self.is_screen_sharing(),
                'error': self.get_screen_error(),
                'healthy': self.is_screen_sharing() and not self.get_screen_error()
            },
            'playback': {
                'active': self.audio_playback.is_active if self.audio_playback else False,
                'error': self.get_playback_error(),
                'healthy': (self.audio_playback.is_active if self.audio_playback else False) and not self.get_playback_error()
            }
        }
        
        return health_status