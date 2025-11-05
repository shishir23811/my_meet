# LAN Communicator

A comprehensive real-time communication application for local area networks, featuring video calls, voice chat, screen sharing, and file transfer capabilities.

## Installation & Setup

### 1. Clone the Repository
```bash
git clone <repository-url>
cd my_meet
```

### 2. Create Virtual Environment (Recommended)
```bash
# Windows
python -m venv venv
venv\\Scripts\\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Firewall (Windows)
For Windows users, run the firewall setup script as administrator:
```bash
# PowerShell (as Administrator)
.\\setup_firewall.ps1

# Or Command Prompt (as Administrator)
setup_firewall.bat
```

## 🎮 How to Run

### Starting the Application
```bash
python app.py
```

### Setting Up a Session

#### Option 1: Host a Session
1. **Launch the application** and enter your username
2. **Click "Host a Session"**
3. **Generate a Session ID** using the "Generate Session ID" button
4. **Share the session information** with other participants:
   - Session ID (8-character code)
   - Your IP address
   - TCP and UDP ports (if not using defaults)
5. **Click "Start Hosting"** to begin the session
6. **Wait for participants** to join using your session information

#### Option 2: Join a Session
1. **Launch the application** and enter your username
2. **Click "Join a Session"**
3. **Enter the session details** provided by the host:
   - Session ID
   - Host's IP address
   - TCP and UDP ports (if not defaults)
4. **Click "Join Session"** to connect
5. **Start communicating** once connected

### Using the Features

#### Video & Audio
- **Toggle microphone**: Click the microphone button in the bottom control bar
- **Toggle camera**: Click the camera button in the bottom control bar
- **Speaking indicators**: Green borders appear around users who are speaking
- **Audio controls**: Mute/unmute yourself or adjust audio settings

#### Screen Sharing
- **Start screen sharing**: Click the screen share button in the control bar
- **Stop screen sharing**: Click the screen share button again to stop
- **View shared screens**: Shared screens appear in the main video grid

#### Chat
- **Open chat**: Click the chat button (💬) in the bottom right
- **Send messages**: Type in the chat input and press Enter or click "Send"
- **View history**: Scroll through the chat history in the sidebar

#### File Transfer
- **Share files**: 
  1. Click the chat button to open the sidebar
  2. Switch to the "Files" tab
  3. Click "Browse Files..." to select a file
  4. Click "Share File" to upload
- **Download files**: 
  1. View available files in the Files tab
  2. Double-click a file or select and click "Download Selected"
  3. Choose download location

#### User Management
- **View participants**: Click the users button (👥) to see all participants
- **User status**: See who's online and their current media status
- **Leave session**: Click "Leave Session" or close the application

## 🔧 Configuration

### Network Settings
The application uses the following default ports:
- **TCP Port**: 54321 (for control messages)
- **UDP Port**: 54322 (for media streams)

These can be configured in `config.json`:
```json
{
  "network": {
    "tcp_port": 54321,
    "udp_port": 54322,
    "buffer_size": 65536
  },
  "media": {
    "video_quality": "medium",
    "audio_sample_rate": 44100
  }
}
```

### User Profiles
User profiles are stored in `profiles.json` and include:
- Username preferences
- Last used settings
- Session history (optional)

## Features

### Video & Audio Communication
- **High-quality video calls** with real-time video streaming
- **Crystal-clear voice chat** with speaking indicators
- **Microphone and camera controls** with mute/unmute functionality
- **Speaking detection** with visual indicators (green borders)
- **Audio strength monitoring** for optimal voice quality

### Screen Sharing
- **Full desktop screen sharing** for presentations and collaboration
- **Real-time screen capture** with optimized performance
- **Easy start/stop controls** for screen sharing sessions

### Real-time Chat
- **Instant messaging** with all participants
- **Message history** during the session
- **User-friendly chat interface** with sidebar design

### File Transfer
- **Secure file sharing** between participants
- **Drag-and-drop file upload** support
- **File download** with progress tracking
- **Multiple file format support**

### User Management
- **Multi-user sessions** with up to multiple participants
- **User presence indicators** showing who's online
- **Dynamic user grid** that adapts to the number of participants
- **User authentication** with session-based access

### Advanced Features
- **Session hosting and joining** with unique session IDs
- **Automatic network discovery** and configuration
- **Reconnection handling** for network interruptions
- **Error management** with user-friendly notifications
- **Responsive UI** that adapts to different screen sizes

## Technical Implementation

### Architecture
- **Client-Server Architecture**: Centralized server for session management
- **Multi-threaded Design**: Separate threads for GUI, networking, and media processing
- **Qt-based GUI**: Modern, responsive user interface using PySide6
- **UDP Media Streaming**: Low-latency audio/video transmission
- **TCP Control Channel**: Reliable messaging for chat and file metadata

### Core Components

#### 1. **Application Layer** (`app.py`)
- Main application controller managing window transitions
- Integration between GUI and networking components
- Session lifecycle management

#### 2. **GUI Components** (`gui/`)
- **Login Window**: User authentication and profile management
- **Host/Join Window**: Session creation and connection interface
- **Main App Window**: Primary communication interface with all features
- **Responsive Design**: Adaptive layouts for different screen sizes

#### 3. **Client Networking** (`client/`)
- **LANClient**: Main client networking class
- **MediaCaptureManager**: Audio/video capture and processing
- **FileTransferManager**: File upload/download handling
- **Reconnection Logic**: Automatic reconnection on network issues

#### 4. **Server Networking** (`server/`)
- **LANServer**: Multi-client server for session management
- **Message Routing**: Efficient message distribution to clients
- **Media Relay**: UDP stream forwarding between participants
- **Session Management**: User presence and session state

#### 5. **Utilities** (`utils/`)
- **Network Protocol**: Message serialization and packet handling
- **Configuration Management**: Settings and preferences
- **Logging System**: Comprehensive logging for debugging
- **Error Management**: Centralized error handling and reporting

### Media Processing
- **OpenCV**: Video capture and frame processing
- **SoundDevice**: Audio capture and playback
- **MSS**: Screen capture for screen sharing
- **NumPy**: Audio processing and analysis

### Network Protocol
- **TCP Control Channel**: JSON-based messaging for reliability
- **UDP Media Streams**: Binary packet streaming for low latency
- **Message Types**: Authentication, chat, file transfer, media control
- **Stream Identification**: Unique stream IDs for media routing

## Requirements

### System Requirements
- **Operating System**: Windows 10/11
- **Python**: 3.8 or higher
- **Memory**: 4GB RAM minimum, 8GB recommended
- **Network**: Local Area Network (LAN) connectivity
- **Hardware**: Webcam and microphone for full functionality

### Python Dependencies
```
PySide6>=6.5.0          # GUI framework
opencv-python>=4.8.0    # Video processing
numpy>=1.24.0           # Numerical operations
sounddevice>=0.4.6      # Audio capture/playback
mss>=9.0.0              # Screen capture
pyinstaller>=5.13.0     # Executable creation (optional)
```

## Troubleshooting

### Common Issues

#### Connection Problems
- **Cannot connect to host**: 
  - Verify the IP address and ports are correct
  - Check firewall settings on both host and client
  - Ensure both devices are on the same network

#### Audio/Video Issues
- **No audio/video**: 
  - Check device permissions for camera and microphone
  - Verify devices are not being used by other applications
  - Restart the application if devices were connected after launch

#### Performance Issues
- **Lag or poor quality**: 
  - Close unnecessary applications
  - Check network bandwidth
  - Reduce video quality in settings

#### Firewall Issues
- **Windows Firewall blocking**: Run the firewall setup scripts as administrator
- **Third-party firewalls**: Add exceptions for the application and ports 54321-54322

### Logs and Debugging
- **Log files**: Check the `logs/` directory for detailed error information
- **Verbose logging**: Enable debug logging in the configuration
- **Network diagnostics**: Use built-in connection testing features

## Development

### Project Structure
```
my_meet/
├── app.py                 # Main application entry point
├── requirements.txt       # Python dependencies
├── config.json           # Application configuration
├── profiles.json         # User profiles
├── gui/                  # User interface components
│   ├── login.py          # Login window
│   ├── hostjoin.py       # Host/Join session window
│   ├── mainapp.py        # Main application window
│   └── icons.py          # UI icons and graphics
├── client/               # Client networking
│   ├── client.py         # Main client class
│   └── media_capture.py  # Media capture management
├── server/               # Server networking
│   └── server.py         # Multi-client server
├── utils/                # Utilities and helpers
│   ├── config.py         # Configuration management
│   ├── logger.py         # Logging system
│   ├── error_manager.py  # Error handling
│   ├── network_proto.py  # Network protocol
│   └── file_transfer.py  # File transfer utilities
└── logs/                 # Application logs
```

### Building Executable
To create a standalone executable:
```bash
pip install pyinstaller
pyinstaller --onefile --windowed app.py
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Support

For issues, questions, or contributions:
1. Check the logs in the `logs/` directory for error details
2. Review this README for troubleshooting steps
3. Open an issue on the project repository
4. Provide detailed information about your system and the issue

---

**LAN Communicator** - Bringing people together through seamless local network communication!