# LAN Communication Application - Architecture

## System Overview

The LAN Communication Application is a client-server system designed for local area network communication without internet connectivity. It follows a centralized architecture where one host acts as the server, and multiple clients connect to it for real-time communication.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Application                       │
│  ┌────────────┐   ┌──────────────┐   ┌────────────────────┐   │
│  │   GUI      │   │   Client     │   │  Media Capture     │   │
│  │  (PySide6) │◄─►│  Networking  │◄─►│     (Stub)         │   │
│  └────────────┘   └──────────────┘   └────────────────────┘   │
│        │                 │ TCP                                  │
│        │                 │ UDP                                  │
└────────┼─────────────────┼──────────────────────────────────────┘
         │                 │
         │                 ▼
         │          ┌──────────────┐
         │          │   Network    │
         │          │     (LAN)    │
         │          └──────────────┘
         │                 │
         │                 ▼
┌────────┼─────────────────┼──────────────────────────────────────┐
│        │                 │ TCP                                  │
│        │                 │ UDP                                  │
│  ┌────────────┐   ┌──────────────┐   ┌────────────────────┐   │
│  │  Server    │   │   Session    │   │   Stream Relay/    │   │
│  │ Networking │◄─►│   Manager    │◄─►│      Mixer         │   │
│  └────────────┘   └──────────────┘   └────────────────────┘   │
│                        Server Application                       │
└─────────────────────────────────────────────────────────────────┘
```

## Component Architecture

### Client Components

#### 1. GUI Layer (`gui/`)

**LoginWindow** (`gui/login.py`)
- User authentication interface
- Sign in / Sign up tabs
- Profile validation
- Signals: `login_successful(username)`

**HostJoinWindow** (`gui/hostjoin.py`)
- Session creation and joining interface
- Session ID generation
- Server address input
- Signals: `host_session(session_id, username)`, `join_session(...)`

**MainAppWindow** (`gui/mainapp.py`)
- Primary communication interface
- Features:
  - User list with checkboxes (multicast selection)
  - Chat panel with history
  - File transfer panel
  - Audio/Video controls
  - Screen share display
  - Communication mode selector
- Signals for all user actions

#### 2. Client Networking (`client/client.py`)

**LANClient** (QObject)
- Manages TCP control channel
- Handles UDP media streaming
- Thread-safe Qt signals for GUI updates
- Responsibilities:
  - Connect to server
  - Authenticate
  - Send/receive control messages
  - Send UDP media packets
  - Maintain heartbeat

**MediaCaptureStub**
- Placeholder for audio/video capture
- TODO: Implement real capture with opencv-python, sounddevice

### Server Components

#### 1. Server Networking (`server/server.py`)

**LANServer**
- Multi-client TCP server
- UDP media relay
- Responsibilities:
  - Accept client connections
  - Authenticate users
  - Route messages (unicast/multicast/broadcast)
  - Relay UDP streams
  - Monitor client heartbeats
  - Manage session state

**ClientConnection**
- Represents a connected client
- Stores socket, address, username, UDP address
- Tracks last heartbeat time

### Utility Components (`utils/`)

#### logger.py
- Centralized logging to console and file
- Daily log rotation
- Debug/Info/Warning/Error levels

#### config.py
- Configuration management
- Default network ports, buffer sizes
- Media settings (resolution, FPS, sample rate)
- Profile file paths

#### network_proto.py
- Message type definitions (enum)
- Packet structures (dataclasses)
- Serialization/deserialization functions
- UDP packet framing

#### profiles.py
- User profile management
- SHA-256 password hashing
- JSON storage in profiles.json

## Threading Model

### Client Threads

```
Main Thread (Qt Event Loop)
├── GUI Event Handling
└── Signal/Slot Processing

Background Threads:
├── TCP Receive Thread
│   └── Processes incoming control messages
├── UDP Receive Thread
│   └── Processes incoming media packets
└── Heartbeat Thread
    └── Sends periodic ping messages
```

### Server Threads

```
Main Thread
└── Server Control Loop

Background Threads:
├── TCP Accept Thread
│   └── Accepts new client connections
├── TCP Client Handler Threads (one per client)
│   └── Processes client control messages
├── UDP Receive Thread
│   └── Receives and relays media packets
└── Heartbeat Monitor Thread
    └── Checks client liveness
```

## Communication Flow

### 1. Session Setup

```
Host:
1. User clicks "Host Session"
2. Generate session ID
3. Start LANServer (TCP port 5555, UDP port 5556)
4. Create LANClient, connect to 127.0.0.1
5. Authenticate
6. Display MainAppWindow

Client:
1. User clicks "Join Session"
2. Enter session ID and server IP
3. Create LANClient, connect to server IP
4. Authenticate with session ID
5. Receive user list
6. Display MainAppWindow
```

### 2. Authentication Sequence

```
Client                      Server
  │                           │
  ├──AUTH_REQUEST────────────►│
  │  {username, session_id}   │
  │                           ├─ Validate session_id
  │                           ├─ Check username available
  │                           ├─ Add to clients dict
  │                           │
  │◄────AUTH_RESPONSE─────────┤
  │  {success: true}          │
  │                           │
  │◄────USER_LIST─────────────┤
  │  {users: [...]}           │
  │                           │
  ├──────USER_JOINED────────►│─ Broadcast to others
  │  (server broadcasts)      │
