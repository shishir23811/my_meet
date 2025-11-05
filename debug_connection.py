#!/usr/bin/env python3
"""
Debug connection issues by testing each component separately.
"""

import sys
import socket
import threading
import time
import json
import struct
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from server.server import LANServer
from client.client import LANClient
from utils.logger import setup_logger

logger = setup_logger(__name__)

def get_local_ip():
    """Get local IP address."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"

def test_server_only():
    """Test server startup in isolation."""
    print("=" * 60)
    print("TEST 1: Server Startup")
    print("=" * 60)
    
    local_ip = get_local_ip()
    session_id = "DEBUG123"
    host_username = "debug_host"
    
    print(f"Local IP: {local_ip}")
    print(f"Session ID: {session_id}")
    print(f"Host: {host_username}")
    
    try:
        server = LANServer(session_id, host_username)
        print("✅ Server object created")
        
        server.start()
        print("✅ Server started successfully")
        print(f"   TCP Port: {server.tcp_port}")
        print(f"   UDP Port: {server.udp_port}")
        
        # Test if server is actually listening
        test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_sock.settimeout(2)
        result = test_sock.connect_ex((local_ip, server.tcp_port))
        test_sock.close()
        
        if result == 0:
            print("✅ Server is accepting connections")
        else:
            print(f"❌ Server not accepting connections (error {result})")
        
        # Keep server running for a bit
        time.sleep(2)
        
        server.stop()
        print("✅ Server stopped cleanly")
        
        return True, server.tcp_port, server.udp_port
        
    except Exception as e:
        print(f"❌ Server test failed: {e}")
        return False, None, None

def test_client_connection(server_ip, tcp_port, udp_port):
    """Test client connection in isolation."""
    print("\n" + "=" * 60)
    print("TEST 2: Client Connection")
    print("=" * 60)
    
    session_id = "DEBUG123"
    username = "debug_client"
    
    print(f"Connecting to: {server_ip}:{tcp_port}")
    print(f"Session ID: {session_id}")
    print(f"Username: {username}")
    
    try:
        # Start server first
        server = LANServer(session_id, "debug_host", tcp_port, udp_port)
        server.start()
        print("✅ Test server started")
        
        # Give server time to start
        time.sleep(1)
        
        # Create client
        client = LANClient(username, server_ip, session_id, tcp_port, udp_port)
        print("✅ Client object created")
        
        # Connect
        success = client.connect()
        if success:
            print("✅ Client connected successfully")
            
            # Wait for authentication
            time.sleep(2)
            
            if client.authenticated:
                print("✅ Client authenticated successfully")
            else:
                print("❌ Client connection succeeded but authentication failed")
        else:
            print("❌ Client connection failed")
        
        # Cleanup
        client.disconnect()
        server.stop()
        
        return success and client.authenticated
        
    except Exception as e:
        print(f"❌ Client test failed: {e}")
        return False

def test_gui_simulation():
    """Test the GUI connection flow simulation."""
    print("\n" + "=" * 60)
    print("TEST 3: GUI Flow Simulation")
    print("=" * 60)
    
    local_ip = get_local_ip()
    session_id = "GUI_TEST"
    
    try:
        # Simulate hosting
        print("Simulating HOST flow...")
        
        # 1. Create server (like app.py does)
        server = LANServer(session_id, "gui_host")
        server_thread = threading.Thread(target=server.start, daemon=True)
        server_thread.start()
        
        # 2. Wait for server to start (like app.py does)
        time.sleep(1.0)
        
        if not server.running:
            print("❌ Server failed to start")
            return False
        
        print(f"✅ Server started on {local_ip}:{server.tcp_port}")
        
        # 3. Connect as client to own server (like app.py does)
        client = LANClient("gui_host", local_ip, session_id, server.tcp_port, server.udp_port)
        
        if client.connect():
            print("✅ Host connected to own server")
            
            # Wait for auth
            time.sleep(1)
            
            if client.authenticated:
                print("✅ Host authenticated successfully")
                
                # Now simulate participant joining
                print("\nSimulating PARTICIPANT flow...")
                
                # 4. Create participant client
                participant = LANClient("participant", local_ip, session_id, server.tcp_port, server.udp_port)
                
                if participant.connect():
                    print("✅ Participant connected to server")
                    
                    time.sleep(1)
                    
                    if participant.authenticated:
                        print("✅ Participant authenticated successfully")
                        print("✅ GUI simulation PASSED")
                        result = True
                    else:
                        print("❌ Participant authentication failed")
                        result = False
                else:
                    print("❌ Participant connection failed")
                    result = False
                
                participant.disconnect()
            else:
                print("❌ Host authentication failed")
                result = False
        else:
            print("❌ Host connection to own server failed")
            result = False
        
        # Cleanup
        client.disconnect()
        server.stop()
        
        return result
        
    except Exception as e:
        print(f"❌ GUI simulation failed: {e}")
        return False

def test_connectivity_check():
    """Test the connectivity check function from app.py."""
    print("\n" + "=" * 60)
    print("TEST 4: Connectivity Check Function")
    print("=" * 60)
    
    local_ip = get_local_ip()
    
    # Test connectivity check with no server
    print("Testing connectivity check with no server...")
    test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    test_socket.settimeout(3.0)
    result = test_socket.connect_ex((local_ip, 54321))
    test_socket.close()
    
    if result != 0:
        print("✅ Connectivity check correctly detects no server")
    else:
        print("❌ Connectivity check incorrectly reports server present")
    
    # Test with server running
    print("Testing connectivity check with server running...")
    server = LANServer("CONN_TEST", "conn_host")
    server.start()
    time.sleep(1)
    
    test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    test_socket.settimeout(3.0)
    result = test_socket.connect_ex((local_ip, server.tcp_port))
    test_socket.close()
    
    if result == 0:
        print("✅ Connectivity check correctly detects server")
        success = True
    else:
        print("❌ Connectivity check fails to detect running server")
        success = False
    
    server.stop()
    return success

def main():
    print("LAN Communication Debug Tool")
    print("Systematically testing each component...")
    
    local_ip = get_local_ip()
    print(f"\nLocal IP: {local_ip}")
    
    # Test 1: Server startup
    server_ok, tcp_port, udp_port = test_server_only()
    
    # Test 2: Client connection (if server worked)
    if server_ok and tcp_port and udp_port:
        client_ok = test_client_connection(local_ip, tcp_port, udp_port)
    else:
        client_ok = False
        print("\n❌ Skipping client test due to server failure")
    
    # Test 3: GUI simulation
    gui_ok = test_gui_simulation()
    
    # Test 4: Connectivity check
    conn_check_ok = test_connectivity_check()
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Server startup:      {'✅ PASS' if server_ok else '❌ FAIL'}")
    print(f"Client connection:   {'✅ PASS' if client_ok else '❌ FAIL'}")
    print(f"GUI simulation:      {'✅ PASS' if gui_ok else '❌ FAIL'}")
    print(f"Connectivity check:  {'✅ PASS' if conn_check_ok else '❌ FAIL'}")
    
    if all([server_ok, client_ok, gui_ok, conn_check_ok]):
        print("\n✅ ALL TESTS PASSED - Network layer is working correctly")
        print("   The issue is likely in the GUI layer or user workflow")
    else:
        print("\n❌ SOME TESTS FAILED - Network layer has issues")
        
        if not server_ok:
            print("   → Server cannot start or bind to ports")
        if not client_ok:
            print("   → Client cannot connect or authenticate")
        if not gui_ok:
            print("   → GUI workflow simulation failed")
        if not conn_check_ok:
            print("   → Connectivity check function is broken")

if __name__ == "__main__":
    main()