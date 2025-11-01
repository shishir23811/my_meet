"""
Network protocol definitions for LAN Communication Application.

Defines message types, packet structures, and serialization for TCP control
channel and UDP media streams.

TCP Control Channel Messages (JSON):
- Authentication, session management, chat, file transfer metadata
- All messages are JSON objects with 'type' field

UDP Media Packets (Binary):
- Audio/video streams with custom header for sequencing and identification
- Header: [stream_id(4B)][seq_num(4B)][timestamp(8B)][payload_size(4B)][payload]
"""

import struct
import time
from enum import Enum
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
import json

# ============================================================================
# TCP Control Message Types
# ============================================================================

class MessageType(Enum):
    """Enumeration of all TCP control message types."""
    
    # Authentication & Session
    AUTH_REQUEST = "auth_request"
    AUTH_RESPONSE = "auth_response"
    JOIN_SESSION = "join_session"
    LEAVE_SESSION = "leave_session"
    SESSION_UPDATE = "session_update"
    
    # Chat
    CHAT_MESSAGE = "chat_message"
    
    # File Transfer
    FILE_OFFER = "file_offer"
    FILE_REQUEST = "file_request"
    FILE_CHUNK = "file_chunk"
    FILE_COMPLETE = "file_complete"
    FILE_LIST = "file_list"
    
    # Media Control
    MEDIA_START = "media_start"
    MEDIA_STOP = "media_stop"
    SCREEN_SHARE_START = "screen_share_start"
    SCREEN_SHARE_STOP = "screen_share_stop"
    SCREEN_FRAME = "screen_frame"
    
    # User Presence
    USER_JOINED = "user_joined"
    USER_LEFT = "user_left"
    USER_LIST = "user_list"
    
    # Heartbeat
    PING = "ping"
    PONG = "pong"
    
    # Error
    ERROR = "error"

class CommunicationMode(Enum):
    """Communication addressing modes."""
    UNICAST = "unicast"       # 1:1 to single user
    MULTICAST = "multicast"   # to selected users
    BROADCAST = "broadcast"   # to all users

# ============================================================================
# TCP Message Classes
# ============================================================================

@dataclass
class ControlMessage:
    """Base class for all TCP control messages."""
    type: str
    from_user: str
    timestamp: float
    
    def to_json(self) -> str:
        """Serialize message to JSON string."""
        data = asdict(self)
        return json.dumps(data)
    
    @staticmethod
    def from_json(json_str: str) -> Dict[str, Any]:
        """Deserialize message from JSON string."""
        return json.loads(json_str)

@dataclass
class ChatMessage(ControlMessage):
    """Chat message with addressing mode."""
    mode: str  # unicast, multicast, broadcast
    to_users: List[str]  # target users (empty for broadcast)
    payload: str  # message text
    
    def __init__(self, from_user: str, payload: str, 
                 mode: str = "broadcast", to_users: List[str] = None):
        super().__init__(
            type=MessageType.CHAT_MESSAGE.value,
            from_user=from_user,
            timestamp=time.time()
        )
        self.mode = mode
        self.to_users = to_users or []
        self.payload = payload

@dataclass
class FileOfferMessage(ControlMessage):
    """File transfer offer message."""
    file_id: str
    filename: str
    file_size: int
    mode: str
    to_users: List[str]
    
    def __init__(self, from_user: str, file_id: str, filename: str, 
                 file_size: int, mode: str = "broadcast", to_users: List[str] = None):
        super().__init__(
            type=MessageType.FILE_OFFER.value,
            from_user=from_user,
            timestamp=time.time()
        )
        self.file_id = file_id
        self.filename = filename
        self.file_size = file_size
        self.mode = mode
        self.to_users = to_users or []

@dataclass
class AuthRequest:
    """Authentication request message."""
    type: str = MessageType.AUTH_REQUEST.value
    username: str = ""
    password_hash: str = ""
    session_id: Optional[str] = None
    
    def to_json(self) -> str:
        return json.dumps(asdict(self))

