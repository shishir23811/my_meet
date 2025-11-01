# LAN Communication Application

A robust, standalone, LAN-only multi-user communication application built with PySide6 and Python sockets. Provides video conferencing, audio conferencing, screen sharing, group chat, and file sharing capabilities without requiring internet connectivity.

## Features

- **🔐 User Authentication**: Local profile management with sign in/sign up
- **👥 Multi-user Sessions**: Host or join sessions with unique session IDs
- **💬 Group Chat**: Real-time text messaging with broadcast/multicast/unicast modes
- **📁 File Sharing**: Upload and download files between users
- **🎤 Audio Conferencing**: UDP-based audio streaming (stub provided)
- **📹 Video Conferencing**: UDP-based video streaming (stub provided)
- **🖥️ Screen Sharing**: TCP-based screen frame transmission (stub provided)
- **📡 Communication Modes**:
  - **Broadcast**: Send to all users
  - **Multicast**: Send to selected users
  - **Unicast**: Send to one specific user

## Project Structure

```
/
├── app.py                 # Main application launcher
├── profiles.json          # Local user profiles
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── ARCHITECTURE.md       # Architecture documentation
├── network_protocol.md   # Network protocol specification
├── client/               # Client networking components
│   ├── __init__.py
│   └── client.py         # TCP/UDP client implementation
├── server/               # Server networking components
│   ├── __init__.py
│   └── server.py         # TCP/UDP server implementation
├── gui/                  # PySide6 GUI windows
│   ├── __init__.py
│   ├── login.py          # Login/signup window
│   ├── hostjoin.py       # Host/join session window
│   └── mainapp.py        # Main communication window
└── utils/                # Utilities and helpers
    ├── __init__.py
    ├── logger.py         # Logging configuration
    ├── config.py         # Configuration management
    ├── network_proto.py  # Network protocol definitions
    └── profiles.py       # Profile management
```

## Installation

### Prerequisites

- Python 3.11 or higher
- pip (Python package manager)

### Setup

1. **Clone or download this repository**

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Running the Application

**Start the application**:
```bash
python app.py
```

### Workflow

1. **Login/Sign Up**:
   - Create a new account or sign in with existing credentials
   - Sample users in `profiles.json`:
     - Username: `alice`, Password: `hello` (hash: `2cf24dba...`)
     - Username: `bob`, Password: `world` (hash: `81b637d8...`)

2. **Host a Session**:
   - Click "Host a Session"
   - Generate a session ID
   - Share the session ID and your IP address with others
   - Click "Start Hosting"

3. **Join a Session**:
   - Click "Join a Session"
   - Enter the session ID provided by the host
   - Enter the host's IP address (use `127.0.0.1` for localhost testing)
   - Click "Join Session"

4. **Communicate**:
   - **Chat**: Type messages and select communication mode
   - **Files**: Upload files and download shared files
   - **Audio/Video**: Start/stop audio and video streams
   - **Screen Share**: Share your screen with others

### Testing Locally

To test with multiple users on the same machine:

1. **Terminal 1** - Start as host:
   ```bash
   python app.py
   # Login as 'alice'
   # Host session with ID 'TEST123'
   ```

2. **Terminal 2** - Join as client:
   ```bash
   python app.py
   # Login as 'bob'
   # Join session 'TEST123' at '127.0.0.1'
   ```

3. **Send messages** between alice and bob

### Network Configuration

Default ports (configurable in `utils/config.py`):
- **TCP**: 5555 (control channel for chat, files, commands)
- **UDP**: 5556 (media streams for audio/video)

## Configuration

### User Profiles

Profiles are stored in `profiles.json` at the project root:

```json
{
  "users": {
    "username": {
      "username": "username",
      "display_name": "Display Name",
      "password_hash": "sha256_hash_of_password",
      "created_at": "2025-01-15T10:00:00",
      "last_login": "2025-01-20T14:30:00"
    }
  }
}
```

### Network Settings

Edit `utils/config.py` to change:
- TCP/UDP ports
- Buffer sizes
- Video/audio settings
- File transfer limits

## Building Executables

Create standalone executables using PyInstaller:

```bash
# Windows
pyinstaller --onefile --windowed --name="LAN Communicator" app.py

# Linux
pyinstaller --onefile --windowed --name="LAN Communicator" app.py
```

The executable will be in the `dist/` directory.

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed architecture documentation including:
- System design
- Component interactions
- Sequence diagrams
- Threading model

## Network Protocol

See [network_protocol.md](network_protocol.md) for detailed protocol specification including:
- TCP control message formats
- UDP packet structure
- Message flow diagrams
- Authentication handshake

## Development

### Adding New Features

1. **Media Codecs**: Replace stubs in `client/client.py` (MediaCaptureStub) with real implementations:
   - Audio: Use `sounddevice` or `pyaudio` for capture, Opus for encoding
   - Video: Use `opencv-python` for capture, H.264 for encoding

2. **File Transfer**: Implement chunked file transfer in server/client

3. **Screen Sharing**: Implement screen capture and frame transmission

### Logging

Logs are stored in `logs/app_YYYYMMDD.log`. Configure log level in `utils/logger.py`.

### Testing

Run the server standalone:
```bash
python server/server.py SESSION_ID HOST_USERNAME
```

## Troubleshooting

### Connection Issues

- **Firewall**: Ensure ports 5555 (TCP) and 5556 (UDP) are open
- **IP Address**: Use `ipconfig` (Windows) or `ifconfig` (Linux) to find your local IP
- **Same Machine**: Use `127.0.0.1` or `localhost`

### Authentication Failures

- Check `profiles.json` exists and is valid JSON
- Passwords are hashed with SHA-256
- Create new users via Sign Up tab

### Port Already in Use

- Change ports in `utils/config.py`
- Kill existing processes using the ports

## License

This is a demonstration/educational project. Use at your own risk.

## Credits

Developed as a LAN-only communication system using:
- PySide6 for GUI
- Python sockets for networking
- Threading for concurrency

## Roadmap

Future enhancements (marked as TODO in code):
- ✅ Basic chat and user management
- ⏳ Real audio/video capture and encoding
- ⏳ Audio mixing on server side
- ⏳ Bandwidth management
- ⏳ End-to-end encryption
- ⏳ Persistent file storage
- ⏳ Session recording
- ⏳ Mobile client support

## Support

For issues or questions:
1. Check logs in `logs/` directory
2. Review ARCHITECTURE.md and network_protocol.md
3. Inspect code comments for TODO items and implementation notes
