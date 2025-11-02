# Network Troubleshooting Guide

## 🔥 Connection Timeout Error (WinError 10060)

This error occurs when trying to connect from one computer to another over the network. Here's how to diagnose and fix it:

### 🔍 **Understanding the Error**

**Error**: `[WinError 10060] A connection attempt failed because the connected party did not properly respond after a period of time`

**What it means**: Your computer can't establish a connection to the host computer, usually due to:
1. **Firewall blocking the connection**
2. **Network configuration issues**
3. **Host not properly listening on the expected port**
4. **Different network segments**

### 🛠️ **Step-by-Step Solutions**

#### **Step 1: Verify Network Connectivity**

1. **Test basic connectivity**:
   ```bash
   ping 172.17.131.211
   ```
   - ✅ If successful: Network path exists
   - ❌ If failed: Network routing issue

2. **Run network diagnostics**:
   ```bash
   python network_diagnostics.py 172.17.131.211
   ```

#### **Step 2: Check Windows Firewall (CRITICAL)**

**On the HOST computer (172.17.131.211):**

1. **Open Windows Defender Firewall**:
   - Press `Win + R`, type `wf.msc`, press Enter

2. **Create Inbound Rules**:
   - Click "Inbound Rules" → "New Rule"
   - Select "Port" → Next
   - Select "TCP" → Specific local ports: `5555`
   - Select "Allow the connection" → Next
   - Check all profiles (Domain, Private, Public) → Next
   - Name: "LAN Communicator TCP" → Finish

3. **Repeat for UDP**:
   - Create another rule for UDP port `5556`
   - Name: "LAN Communicator UDP"

**Quick Firewall Test**:
```bash
# Temporarily disable firewall for testing (HOST computer)
# Run as Administrator in PowerShell:
Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled False

# Test connection, then re-enable:
Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled True
```

#### **Step 3: Verify Host is Running**

**On the HOST computer:**

1. **Check if server is listening**:
   ```bash
   netstat -an | findstr :5555
   ```
   - Should show: `TCP    0.0.0.0:5555    0.0.0.0:0    LISTENING`

2. **Check application logs**:
   - Look for "Server started successfully" messages
   - Verify no port binding errors

#### **Step 4: Network Configuration**

1. **Same Network Check**:
   - Both computers should be on same subnet
   - Example: Host `172.17.131.211`, Client should be `172.17.131.xxx`

2. **Router/Switch Issues**:
   - Some routers block inter-device communication
   - Check router settings for "AP Isolation" or "Client Isolation"
   - Disable if enabled

#### **Step 5: Alternative Connection Methods**

1. **Try Host's Other IP Addresses**:
   ```bash
   # On host computer, find all IP addresses:
   ipconfig /all
   ```
   - Try WiFi adapter IP
   - Try Ethernet adapter IP

2. **Use Computer Name**:
   - Instead of IP, try computer name
   - Example: `DESKTOP-ABC123` instead of `172.17.131.211`

### 🔧 **Advanced Troubleshooting**

#### **Port Testing Tools**

1. **Test specific port connectivity**:
   ```bash
   # On client computer:
   telnet 172.17.131.211 5555
   ```
   - If connects: Port is open
   - If fails: Port is blocked

2. **PowerShell port test**:
   ```powershell
   Test-NetConnection -ComputerName 172.17.131.211 -Port 5555
   ```

#### **Wireshark Analysis**

1. Install Wireshark on host computer
2. Capture traffic on port 5555
3. Look for connection attempts from client IP
4. Check if packets are reaching the host

### 🎯 **Quick Fix Checklist**

**On HOST computer:**
- [ ] Application is running and shows "Server started"
- [ ] Windows Firewall allows ports 5555 and 5556
- [ ] No other application is using these ports
- [ ] Computer is connected to network

**On CLIENT computer:**
- [ ] Can ping the host IP address
- [ ] Using correct IP address
- [ ] Session ID is correct
- [ ] Network diagnostics pass

**Network:**
- [ ] Both computers on same network
- [ ] Router not blocking inter-device communication
- [ ] No VPN interfering with local network

### 🚀 **Immediate Solutions to Try**

#### **Solution 1: Firewall Exception**
```bash
# Run as Administrator on HOST:
netsh advfirewall firewall add rule name="LAN Communicator TCP" dir=in action=allow protocol=TCP localport=5555
netsh advfirewall firewall add rule name="LAN Communicator UDP" dir=in action=allow protocol=UDP localport=5556
```

#### **Solution 2: Different Ports**
If default ports are blocked, modify `config.json` on both computers:
```json
{
  "network": {
    "tcp_port": 8080,
    "udp_port": 8081
  }
}
```

#### **Solution 3: Hotspot Method**
1. Host creates mobile hotspot
2. Client connects to hotspot
3. Use hotspot IP address (usually `192.168.137.1`)

### 📞 **Still Not Working?**

1. **Check antivirus software** - may block connections
2. **Try different network** - use mobile hotspot
3. **Restart both applications** - clear any stuck states
4. **Reboot both computers** - clear network stack
5. **Check Windows updates** - ensure network stack is current

### 🔍 **Diagnostic Commands Summary**

```bash
# On HOST computer:
ipconfig /all                          # Get all IP addresses
netstat -an | findstr :5555           # Check if server listening
netsh advfirewall show allprofiles    # Check firewall status

# On CLIENT computer:
ping 172.17.131.211                   # Test basic connectivity
telnet 172.17.131.211 5555           # Test port connectivity
python network_diagnostics.py 172.17.131.211  # Run our diagnostic tool
```