@dataclass
class SessionUpdate:
    """Session state update message."""
    type: str = MessageType.SESSION_UPDATE.value
    users: List[Dict[str, Any]] = None
    timestamp: float = None
    
    def __post_init__(self):
        if self.users is None:
            self.users = []
        if self.timestamp is None:
            self.timestamp = time.time()
    
    def to_json(self) -> str:
        return json.dumps(asdict(self))

# ============================================================================
# UDP Media Packet Structure
# ============================================================================

# UDP packet header format: >IIQI (big-endian: uint32, uint32, uint64, uint32)
# stream_id (4 bytes) | seq_num (4 bytes) | timestamp (8 bytes) | payload_size (4 bytes)
UDP_HEADER_FORMAT = ">IIQI"
UDP_HEADER_SIZE = struct.calcsize(UDP_HEADER_FORMAT)

class StreamType(Enum):
    """Media stream types for UDP packets."""
    AUDIO = 0x01
    VIDEO = 0x02
    
@dataclass
class UDPPacket:
    """UDP media packet structure."""
    stream_id: int      # Unique stream identifier
    seq_num: int        # Sequence number for ordering
    timestamp: int      # Microsecond timestamp
    payload: bytes      # Encoded media data
    
    def pack(self) -> bytes:
        """Pack UDP packet into binary format."""
        header = struct.pack(
            UDP_HEADER_FORMAT,
            self.stream_id,
            self.seq_num,
            self.timestamp,
            len(self.payload)
        )
        return header + self.payload
    
    @staticmethod
    def unpack(data: bytes) -> Optional['UDPPacket']:
        """Unpack binary data into UDPPacket."""
        if len(data) < UDP_HEADER_SIZE:
            return None
        
        header = data[:UDP_HEADER_SIZE]
        payload = data[UDP_HEADER_SIZE:]
        
        stream_id, seq_num, timestamp, payload_size = struct.unpack(
            UDP_HEADER_FORMAT, header
        )
        
        if len(payload) != payload_size:
            return None
        
        return UDPPacket(stream_id, seq_num, timestamp, payload)

# ============================================================================
# Helper Functions
# ============================================================================

def create_message(msg_type: MessageType, **kwargs) -> Dict[str, Any]:
    """
    Create a control message dictionary.
    
    Args:
        msg_type: Type of message to create
        **kwargs: Message-specific fields
    
    Returns:
        Dictionary representing the message
    """
    message = {
        "type": msg_type.value,
        "timestamp": time.time(),
        **kwargs
    }
    return message

def serialize_message(message: Dict[str, Any]) -> bytes:
    """Serialize message dictionary to bytes for TCP transmission."""
    json_str = json.dumps(message)
    json_bytes = json_str.encode('utf-8')
    # Prefix with 4-byte length header for framing
    length = struct.pack(">I", len(json_bytes))
    return length + json_bytes

def deserialize_message(data: bytes) -> Optional[Dict[str, Any]]:
    """
    Deserialize bytes to message dictionary.
    Expects 4-byte length prefix.
    """
    if len(data) < 4:
        return None
    
    length = struct.unpack(">I", data[:4])[0]
    if len(data) < 4 + length:
        return None
    
    json_bytes = data[4:4+length]
    json_str = json_bytes.decode('utf-8')
    return json.loads(json_str)

def generate_stream_id(username: str, stream_type: StreamType) -> int:
    """
    Generate unique stream ID from username and stream type.
    
    Args:
        username: Username of the stream owner
        stream_type: Type of stream (AUDIO or VIDEO)
    
    Returns:
        32-bit stream identifier
    """
    # Simple hash-based ID generation
    hash_val = hash(username) & 0x7FFFFFFF  # Keep positive
    return (hash_val << 4) | stream_type.value
