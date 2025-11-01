# Network Protocol Specification

## Overview

The LAN Communication Application uses a dual-channel approach:
- **TCP Control Channel**: Reliable, ordered delivery for control messages, chat, file metadata
- **UDP Media Channel**: Low-latency, unreliable delivery for real-time audio/video streams

## TCP Control Channel

### Connection

- **Protocol**: TCP
- **Default Port**: 5555
- **Encoding**: UTF-8
- **Framing**: Length-prefixed JSON messages

### Message Framing

All TCP messages use a 4-byte big-endian length prefix:

```
┌────────────────┬────────────────────────────────────┐
│  Length (4B)   │  JSON Payload (variable)          │
│  Big-endian    │  UTF-8 encoded                     │
└────────────────┴────────────────────────────────────┘
```

**Example**:
```
Length: 0x00000032 (50 bytes)
Payload: {"type":"chat_message","from_user":"alice"...}
```

### Message Types

All messages are JSON objects with a required `type` field and optional `timestamp` field.

#### 1. Authentication

**AUTH_REQUEST** (Client → Server)
```json
{
  "type": "auth_request",
  "username": "alice",
  "password_hash": "sha256_hash",
  "session_id": "ABC123"
}
```

**AUTH_RESPONSE** (Server → Client)
```json
{
  "type": "auth_response",
  "success": true,
  "username": "alice",
  "reason": "Authentication successful"
}
```

#### 2. Session Management

**JOIN_SESSION** (Client → Server)
```json
{
  "type": "join_session",
  "username": "alice",
  "session_id": "ABC123"
}
```

**LEAVE_SESSION** (Client → Server)
```json
{
  "type": "leave_session",
  "username": "alice"
}
```

**SESSION_UPDATE** (Server → Client)
```json
{
  "type": "session_update",
  "users": [
    {"username": "alice", "status": "active"},
    {"username": "bob", "status": "active"}
  ],
  "timestamp": 1706000000.123
}
```

#### 3. User Presence

**USER_JOINED** (Server → All Clients)
```json
{
  "type": "user_joined",
  "username": "charlie",
  "timestamp": 1706000000.123
}
```

**USER_LEFT** (Server → All Clients)
```json
{
  "type": "user_left",
  "username": "charlie",
  "timestamp": 1706000000.123
}
```

**USER_LIST** (Server → Client)
```json
{
  "type": "user_list",
  "users": ["alice", "bob", "charlie"],
  "timestamp": 1706000000.123
}
```

#### 4. Chat Messages

**CHAT_MESSAGE** (Client → Server → Clients)
```json
{
  "type": "chat_message",
  "from_user": "alice",
  "mode": "broadcast",
  "to_users": [],
  "payload": "Hello everyone!",
  "timestamp": 1706000000.123
}
```

**Mode values**:
- `"broadcast"`: Send to all users (to_users ignored)
- `"multicast"`: Send to selected users (to_users required)
- `"unicast"`: Send to single user (to_users[0] required)

#### 5. File Transfer

**FILE_OFFER** (Client → Server → Clients)
```json
{
  "type": "file_offer",
  "from_user": "alice",
  "file_id": "uuid-1234-5678",
  "filename": "document.pdf",
  "file_size": 1048576,
  "mode": "broadcast",
  "to_users": [],
  "timestamp": 1706000000.123
}
```

**FILE_REQUEST** (Client → Server → Owner)
```json
{
  "type": "file_request",
  "from_user": "bob",
  "to_user": "alice",
  "file_id": "uuid-1234-5678",
  "timestamp": 1706000000.123
}
```

**FILE_CHUNK** (Client → Server → Recipient)
```json
{
  "type": "file_chunk",
  "file_id": "uuid-1234-5678",
  "chunk_index": 0,
  "total_chunks": 16,
  "data": "base64_encoded_chunk",
  "timestamp": 1706000000.123
}
```

**FILE_COMPLETE** (Client → Server → Recipient)
```json
{
  "type": "file_complete",
  "file_id": "uuid-1234-5678",
  "timestamp": 1706000000.123
}
```

**FILE_LIST** (Server → Client)
```json
{
  "type": "file_list",
  "files": [
    {
      "file_id": "uuid-1234",
      "filename": "doc.pdf",
      "size": 1048576,
      "owner": "alice"
    }
  ],
  "timestamp": 1706000000.123
}
```

#### 6. Media Control