```

### 3. Chat Message Flow

```
Sender                     Server                   Receivers
  │                           │                          │
  ├──CHAT_MESSAGE────────────►│                          │
  │  {from, mode, to, text}   ├─ Route by mode:         │
  │                           │  - broadcast: all        │
  │                           │  - multicast: to_users   │
  │                           │  - unicast: one user     │
  │                           │                          │
  │                           ├──CHAT_MESSAGE───────────►│
  │                           │  {from, text}            │
  │                           │                          │
  │                           ├──CHAT_MESSAGE───────────►│
  │                           │  {from, text}            │
```

### 4. UDP Media Streaming

```
Client A                    Server                   Client B
  │                           │                          │
  │──UDP Audio Packet────────►│                          │
  │  [header + payload]       ├─ Parse packet           │
  │                           ├─ Relay to all others    │
  │                           │                          │
  │                           ├──UDP Audio Packet───────►│
  │                           │  [header + payload]      │
  │                           │                          │
  │◄─UDP Video Packet─────────┤◄───UDP Video Packet─────┤
  │  [header + payload]       │    [header + payload]   │
```

## Network Protocol Details

See [network_protocol.md](network_protocol.md) for complete protocol specification.

### TCP Control Channel

- **Transport**: TCP
- **Port**: 5555 (default)
- **Framing**: 4-byte length prefix + JSON payload
- **Message Types**: auth_request, chat_message, file_offer, user_joined, etc.

### UDP Media Channel

- **Transport**: UDP
- **Port**: 5556 (default)
- **Packet Structure**: Binary header (20 bytes) + payload
  - stream_id (4 bytes)
  - seq_num (4 bytes)
  - timestamp (8 bytes, microseconds)
  - payload_size (4 bytes)
  - payload (variable)

## Data Flow

### Profiles (profiles.json)
```
Load on startup → ProfileManager → Authenticate user → Store last_login
```

### Configuration (config.json)
```
Load defaults → Override from file → Used by all components
```

### Logs (logs/)
```
All components → Logger → Console + File (daily rotation)
```

### Temporary Files (temp_files/)
```
File uploads → Store with unique ID → Broadcast file_offer → Download on request
```

## Security Considerations

### Current Implementation
- ✅ SHA-256 password hashing
- ✅ Session ID validation
- ✅ Local profile storage

### TODO for Production
- ⏳ TLS/SSL for TCP control channel
- ⏳ DTLS for UDP media streams
- ⏳ End-to-end encryption for messages
- ⏳ Certificate-based authentication
- ⏳ Rate limiting and DoS protection
- ⏳ Input validation and sanitization

## Scalability

### Current Limitations
- Single server instance (no horizontal scaling)
- No load balancing
- In-memory session state (lost on restart)
- Broadcast UDP relay (bandwidth grows with users)

### Optimizations for Large Sessions
- Audio mixing on server (reduce bandwidth)
- Selective video forwarding
- Adaptive bitrate streaming
- P2P fallback for direct connections
- Session recording and playback

## Error Handling

### Network Errors
- Connection timeout: Retry with exponential backoff
- Disconnection: Emit signal to GUI, show reconnect dialog
- Heartbeat timeout: Remove client from session

### GUI Errors
- Validation errors: Show message box to user
- File errors: Log and notify user

### Server Errors
- Port binding error: Log and exit gracefully
- Client error: Log, close socket, notify other clients

## Testing Strategy

### Unit Tests
- Profile manager (authentication, CRUD)
- Network protocol (serialization/deserialization)
- Configuration loading

### Integration Tests
- Client-server connection
- Message routing (unicast/multicast/broadcast)
- File transfer handshake
- Heartbeat mechanism

### Manual Tests
- Multi-user chat
- File upload/download
- User join/leave
- Connection loss recovery
- Different network conditions

## Performance Considerations

### Latency
- TCP: Nagle's algorithm disabled for low latency
- UDP: No acknowledgment, minimal overhead
- Target: <100ms for chat, <50ms for media

### Throughput
- TCP buffer: 8192 bytes
- UDP packet: 1400 bytes (avoid fragmentation)
- File transfer: 64KB chunks

### Memory
- Client: ~50MB base + media buffers
- Server: ~100MB base + per-client overhead

## Deployment

### Development
```bash
python app.py
```

### Production Executable
```bash
pyinstaller --onefile --windowed app.py
./dist/app  # or app.exe on Windows
```

### Network Setup
1. Host determines local IP: `ipconfig` / `ifconfig`
2. Open firewall ports: 5555 (TCP), 5556 (UDP)
3. Share session ID and IP with participants
4. Participants join using host IP

## Future Enhancements

- [ ] Real audio/video codec integration
- [ ] Screen sharing with compression
- [ ] File transfer resume support
- [ ] Session persistence and reconnection
- [ ] Mobile client (PySide6 Mobile)
- [ ] Web client (WebSocket bridge)
- [ ] Admin controls (mute users, kick, etc.)
- [ ] Recording and playback
- [ ] Statistics and monitoring dashboard
