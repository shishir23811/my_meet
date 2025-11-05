#!/usr/bin/env python3
"""
Quick test to simulate host and join on same machine.
"""

import sys
import time
import threading
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from server.server import LANServer
from client.client import LANClient

def simulate_host_and_join():
    """Simulate hosting and joining on same machine."""
    print("🚀 Starting Host and Join Simulation")
    print("=" * 50)
    
    session_id = "DEMO123"
    local_ip = "172.17.131.211"
    
    # Step 1: Start server (simulate host)
    print("👑 STEP 1: Starting Host Server")
    server = LANServer(session_id, "host_user")
    server.start()
    
    print(f"✅ Server started on {local_ip}:{server.tcp_port}")
    print(f"   Session ID: {session_id}")
    
    # Give server time to fully start
    time.sleep(2)
    
    # Step 2: Connect host client
    print("\n👑 STEP 2: Host Connecting to Own Server")
    host_client = LANClient("host_user", local_ip, session_id, server.tcp_port, server.udp_port)
    
    if host_client.connect():
        print("✅ Host connected successfully")
        time.sleep(1)
        if host_client.authenticated:
            print("✅ Host authenticated successfully")
        else:
            print("❌ Host authentication failed")
            return False
    else:
        print("❌ Host connection failed")
        return False
    
    # Step 3: Simulate participant joining
    print("\n👤 STEP 3: Participant Joining Session")
    participant_client = LANClient("participant_user", local_ip, session_id, server.tcp_port, server.udp_port)
    
    if participant_client.connect():
        print("✅ Participant connected successfully")
        time.sleep(1)
        if participant_client.authenticated:
            print("✅ Participant authenticated successfully")
            print("🎉 SUCCESS: Both host and participant connected!")
            success = True
        else:
            print("❌ Participant authentication failed")
            success = False
    else:
        print("❌ Participant connection failed")
        success = False
    
    # Cleanup
    print("\n🧹 Cleaning up...")
    participant_client.disconnect()
    host_client.disconnect()
    time.sleep(1)
    server.stop()
    
    return success

if __name__ == "__main__":
    success = simulate_host_and_join()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ SIMULATION SUCCESSFUL!")
        print("\nThis proves the application works correctly.")
        print("For cross-device connections:")
        print("1. Run setup_firewall.bat as Administrator on host machine")
        print("2. Make sure both devices are on same WiFi network")
        print("3. Host starts session and shares IP + Session ID")
        print("4. Participant uses exact IP and Session ID to join")
    else:
        print("❌ SIMULATION FAILED!")
        print("There may be an issue with the application code.")