**MEDIA_START** (Client → Server → Clients)
```json
{
  "type": "media_start",
  "username": "alice",
  "media_type": "audio",
  "stream_id": 12345,
  "timestamp": 1706000000.123
}
```

**MEDIA_STOP** (Client → Server → Clients)
```json
{
  "type": "media_stop",
  "username": "alice",
  "media_type": "audio",
  "stream_id": 12345,
  "timestamp": 1706000000.123
}
```

**SCREEN_SHARE_START** / **SCREEN_SHARE_STOP** (similar)

**SCREEN_FRAME** (Client → Server → Clients)
```json
{
  "type": "screen_frame",
  "from_user": "alice",
  "frame_data": "base64_encoded_image",
  "width": 1920,
  "height": 1080,
  "timestamp": 1706000000.123
}
```

#### 7. Heartbeat

**PING** (Client → Server)
```json
{
  "type": "ping",
  "username": "alice",
  "timestamp": 1706000000.123
}
```

**PONG** (Server → Client)
```json
{
  "type": "pong",
  "timestamp": 1706000000.123
}
```

#### 8. Error Handling

**ERROR** (Server → Client)
```json
{
  "type": "error",
  "error_code": "INVALID_SESSION",
  "message": "Session ID does not exist",
  "timestamp": 1706000000.123
}
```

## UDP Media Channel

### Connection

- **Protocol**: UDP
- **Default Port**: 5556
- **Encoding**: Binary
- **Reliability**: Best-effort (no retransmission)

### Packet Structure

UDP packets use a fixed 20-byte binary header followed by payload:

```
┌────────────┬────────────┬───────────────┬──────────────┬─────────────┐
│ Stream ID  │  Seq Num   │  Timestamp    │ Payload Size │   Payload   │
│  (4 bytes) │ (4 bytes)  │  (8 bytes)    │  (4 bytes)   │  (variable) │
│ Big-endian │ Big-endian │  Big-endian   │  Big-endian  │   Binary    │
└────────────┴────────────┴───────────────┴──────────────┴─────────────┘
      0            4             8              16            20        →
```

### Header Fields

**stream_id** (uint32):
- Unique identifier for the stream
- Generated from hash of username + stream type
- Upper 28 bits: hash(username)
- Lower 4 bits: stream type (0x01=audio, 0x02=video)

**seq_num** (uint32):
- Sequence number for packet ordering
- Increments for each packet
- Wraps around at 2^32

**timestamp** (uint64):
- Capture timestamp in microseconds since Unix epoch
- Used for synchronization and jitter calculation

**payload_size** (uint32):
- Size of payload in bytes
- Must match actual payload length

**payload** (bytes):
- Encoded media data
- Format depends on codec:
  - Audio: Opus/AAC frames
  - Video: H.264/VP8 frames

### Stream Types

```
0x01 - Audio stream
0x02 - Video stream
0x03-0xFF - Reserved for future use
```

### Packet Size

- **Maximum**: 1400 bytes (including header)
- **Recommended**: ≤1200 bytes payload to avoid fragmentation
- **Audio**: Typically 20-60ms frames (~160-480 bytes)
- **Video**: Typically full MTU minus header (~1380 bytes)

## Communication Patterns

### 1. Broadcast Flow

```
Client A                     Server                      Clients B,C
   │                            │                             │
   ├─── TCP: CHAT_MESSAGE ─────►│                             │
   │    mode: "broadcast"       │                             │
   │                            ├─── TCP: CHAT_MESSAGE ──────►│
   │                            │    (to all except A)        │
   │                            ├─── TCP: CHAT_MESSAGE ──────►│
```

### 2. Multicast Flow

```
Client A                     Server                      Clients B,C,D
   │                            │                             │
   ├─── TCP: CHAT_MESSAGE ─────►│                             │
   │    mode: "multicast"       │                             │
   │    to_users: ["B","C"]     │                             │
   │                            ├─── TCP: CHAT_MESSAGE ──────►│ B
   │                            │                             │
   │                            ├─── TCP: CHAT_MESSAGE ──────►│ C
   │                            │                             │
   │                            │  (D not included)           X D
```

### 3. Unicast Flow

```
Client A                     Server                      Client B
   │                            │                             │
   ├─── TCP: CHAT_MESSAGE ─────►│                             │
   │    mode: "unicast"         │                             │
   │    to_users: ["B"]         │                             │
   │                            ├─── TCP: CHAT_MESSAGE ──────►│
```

### 4. UDP Media Relay

