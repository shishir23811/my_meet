"""
Configuration management for LAN Communication Application.
Handles application settings, network ports, and default values.
"""

import json
import socket
from pathlib import Path
from typing import Any, Dict, Tuple
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent

# Network configuration
# Using high-numbered ports to avoid firewall issues
# Ports 49152-65535 are typically unrestricted
DEFAULT_TCP_PORT = 54321  # High port, less likely to be blocked
DEFAULT_UDP_PORT = 54322  # High port, less likely to be blocked
BUFFER_SIZE = 8192
UDP_PACKET_SIZE = 1400  # Safe size for UDP to avoid fragmentation

# File transfer configuration
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
CHUNK_SIZE = 64 * 1024  # 64 KB chunks for file transfer
TEMP_FILES_DIR = PROJECT_ROOT / "temp_files"

# Media configuration
VIDEO_WIDTH = 640
VIDEO_HEIGHT = 480
VIDEO_FPS = 30
AUDIO_SAMPLE_RATE = 44100
AUDIO_CHANNELS = 2

# Profiles configuration
PROFILES_FILE = PROJECT_ROOT / "profiles.json"

class Config:
    """
    Configuration manager for application settings.
    Loads and saves configuration from/to JSON file.
    """
    
    def __init__(self, config_file: Path = None):
        """Initialize configuration manager."""
        self.config_file = config_file or (PROJECT_ROOT / "config.json")
        self.settings: Dict[str, Any] = self._load_defaults()
        self.load()
    
    def _load_defaults(self) -> Dict[str, Any]:
        """Load default configuration values."""
        return {
            "network": {
                "tcp_port": DEFAULT_TCP_PORT,
                "udp_port": DEFAULT_UDP_PORT,
                "buffer_size": BUFFER_SIZE
            },
            "media": {
                "video_width": VIDEO_WIDTH,
                "video_height": VIDEO_HEIGHT,
                "video_fps": VIDEO_FPS,
                "audio_sample_rate": AUDIO_SAMPLE_RATE,
                "audio_channels": AUDIO_CHANNELS
            },
            "ui": {
                "theme": "dark",
                "remember_me": False,
                "last_username": ""
            }
        }
    
    def load(self) -> None:
        """Load configuration from file, or use defaults if file doesn't exist."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    loaded_settings = json.load(f)
                    self.settings.update(loaded_settings)
                logger.info(f"Configuration loaded from {self.config_file}")
            except Exception as e:
                logger.error(f"Failed to load configuration: {e}")
        else:
            logger.info("Using default configuration")
    
    def save(self) -> None:
        """Save current configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
            logger.info(f"Configuration saved to {self.config_file}")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-separated key."""
        keys = key.split('.')
        value = self.settings
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k, default)
            else:
                return default
        return value
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value by dot-separated key."""
        keys = key.split('.')
        settings = self.settings
        for k in keys[:-1]:
            settings = settings.setdefault(k, {})
        settings[keys[-1]] = value

def find_available_ports(start_port: int = 49152, count: int = 2) -> Tuple[int, int]:
    """
    Find available TCP and UDP ports starting from start_port.
    
    Args:
        start_port: Starting port number (default: 49152 - dynamic port range)
        count: Number of consecutive ports needed (default: 2 for TCP+UDP)
    
    Returns:
        Tuple of (tcp_port, udp_port)
    """
    for port in range(start_port, 65535 - count):
        tcp_port = port
        udp_port = port + 1
        
        # Test TCP port
        try:
            tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tcp_sock.bind(('', tcp_port))
            tcp_sock.close()
        except OSError:
            continue  # Port in use, try next
        
        # Test UDP port
        try:
            udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            udp_sock.bind(('', udp_port))
            udp_sock.close()
            
            # Both ports available
            logger.info(f"Found available ports: TCP {tcp_port}, UDP {udp_port}")
            return tcp_port, udp_port
            
        except OSError:
            continue  # Port in use, try next
    
    # Fallback to default ports if no available ports found
    logger.warning("No available ports found in dynamic range, using defaults")
    return DEFAULT_TCP_PORT, DEFAULT_UDP_PORT

# Global configuration instance
config = Config()
