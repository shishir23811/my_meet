#!/usr/bin/env python3
"""
Comprehensive connection test for LAN Communication Application.
Tests both local and remote connectivity scenarios.
"""

import socket
import json
import struct
import time
import threading
import sys
from pathlib import Path

# Add project root to path to import modules
sys.path.append(str(Path(__file__).parent))

def get_local_ip():
    """Get the local IP address."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"

def test_port_binding(ip, port, protocol="TCP"):
    """Test if we can bind to a port (for hosting)."""
    try:
        if protocol.upper() == "TCP":
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        else:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((ip, port))
        sock.close()
        return True, "Can bind"
    except OSError as e:
        return False, str(e)

def test_connection(target_ip, port, timeout=5):
    """Test TCP connection to a target."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((target_ip, port))
        sock.close()
        if result == 0:
            return True, "Connected"
        else:
            return False, f"Connection failed (error {result})"
    except Exception as e:
        return False, str(e)

def start_test_server(ip, port, session_id="TEST123"):
    """Start a minimal test server."""
    print(f"Starting test server on {ip}:{port}")
    
    try:
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((ip, port))
        server_sock.listen(5)
        
        print(f"✅ Test server listening on {ip}:{port}")
        
        while True:
            try:
                client_sock, addr = server_sock.accept()
                print(f"📞 Connection from {addr}")
                
                # Read message length
                length_data = client_sock.recv(4)
                if len(length_data) == 4:
                    msg_length = struct.unpack(">I", length_data)[0]
                    msg_data = client_sock.recv(msg_length)
                    
                    try:
                        message = json.loads(msg_data.decode('utf-8'))
                        print(f"📨 Received: {message}")
                        
                        # Send response
                        if message.get('type') == 'auth_request':
                            if message.get('session_id') == session_id:
                                response = {
                                    "type": "auth_response",
                                    "success": True,
                                    "username": message.get('username')
                                }
                                print("✅ Authentication successful")
                            else:
                                response = {
                                    "type": "auth_response", 
                                    "success": False,
                                    "reason": "Invalid session ID"
                                }
                                print("❌ Authentication failed - wrong session ID")
                        else:
                            response = {"type": "unknown", "success": False}
                        
                        # Send response
                        response_data = json.dumps(response).encode('utf-8')
                        response_length = struct.pack(">I", len(response_data))
                        client_sock.sendall(response_length + response_data)
                        
                    except json.JSONDecodeError:
                        print("❌ Invalid JSON received")
                
                client_sock.close()
                
            except socket.timeout:
                continue
            except Exception as e:
                print(f"❌ Server error: {e}")
                break
                
    except Exception as e:
        print(f"❌ Failed to start test server: {e}")
        return False
    finally:
        try:
            server_sock.close()
        except:
            pass

def test_client_connection(server_ip, port, session_id="TEST123", username="testuser"):
    """Test client connection to server."""
    print(f"Testing client connection to {server_ip}:{port}")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        
        print(f"Connecting to {server_ip}:{port}...")
        sock.connect((server_ip, port))
        print("✅ TCP connection established")
        
        # Send auth message
        auth_msg = {
            "type": "auth_request",
            "username": username,
            "session_id": session_id
        }
        
        msg_data = json.dumps(auth_msg).encode('utf-8')
        msg_length = struct.pack(">I", len(msg_data))
        
        sock.sendall(msg_length + msg_data)
        print("📤 Authentication sent")
        
        # Read response
        response_length_data = sock.recv(4)
        if len(response_length_data) == 4:
            response_length = struct.unpack(">I", response_length_data)[0]
            response_data = sock.recv(response_length)
            response = json.loads(response_data.decode('utf-8'))
            
            print(f"📥 Response: {response}")
            
            if response.get('success'):
                print("✅ Client test PASSED")
                return True
            else:
                print(f"❌ Client test FAILED: {response.get('reason')}")
                return False
        else:
            print("❌ No response received")
            return False
            
    except Exception as e:
        print(f"❌ Client connection failed: {e}")
        return False
    finally:
        try:
            sock.close()
        except:
            pass

def main():
    print("=" * 70)
    print("LAN Communication Connection Test")
    print("=" * 70)
    
    local_ip = get_local_ip()
    tcp_port = 54321
    
    print(f"Local IP: {local_ip}")
    print(f"Test Port: {tcp_port}")
    print()
    
    # Test 1: Port binding
    print("🔍 Test 1: Port Binding")
    can_bind, bind_msg = test_port_binding(local_ip, tcp_port)
    print(f"   Bind to {local_ip}:{tcp_port}: {'✅' if can_bind else '❌'} {bind_msg}")
    
    if not can_bind:
        print("❌ Cannot bind to port - testing stopped")
        return
    
    # Test 2: Localhost connection
    print("\n🔍 Test 2: Localhost Connection")
    localhost_ok, localhost_msg = test_connection("127.0.0.1", tcp_port, timeout=2)
    print(f"   Connect to 127.0.0.1:{tcp_port}: {'✅' if localhost_ok else '❌'} {localhost_msg}")
    
    # Test 3: LAN IP connection  
    print(f"\n🔍 Test 3: LAN IP Connection")
    lan_ok, lan_msg = test_connection(local_ip, tcp_port, timeout=2)
    print(f"   Connect to {local_ip}:{tcp_port}: {'✅' if lan_ok else '❌'} {lan_msg}")
    
    # Test 4: Full server-client test
    print(f"\n🔍 Test 4: Server-Client Communication")
    print("Starting test server in background...")
    
    # Start server in thread
    server_thread = threading.Thread(
        target=start_test_server, 
        args=(local_ip, tcp_port),
        daemon=True
    )
    server_thread.start()
    
    # Give server time to start
    time.sleep(2)
    
    # Test client connection
    client_success = test_client_connection(local_ip, tcp_port)
    
    print(f"\n📋 Summary:")
    print(f"   Port binding: {'✅' if can_bind else '❌'}")
    print(f"   Localhost: {'✅' if localhost_ok else '❌'}")
    print(f"   LAN IP: {'✅' if lan_ok else '❌'}")
    print(f"   Full test: {'✅' if client_success else '❌'}")
    
    if can_bind and client_success:
        print(f"\n✅ All tests PASSED - Your setup should work!")
        print(f"   Host IP to share: {local_ip}")
        print(f"   Port: {tcp_port}")
    else:
        print(f"\n❌ Some tests FAILED - Check network configuration")

if __name__ == "__main__":
    main()