```
Client A                     Server                      Client B
   │                            │                             │
   ├─── UDP: Audio Packet ─────►│                             │
   │    [header + opus data]    ├─ Parse, identify sender    │
   │                            ├─ Relay to all others       │
   │                            │                             │
   │                            ├─── UDP: Audio Packet ──────►│
   │                            │    [header + opus data]     │
```

## Connection Lifecycle

### 1. Initial Connection

```
1. Client connects TCP socket to server
2. Client sends AUTH_REQUEST with session_id
3. Server validates session_id and username
4. Server sends AUTH_RESPONSE (success/failure)
5. Server sends USER_LIST with current users
6. Server broadcasts USER_JOINED to others
7. Client opens UDP socket for media
8. Ready for communication
```

### 2. Heartbeat Mechanism

```
Every 20 seconds:
  Client ──PING──► Server
  Server ──PONG──► Client

Server monitors:
  If no PING for 90 seconds → disconnect client
  Broadcast USER_LEFT to others
```

### 3. Graceful Disconnect

```
1. User clicks "Leave Session"
2. Client sends LEAVE_SESSION message
3. Client closes sockets
4. Server broadcasts USER_LEFT
5. Server removes client from session
```

## Error Handling

### TCP Errors

- **Connection refused**: Server not running or firewall blocking
- **Connection timeout**: Network issue or server overloaded
- **Socket closed**: Peer disconnected
- **Invalid JSON**: Malformed message → log and skip
- **Unknown message type**: Log and ignore

### UDP Errors

- **Packet loss**: Expected and handled by application
- **Out-of-order**: Use seq_num to reorder or discard
- **Invalid header**: Discard packet and log
- **Payload size mismatch**: Discard and log

## Security Considerations

### Current Implementation

- ✅ Session ID validation
- ✅ Username uniqueness check
- ✅ Basic input validation

### TODO for Production

- ⏳ TLS 1.3 for TCP channel
- ⏳ DTLS for UDP channel
- ⏳ Message authentication codes (MAC)
- ⏳ End-to-end encryption for chat/files
- ⏳ Rate limiting per client
- ⏳ Maximum message size enforcement
- ⏳ Replay attack prevention (nonce)

## Performance Optimization

### TCP

- Disable Nagle's algorithm: `socket.TCP_NODELAY`
- Set send/receive buffers: `SO_SNDBUF`, `SO_RCVBUF`
- Use non-blocking I/O with select/epoll

### UDP

- Large socket buffers to avoid packet loss
- Minimize packet size to avoid fragmentation
- Consider FEC (Forward Error Correction) for resilience

### Application Layer

- Audio mixing on server (N:1 instead of N:N bandwidth)
- Video simulcast (multiple quality levels)
- Adaptive bitrate based on network conditions
- Packet batching to reduce system calls

## Testing Tools

### Packet Inspection

```bash
# Capture TCP control channel
tcpdump -i any -A 'tcp port 5555'

# Capture UDP media channel
tcpdump -i any -X 'udp port 5556'
```

### Network Simulation

```bash
# Add latency
tc qdisc add dev eth0 root netem delay 50ms

# Add packet loss
tc qdisc add dev eth0 root netem loss 5%

# Add bandwidth limit
tc qdisc add dev eth0 root tbf rate 1mbit burst 32kbit latency 400ms
```

## Appendix: Example Session

```
Time  Direction  Type              Details
----  ---------  ----------------  ---------------------------
0.0s  C→S        TCP: Connect      Establish TCP connection
0.1s  C→S        AUTH_REQUEST      {username: "alice", session_id: "ABC"}
0.2s  S→C        AUTH_RESPONSE     {success: true}
0.2s  S→C        USER_LIST         {users: ["bob"]}
0.2s  S→B        USER_JOINED       {username: "alice"}
1.0s  C→S        CHAT_MESSAGE      {mode: "broadcast", text: "Hi!"}
1.0s  S→B        CHAT_MESSAGE      {from: "alice", text: "Hi!"}
2.0s  C→S        MEDIA_START       {media_type: "audio"}
2.1s  C→S        UDP: Audio        [stream_id=1234, seq=0, data]
2.1s  S→B        UDP: Audio        [stream_id=1234, seq=0, data]
2.2s  C→S        UDP: Audio        [stream_id=1234, seq=1, data]
...
20.0s C→S        PING              Heartbeat
20.0s S→C        PONG              Heartbeat response
...
60.0s C→S        LEAVE_SESSION     User leaving
60.0s S→B        USER_LEFT         {username: "alice"}
```
