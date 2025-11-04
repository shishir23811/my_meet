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
    Includes real-time audio strength detection.
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
        
        # Audio strength detection
        self.audio_strength = 0.0  # Current audio strength (0.0 to 1.0)
        self.peak_strength = 0.0   # Peak strength in current session
        self.strength_history = deque(maxlen=50)  # Last 50 measurements (1 second at 20ms frames)
        self.strength_callback: Optional[Callable[[float, float], None]] = None  # Callback for strength updates
        self.silence_threshold = 0.0001  # Below this is considered silence (very sensitive)
        self.speaking_threshold = 0.001  # Above this is considered speaking (very sensitive)
        self.loud_threshold = 0.01     # Above this is considered loud speaking (very sensitive)
        self.strength_smoothing = 0.3   # Less smoothing for more responsive detection
        
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
            # Calculate audio strength from input data
            raw_strength = self._calculate_audio_strength(indata)
            self._update_strength_metrics(raw_strength)
            
            # Debug: Log audio activity
            if raw_strength > 0.0001:  # Only log when there's some audio
                logger.debug(f"Audio captured: strength={raw_strength:.6f}, size={len(indata)} frames")
            
            # Convert to bytes for UDP transmission
            audio_bytes = indata.tobytes()
            
            # Send via client UDP (always send, even if silent, for continuous stream)
            if self.client and hasattr(self.client, 'send_audio_packet'):
                self.client.send_audio_packet(audio_bytes)
                if raw_strength > 0.0001:  # Only log when there's audio activity
                    logger.debug(f"Audio packet sent: {len(audio_bytes)} bytes")
                
        except Exception as e:
            logger.error(f"Audio callback error: {e}")
    
    def get_error_message(self) -> str:
        """Get last error message."""
        return self.error_message
    
    # ========================================================================
    # Audio Strength Detection Methods
    # ========================================================================
    
    def set_strength_callback(self, callback: Callable[[float, float], None]):
        """
        Set callback function for audio strength updates.
        
        Args:
            callback: Function that receives (current_strength, peak_strength) as parameters
        """
        self.strength_callback = callback
    
    def _calculate_audio_strength(self, audio_data: np.ndarray) -> float:
        """
        Calculate the audio strength (volume level) from audio data.
        
        Args:
            audio_data: NumPy array of audio samples
            
        Returns:
            Audio strength value between 0.0 and 1.0
        """
        try:
            # Convert to float for calculations
            audio_float = audio_data.astype(np.float32)
            
            # Calculate RMS (Root Mean Square) for overall volume
            rms = np.sqrt(np.mean(audio_float ** 2))
            
            # Normalize to 0-1 range (assuming 16-bit audio range)
            max_amplitude = 32767.0  # Maximum value for int16
            normalized_rms = rms / max_amplitude
            
            # Use simpler linear scaling for better responsiveness
            # Apply a small amplification to make quiet sounds more detectable
            strength = min(normalized_rms * 10.0, 1.0)  # Amplify by 10x, cap at 1.0
            
            return strength
            
        except Exception as e:
            logger.error(f"Error calculating audio strength: {e}")
            return 0.0
    
    def _update_strength_metrics(self, raw_strength: float):
        """
        Update audio strength metrics with smoothing and history tracking.
        
        Args:
            raw_strength: Raw calculated strength value
        """
        try:
            # Apply smoothing to reduce jitter
            if self.audio_strength == 0.0:
                # First measurement
                self.audio_strength = raw_strength
            else:
                # Exponential moving average for smoothing
                self.audio_strength = (self.strength_smoothing * self.audio_strength + 
                                     (1 - self.strength_smoothing) * raw_strength)
            
            # Update peak strength
            if self.audio_strength > self.peak_strength:
                self.peak_strength = self.audio_strength
            
            # Add to history for trend analysis
            self.strength_history.append(self.audio_strength)
            
            # Call callback if set
            if self.strength_callback:
                self.strength_callback(self.audio_strength, self.peak_strength)
                
        except Exception as e:
            logger.error(f"Error updating strength metrics: {e}")
    
    def get_audio_strength(self) -> float:
        """
        Get current audio strength level.
        
        Returns:
            Current audio strength (0.0 to 1.0)
        """
        return self.audio_strength
    
    def get_peak_strength(self) -> float:
        """
        Get peak audio strength since capture started.
        
        Returns:
            Peak audio strength (0.0 to 1.0)
        """
        return self.peak_strength
    
    def get_average_strength(self, seconds: float = 1.0) -> float:
        """
        Get average audio strength over the specified time period.
        
        Args:
            seconds: Time period in seconds (default: 1.0)
            
        Returns:
            Average audio strength over the period
        """
        if not self.strength_history:
            return 0.0
        
        # Calculate how many samples to include
        samples_per_second = 1.0 / self.frame_duration  # 50 samples per second at 20ms frames
        num_samples = min(int(seconds * samples_per_second), len(self.strength_history))
        
        if num_samples <= 0:
            return 0.0
        
        # Get recent samples
        recent_samples = list(self.strength_history)[-num_samples:]
        return sum(recent_samples) / len(recent_samples)
    
    def is_speaking(self) -> bool:
        """
        Determine if the user is currently speaking.
        
        Returns:
            True if audio level indicates speaking
        """
        return self.audio_strength > self.speaking_threshold
    
    def is_loud_speaking(self) -> bool:
        """
        Determine if the user is speaking loudly.
        
        Returns:
            True if audio level indicates loud speaking
        """
        return self.audio_strength > self.loud_threshold
    
    def is_silent(self) -> bool:
        """
        Determine if the audio is currently silent.
        
        Returns:
            True if audio level is below silence threshold
        """
        return self.audio_strength < self.silence_threshold
    
    def reset_peak_strength(self):
        """Reset the peak strength measurement."""
        self.peak_strength = 0.0
    
    def get_strength_level_description(self) -> str:
        """
        Get a human-readable description of the current audio strength level.
        
        Returns:
            Description string (e.g., "Silent", "Speaking", "Loud")
        """
        if self.is_silent():
            return "Silent"
        elif self.is_loud_speaking():
            return "Loud"
        elif self.is_speaking():
            return "Speaking"
        else:
            return "Quiet"
    
    def get_strength_percentage(self) -> int:
        """
        Get audio strength as a percentage (0-100).
        
        Returns:
            Audio strength as percentage
        """
        return int(self.audio_strength * 100)
    
    def set_thresholds(self, silence: float = None, speaking: float = None, loud: float = None):
        """
        Set custom thresholds for audio level detection.
        
        Args:
            silence: Silence threshold (0.0 to 1.0)
            speaking: Speaking threshold (0.0 to 1.0)  
            loud: Loud speaking threshold (0.0 to 1.0)
        """
        if silence is not None:
            self.silence_threshold = max(0.0, min(1.0, silence))
        if speaking is not None:
            self.speaking_threshold = max(0.0, min(1.0, speaking))
        if loud is not None:
            self.loud_threshold = max(0.0, min(1.0, loud))
        
        logger.info(f"Audio thresholds updated: silence={self.silence_threshold:.3f}, "
                   f"speaking={self.speaking_threshold:.3f}, loud={self.loud_threshold:.3f}")


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
                        jpeg_bytes = jpeg_data.tobytes()
                        
                        # Send via client UDP to other users
                        if self.client and hasattr(self.client, 'send_video_packet'):
                            self.client.send_video_packet(jpeg_bytes)
                        
                        # Send to local GUI for self-preview
                        if hasattr(self.client, 'update_self_video_frame'):
                            self.client.update_self_video_frame(jpeg_bytes)
                
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
        
        try:
            # Create a simple animated test pattern
            import numpy as np
            
            # Create base pattern with a nice gradient background
            frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
            
            # Add moving gradient background
            offset = (frame_count * 3) % (self.width * 2)  # Slower movement
            for y in range(self.height):
                for x in range(self.width):
                    # Create a diagonal gradient with animation
                    gradient_pos = (x + y + offset) % (self.width + self.height)
                    normalized_pos = gradient_pos / (self.width + self.height)
                    
                    # Generate RGB values with smooth transitions
                    r = int(128 + 127 * np.sin(2 * np.pi * normalized_pos))
                    g = int(128 + 127 * np.sin(2 * np.pi * normalized_pos + np.pi / 3))
                    b = int(128 + 127 * np.sin(2 * np.pi * normalized_pos + 2 * np.pi / 3))
                    
                    frame[y, x] = [b, g, r]  # OpenCV uses BGR format
            
            # Add animated circles
            center_x, center_y = self.width // 2, self.height // 2
            radius = int(50 + 30 * np.sin(frame_count * 0.1))
            self.cv2.circle(frame, (center_x, center_y), radius, (255, 255, 255), 2)
            
            # Add text overlay
            text = f"Test Pattern - Frame {frame_count}"
            font = self.cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.7
            thickness = 2
            
            # Get text size for centering
            text_size = self.cv2.getTextSize(text, font, font_scale, thickness)[0]
            text_x = (self.width - text_size[0]) // 2
            text_y = (self.height + text_size[1]) // 2
            
            # Add text with black outline for better visibility
            self.cv2.putText(frame, text, (text_x, text_y), font, font_scale, (0, 0, 0), thickness + 2)
            self.cv2.putText(frame, text, (text_x, text_y), font, font_scale, (255, 255, 255), thickness)
            
            # Add timestamp in corner
            timestamp_text = f"Time: {int(time.time()) % 10000}"
            self.cv2.putText(frame, timestamp_text, (10, 30), font, 0.5, (255, 255, 255), 1)
            
            return frame
            
        except Exception as e:
            logger.error(f"Error generating test pattern: {e}")
            # Return a simple solid color frame as fallback
            fallback_frame = np.full((self.height, self.width, 3), [64, 128, 192], dtype=np.uint8)
            return fallback_frame
    
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
                
                # Convert to OpenCV format for JPEG encoding
                import numpy as np
                import cv2
                
                # Convert BGRA to BGR using numpy (OpenCV's native format)
                img_array = np.frombuffer(screenshot.bgra, dtype=np.uint8)
                img_array = img_array.reshape((screenshot.height, screenshot.width, 4))
                
                # Convert BGRA to BGR (OpenCV's native format for proper color encoding)
                img_bgr = cv2.cvtColor(img_array, cv2.COLOR_BGRA2BGR)
                
                # Encode as JPEG using OpenCV
                encode_params = [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality]
                success, jpeg_buffer = cv2.imencode('.jpg', img_bgr, encode_params)
                
                if success:
                    return jpeg_buffer.tobytes()
                else:
                    logger.error("Failed to encode screen capture as JPEG")
                    return b''
                
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
    
    Manages audio, video, and screen capture with comprehensive error handling
    and audio strength detection capabilities.
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
    
    # ========================================================================
    # Audio Methods with Strength Detection
    # ========================================================================
    
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
    
    # Audio strength detection methods
    def set_audio_strength_callback(self, callback: Callable[[float, float], None]):
        """
        Set callback for audio strength updates.
        
        Args:
            callback: Function that receives (current_strength, peak_strength)
        """
        if self.audio_capture:
            self.audio_capture.set_strength_callback(callback)
    
    def get_audio_strength(self) -> float:
        """
        Get current audio strength level.
        
        Returns:
            Current audio strength (0.0 to 1.0)
        """
        if self.audio_capture:
            return self.audio_capture.get_audio_strength()
        return 0.0
    
    def get_peak_audio_strength(self) -> float:
        """
        Get peak audio strength for current session.
        
        Returns:
            Peak audio strength (0.0 to 1.0)
        """
        if self.audio_capture:
            return self.audio_capture.get_peak_strength()
        return 0.0
    
    def get_average_audio_strength(self, seconds: float = 1.0) -> float:
        """
        Get average audio strength over recent history.
        
        Args:
            seconds: Time period in seconds (default: 1.0)
        
        Returns:
            Average audio strength (0.0 to 1.0)
        """
        if self.audio_capture:
            return self.audio_capture.get_average_strength(seconds)
        return 0.0
    
    def is_user_speaking(self) -> bool:
        """
        Check if user is currently speaking.
        
        Returns:
            True if audio strength is above speaking threshold
        """
        if self.audio_capture:
            return self.audio_capture.is_speaking()
        return False
    
    def is_user_speaking_loudly(self) -> bool:
        """
        Check if user is speaking loudly.
        
        Returns:
            True if audio strength is above loud speaking threshold
        """
        if self.audio_capture:
            return self.audio_capture.is_loud_speaking()
        return False
    
    def is_user_silent(self) -> bool:
        """
        Check if user is currently silent.
        
        Returns:
            True if audio strength is below silence threshold
        """
        if self.audio_capture:
            return self.audio_capture.is_silent()
        return True
    
    def get_audio_strength_description(self) -> str:
        """
        Get human-readable description of current audio strength level.
        
        Returns:
            String description of current audio level
        """
        if self.audio_capture:
            return self.audio_capture.get_strength_level_description()
        return "No Audio"
    
    def get_audio_strength_percentage(self) -> int:
        """
        Get audio strength as a percentage (0-100).
        
        Returns:
            Audio strength as percentage
        """
        if self.audio_capture:
            return self.audio_capture.get_strength_percentage()
        return 0
    
    def reset_peak_audio_strength(self):
        """Reset the peak audio strength measurement."""
        if self.audio_capture:
            self.audio_capture.reset_peak_strength()
    
    def set_audio_thresholds(self, silence: float = None, speaking: float = None, loud: float = None):
        """
        Set custom thresholds for audio level detection.
        
        Args:
            silence: Silence threshold (0.0 to 1.0)
            speaking: Speaking threshold (0.0 to 1.0)  
            loud: Loud speaking threshold (0.0 to 1.0)
        """
        if self.audio_capture:
            self.audio_capture.set_thresholds(silence, speaking, loud)
    
    # ========================================================================
    # Video Methods
    # ========================================================================
    
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
    
    # ========================================================================
    # Screen Sharing Methods
    # ========================================================================
    
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
    
    # ========================================================================
    # Error Reporting Methods
    # ========================================================================
    
    def get_audio_error(self) -> str:
        """Get audio capture error message."""
        return self.audio_capture.get_error_message()
    
    def get_video_error(self) -> str:
        """Get video capture error message."""
        return self.video_capture.get_error_message()
    
    def get_screen_error(self) -> str:
        """Get screen capture error message."""
        return self.screen_capture.get_error_message()
    
    def get_playback_error(self) -> str:
        """Get audio playback error message."""
        return self.audio_playback.get_error_message() if self.audio_playback else ""
    
    def cleanup(self):
        """Cleanup all media capture resources."""
        logger.info("Cleaning up media capture resources...")
        self.stop_audio()
        self.stop_video()
        self.stop_screen_share()
        logger.info("Media capture cleanup complete")
    
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
                'healthy': self.is_audio_active() and not self.get_audio_error(),
                'strength': self.get_audio_strength(),
                'speaking': self.is_user_speaking()
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