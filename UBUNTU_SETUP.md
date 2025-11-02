# Ubuntu Setup Guide

## ✅ **Yes, the LAN Communicator works on Ubuntu!**

The application is cross-platform and fully compatible with Ubuntu Linux. Here's how to set it up:

### 📋 **System Requirements**

- **Ubuntu 20.04 LTS or newer**
- **Python 3.8 or newer**
- **Audio system** (PulseAudio/ALSA)
- **Camera** (optional, for video features)
- **Network connection**

### 🛠️ **Installation Steps**

#### **1. Install System Dependencies**

```bash
# Update package list
sudo apt update

# Install Python and pip
sudo apt install python3 python3-pip python3-venv

# Install system dependencies for media libraries
sudo apt install python3-dev portaudio19-dev libasound2-dev

# Install Qt6 dependencies for PySide6
sudo apt install qt6-base-dev qt6-multimedia-dev

# Install camera and video dependencies
sudo apt install libopencv-dev python3-opencv

# Install audio dependencies
sudo apt install pulseaudio pulseaudio-utils alsa-utils

# Install screen capture dependencies
sudo apt install libxcb-xinerama0 libxcb-randr0 libxcb-xtest0 libxcb-xfixes0
```

#### **2. Clone and Setup Project**

```bash
# Clone the project (or copy files)
cd ~/Documents
# (Copy your project files here)

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

#### **3. Setup Firewall (HOST ONLY)**

```bash
# Allow incoming connections on required ports
sudo ufw allow 5555/tcp comment "LAN Communicator TCP"
sudo ufw allow 5556/udp comment "LAN Communicator UDP"

# Enable firewall if not already enabled
sudo ufw enable

# Check firewall status
sudo ufw status
```

#### **4. Test Audio/Video Permissions**

```bash
# Test audio devices
python3 -c "import sounddevice; print(sounddevice.query_devices())"

# Test camera access
python3 -c "import cv2; cap = cv2.VideoCapture(0); print('Camera:', cap.isOpened()); cap.release()"

# Test screen capture
python3 -c "import mss; print('Screen capture available:', len(mss.mss().monitors) > 1)"
```

### 🚀 **Running the Application**

```bash
# Activate virtual environment
source venv/bin/activate

# Run the application
python3 app.py
```

### 🔧 **Ubuntu-Specific Configuration**

#### **Audio Configuration**

If you have audio issues:

```bash
# Check PulseAudio status
pulseaudio --check -v

# Restart PulseAudio if needed
pulseaudio -k
pulseaudio --start

# List audio devices
pactl list short sources  # Input devices
pactl list short sinks    # Output devices
```

#### **Camera Permissions**

```bash
# Add user to video group for camera access
sudo usermod -a -G video $USER

# Check camera devices
ls -la /dev/video*

# Test camera with simple command
ffplay /dev/video0  # Press 'q' to quit
```

#### **Network Configuration**

```bash
# Find your IP address
ip addr show | grep inet

# Test network connectivity
ping <other_computer_ip>

# Check if ports are open (on host)
sudo netstat -tlnp | grep :5555
sudo netstat -ulnp | grep :5556
```

### 🐧 **Ubuntu Firewall Setup Script**

Create `setup_firewall_ubuntu.sh`:

```bash
#!/bin/bash
echo "============================================================"
echo "LAN Communicator - Ubuntu Firewall Setup"
echo "============================================================"
echo
echo "Setting up firewall rules for LAN Communicator..."
echo

# Allow TCP port 5555
sudo ufw allow 5555/tcp comment "LAN Communicator TCP"
echo "✅ TCP port 5555 allowed"

# Allow UDP port 5556
sudo ufw allow 5556/udp comment "LAN Communicator UDP"
echo "✅ UDP port 5556 allowed"

# Enable firewall
sudo ufw --force enable
echo "✅ Firewall enabled"

echo
echo "============================================================"
echo "Firewall setup complete!"
echo "============================================================"
echo
echo "Current firewall status:"
sudo ufw status
echo
echo "You can now host sessions and others should be able to connect."
```

Make it executable:
```bash
chmod +x setup_firewall_ubuntu.sh
./setup_firewall_ubuntu.sh
```

### 🔍 **Troubleshooting Ubuntu Issues**

#### **Audio Problems**

```bash
# Check audio system
systemctl --user status pulseaudio

# Restart audio system
systemctl --user restart pulseaudio

# Test microphone
arecord -l  # List recording devices
arecord -d 5 test.wav  # Record 5 seconds
aplay test.wav  # Play back
```

#### **Camera Problems**

```bash
# Check camera permissions
groups $USER  # Should include 'video'

# Test camera access
v4l2-ctl --list-devices

# Install camera test tool
sudo apt install cheese
cheese  # GUI camera test
```

#### **Network Problems**

```bash
# Check firewall rules
sudo ufw status verbose

# Test port connectivity
nc -zv <host_ip> 5555  # Test TCP
nc -zvu <host_ip> 5556  # Test UDP

# Monitor network traffic
sudo tcpdump -i any port 5555
```

#### **GUI Problems**

```bash
# Install additional Qt dependencies if needed
sudo apt install qt6-wayland

# For X11 systems
export QT_QPA_PLATFORM=xcb

# For Wayland systems
export QT_QPA_PLATFORM=wayland
```

### 📊 **Performance Optimization**

```bash
# Install hardware acceleration for video
sudo apt install intel-media-va-driver-non-free  # Intel
sudo apt install mesa-va-drivers  # AMD

# Optimize audio latency
echo "default-sample-rate = 44100" >> ~/.pulse/daemon.conf
echo "default-fragment-size-msec = 20" >> ~/.pulse/daemon.conf
```

### 🎯 **Cross-Platform Testing**

The application works seamlessly between:
- **Ubuntu ↔ Windows**
- **Ubuntu ↔ Ubuntu**
- **Ubuntu ↔ macOS**

Just ensure:
1. Both systems have firewall rules configured
2. Both systems are on the same network
3. Correct IP addresses are used

### 📱 **Ubuntu Connection Test**

```bash
# Test connection to Windows host
python3 test_connection.py 192.168.1.100

# Test connection to Ubuntu host
python3 test_connection.py 192.168.1.101
```

### 🎉 **Ready to Use!**

After setup, the Ubuntu version has the same features as Windows:
- ✅ Audio capture and playback
- ✅ Video capture and streaming
- ✅ Screen sharing
- ✅ File transfer
- ✅ Chat messaging
- ✅ Cross-platform compatibility

The application will work exactly the same as on Windows, with full feature parity!