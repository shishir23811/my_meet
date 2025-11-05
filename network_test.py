#!/usr/bin/env python3
"""
Network connectivity test for LAN Communication Application.
Helps diagnose network issues between host and participants.
"""

import socket
import sys
import json
from pathlib import Path

def get_local_ip():
    """Get the local IP address."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"

def load_config():
    """Load network configuration."""
    config_file = Path("config.json")
    if config_file.exists():
        with open(config_file) as f:
            config = json.load(f)
            return config.get("network", {})
    return {"tcp_port": 54321, "udp_port": 54322}

def test_port_availability(ip, port, protocol="TCP"):
    """Test if a port is available for binding."""
    try:
        if protocol.upper() == "TCP":
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        else:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((ip, port))
        sock.close()
        return True, "Available"
    except OSError as e:
        return False, str(e)

def test_connectivity(target_ip, port, timeout=5):
    """Test connectivity to a remote host."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((target_ip, port))
        sock.close()
        if result == 0:
            return True, "Connected successfully"
        else:
            return False, f"Connection failed (error {result})"
    except Exception as e:
        return False, str(e)

def main():
    print("=" * 60)
    print("LAN Communication Network Diagnostics")
    print("=" * 60)
    
    # Get local network info
    local_ip = get_local_ip()
    config = load_config()
    tcp_port = config.get("tcp_port", 54321)
    udp_port = config.get("udp_port", 54322)
    
    print(f"\n📍 Local Network Information:")
    print(f"   Local IP Address: {local_ip}")
    print(f"   TCP Port: {tcp_port}")
    print(f"   UDP Port: {udp_port}")
    
    # Test port availability for hosting
    print(f"\n🔍 Port Availability Test (for hosting):")
    tcp_available, tcp_msg = test_port_availability(local_ip, tcp_port, "TCP")
    udp_available, udp_msg = test_port_availability(local_ip, udp_port, "UDP")
    
    print(f"   TCP {tcp_port}: {'✅ Available' if tcp_available else '❌ ' + tcp_msg}")
    print(f"   UDP {udp_port}: {'✅ Available' if udp_available else '❌ ' + udp_msg}")
    
    if not tcp_available or not udp_available:
        print(f"\n⚠️  Some ports are not available. The application will try to find alternative ports.")
    
    # Test connectivity to another host (if provided)
    if len(sys.argv) > 1:
        target_ip = sys.argv[1]
        print(f"\n🌐 Connectivity Test to {target_ip}:")
        
        tcp_connected, tcp_msg = test_connectivity(target_ip, tcp_port)
        print(f"   TCP {target_ip}:{tcp_port}: {'✅ ' + tcp_msg if tcp_connected else '❌ ' + tcp_msg}")
        
        if not tcp_connected:
            print(f"\n💡 Troubleshooting suggestions:")
            print(f"   1. Make sure the host has started a session")
            print(f"   2. Check if both devices are on the same network")
            print(f"   3. Verify firewall settings allow connections on port {tcp_port}")
            print(f"   4. Try running: telnet {target_ip} {tcp_port}")
    else:
        print(f"\n💡 To test connectivity to a host, run:")
        print(f"   python network_test.py <host_ip_address>")
    
    print(f"\n📋 Network Summary:")
    print(f"   • Host should share this IP: {local_ip}")
    print(f"   • Participants should connect to: {local_ip}:{tcp_port}")
    print(f"   • Make sure both devices are on the same WiFi/LAN")
    print("=" * 60)

if __name__ == "__main__":
    main()