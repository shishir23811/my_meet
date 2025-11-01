"""
User profile management for LAN Communication Application.
Handles loading, saving, and validation of user profiles stored in profiles.json.
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from utils.logger import setup_logger
from utils.config import PROFILES_FILE

logger = setup_logger(__name__)

class ProfileManager:
    """Manages user profiles stored in profiles.json."""
    
    def __init__(self, profiles_file: Path = PROFILES_FILE):
        """
        Initialize profile manager.
        
        Args:
            profiles_file: Path to profiles JSON file
        """
        self.profiles_file = profiles_file
        self.profiles: Dict[str, Dict] = {}
        self.load()
    
    def load(self) -> None:
        """Load profiles from JSON file."""
        if self.profiles_file.exists():
            try:
                with open(self.profiles_file, 'r') as f:
                    data = json.load(f)
                    self.profiles = data.get('users', {})
                logger.info(f"Loaded {len(self.profiles)} profiles from {self.profiles_file}")
            except Exception as e:
                logger.error(f"Failed to load profiles: {e}")
                self.profiles = {}
        else:
            logger.info("Profiles file not found, creating new one")
            self.profiles = {}
            self.save()
    
    def save(self) -> None:
        """Save profiles to JSON file."""
        try:
            data = {
                "users": self.profiles,
                "last_updated": datetime.now().isoformat()
            }
            with open(self.profiles_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(self.profiles)} profiles to {self.profiles_file}")
        except Exception as e:
            logger.error(f"Failed to save profiles: {e}")
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash password using SHA-256.
        
        Args:
            password: Plain text password
        
        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    def create_profile(self, username: str, display_name: str, password: str) -> bool:
        """
        Create a new user profile.
        
        Args:
            username: Unique username
            display_name: Display name
            password: Plain text password (will be hashed)
        
        Returns:
            True if profile created successfully, False if username exists
        """
        if username in self.profiles:
            logger.warning(f"Profile creation failed: username '{username}' already exists")
            return False
        
        self.profiles[username] = {
            "username": username,
            "display_name": display_name,
            "password_hash": self.hash_password(password),
            "created_at": datetime.now().isoformat(),
            "last_login": None
        }
        self.save()
        logger.info(f"Created profile for user '{username}'")
        return True
    
    def authenticate(self, username: str, password: str) -> bool:
        """
        Authenticate user credentials.
        
        Args:
            username: Username
            password: Plain text password
        
        Returns:
            True if credentials are valid, False otherwise
        """
        if username not in self.profiles:
            logger.warning(f"Authentication failed: user '{username}' not found")
            return False
        
        password_hash = self.hash_password(password)
        is_valid = self.profiles[username]["password_hash"] == password_hash
        
        if is_valid:
            # Update last login timestamp
            self.profiles[username]["last_login"] = datetime.now().isoformat()
            self.save()
            logger.info(f"User '{username}' authenticated successfully")
        else:
            logger.warning(f"Authentication failed: invalid password for user '{username}'")
        
        return is_valid
    
    def get_profile(self, username: str) -> Optional[Dict]:
        """
        Get profile data for a user.
        
        Args:
            username: Username
        
        Returns:
            Profile dictionary or None if not found
        """
        return self.profiles.get(username)
    
    def list_usernames(self) -> List[str]:
        """Get list of all registered usernames."""
        return list(self.profiles.keys())
    
    def delete_profile(self, username: str) -> bool:
        """
        Delete a user profile.
        
        Args:
            username: Username to delete
        
        Returns:
            True if deleted, False if not found
        """
        if username in self.profiles:
            del self.profiles[username]
            self.save()
            logger.info(f"Deleted profile for user '{username}'")
            return True
        return False

# Global profile manager instance
profile_manager = ProfileManager()
