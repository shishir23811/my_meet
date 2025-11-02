# Session ID Troubleshooting Guide

## ❌ "Invalid Session ID" Error

If you're getting an "Invalid Session ID" error when trying to join a session, here are the most common causes and solutions:

### 🔍 **Common Causes**

#### 1. **Incorrect Session ID Format**
- Session IDs must be exactly **8 characters long**
- Must contain only **numbers (0-9)** and **letters (A-F)**
- Case doesn't matter (automatically converted to uppercase)

**✅ Valid Examples:**
- `A1B2C3D4`
- `12345678`
- `ABCDEF01`
- `a1b2c3d4` (will be converted to `A1B2C3D4`)

**❌ Invalid Examples:**
- `A1B2C3D` (too short - 7 characters)
- `A1B2C3D45` (too long - 9 characters)
- `A1B2C3G4` (contains 'G' which is not a valid hex character)
- `A1B2-C3D4` (contains hyphen)

#### 2. **Typos in Session ID**
- Double-check each character
- The host should copy and share the exact session ID
- Use the "Copy Session Info" button on the host side

#### 3. **Session Not Started**
- The host must click "Start Hosting" before others can join
- Check that the host's session is actually running

#### 4. **Session Expired or Ended**
- The host may have closed the session
- Ask the host to start a new session

### 🛠️ **Troubleshooting Steps**

#### Step 1: Verify Session ID Format
1. Check that the session ID is exactly 8 characters
2. Ensure it only contains 0-9 and A-F
3. Try typing it in all uppercase

#### Step 2: Get Fresh Session Info
1. Ask the host to use "Copy Session Info" button
2. Paste the complete information
3. Extract just the session ID part

#### Step 3: Check Host Status
1. Confirm the host has started the session
2. Verify the host's application is still running
3. Ask the host to check for any error messages

#### Step 4: Test Connection
1. First test network connectivity:
   ```bash
   python network_diagnostics.py <host_ip>
   ```
2. If network is OK but session ID fails, the issue is likely with the session ID itself

### 📋 **For Hosts: How to Share Session Info**

1. **Generate Session ID**: Click "Generate Session ID"
2. **Copy Complete Info**: Click "Copy Session Info" (not just the session ID)
3. **Share with Participants**: Send the complete information that includes:
   - Session ID (8 characters)
   - Your IP address
   - Instructions

### 🔧 **Advanced Debugging**

If you're still having issues, check the application logs for detailed error messages:

1. **Host logs**: Look for server initialization messages
2. **Client logs**: Look for authentication request/response messages
3. **Session ID comparison**: The logs will show exactly what session IDs are being compared

### 📞 **Getting Help**

If none of these steps resolve the issue:

1. Check the application logs in the `logs/` directory
2. Run the network diagnostic tool
3. Verify both devices are on the same network
4. Try generating a new session ID and starting fresh

### 🎯 **Quick Checklist**

- [ ] Session ID is exactly 8 characters
- [ ] Session ID contains only 0-9 and A-F
- [ ] Host has started the session
- [ ] Network connectivity is working
- [ ] No typos in the session ID
- [ ] Session hasn't expired or been closed