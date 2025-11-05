# LAN Communication Troubleshooting Guide

## "Server Cannot Be Reached" Error

### Quick Diagnosis
Run the network test to check your setup:
```bash
python test_connection.py
```

### Common Causes and Solutions

#### 1. Host Not Ready
**Problem**: Participant tries to connect before host is fully ready.
**Solution**: 
- Host should wait for "Server started successfully" message
- Host should see their session info displayed before sharing
- Wait 2-3 seconds after hosting before participants join

#### 2. Wrong IP Address
**Problem**: Participant uses wrong IP address.
**Solution**:
- Host should share the IP shown in the application (e.g., `192.168.1.100`)
- Never use `127.0.0.1` or `localhost` for participants
- Both devices must be on the same WiFi network

#### 3. Session ID Mismatch
**Problem**: Participant enters wrong session ID.
**Solution**:
- Host should copy the complete session info using the "Copy Session Info" button
- Participant should paste exactly what host copied
- Session IDs are case-sensitive

#### 4. Firewall Blocking
**Problem**: Windows/Linux firewall blocks connections.
**Solution**:
- Windows: Allow ports 54321 and 54322 in Windows Defender Firewall
- Linux: `sudo ufw allow 54321/tcp && sudo ufw allow 54322/udp`
- Or temporarily disable firewall for testing

#### 5. Network Isolation
**Problem**: Router blocks device-to-device communication.
**Solution**:
- Check if both devices can ping each other
- Some public WiFi networks isolate devices
- Try using a mobile hotspot for testing

### Step-by-Step Testing

#### For Host:
1. Start the application
2. Login with username
3. Click "Host Session"
4. Wait for "Server started successfully" in logs
5. Copy the session info and share with participant
6. **Important**: Don't close or minimize the application

#### For Participant:
1. Make sure host has completed all steps above
2. Start the application on a different device
3. Login with a different username
4. Click "Join Session"
5. Enter the EXACT session info from host
6. Click "Join"

### Network Requirements
- Both devices on same WiFi network
- No VPN or proxy interfering
- Ports 54321 (TCP) and 54322 (UDP) available
- No firewall blocking connections

### Testing Commands

Check if you can reach the host:
```bash
# Replace 192.168.1.100 with actual host IP
python network_test.py 192.168.1.100
```

Test full connection:
```bash
python test_connection.py
```

### Still Not Working?

1. **Try different ports**: Edit `config.json` and change tcp_port/udp_port
2. **Check logs**: Look for error messages in the application console
3. **Test on same device**: Try hosting and joining from same computer (different usernames)
4. **Network diagnostics**: Use `ping`, `telnet`, or `netcat` to test basic connectivity

### Example Working Setup
```
Host Device (Windows):
- IP: 192.168.1.100
- Username: alice
- Session ID: ABC123
- Status: "Server started successfully"

Participant Device (Phone/Laptop):
- Same WiFi network
- Username: bob
- Connects to: 192.168.1.100:54321
- Session ID: ABC123
```