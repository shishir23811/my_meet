#!/usr/bin/env python3
"""
Network Diagnostics Tool for LAN Communication Application

This tool helps diagnose network connectivity issues when joining sessions.
"""

import socket
import subprocess
import sys
from utils.config import DEFAULT_TCP_PORT, DEFAULT_UDP_PORT

def test_port_connectivity(host: str, port: int, timeout: float = 5.0) -> bool:
    """Test if a specific port is reachable on a host."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        print(f"Error testing {host}:{port} - {e}")
        return False

def ping_host(host: str) -> bool:
    """Test basic network connectivity to host using ping."""
    try:
        # Windows uses -n, Unix uses -c
        param = '-n' if sys.platform.startswith('win') else '-c'
        result = subprocess.run(['ping', param, '1', host], 
                              capture_output=True, text=True, timeout=10)
        return result.returncode == 0
    except Exception as e:
        print(f"Error pinging {host} - {e}")
        return False

def get_local_ip() -> str:
    """Get the local IP address."""
    try:
        # Connect to a remote address to determine local IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "Unable to determine"

def diagnose_connection(server_ip: str):
    """Run comprehensive network diagnostics."""
    print("=" * 60)
    print("LAN Communication - Network Diagnostics")
    print("=" * 60)
    print()
    
    # Basic info
    print(f"Local IP Address: {get_local_ip()}")
    print(f"Target Server: {server_ip}")
    print(f"Expected TCP Port: {DEFAULT_TCP_PORT}")
    print(f"Expected UDP Port: {DEFAULT_UDP_PORT}")
    print()
    
    # Test basic connectivity
    print("Testing basic network connectivity...")
    if ping_host(server_ip):
        print(f"✅ Host {server_ip} is reachable (ping successful)")
    else:
        print(f"❌ Host {server_ip} is not reachable (ping failed)")
        print("   This could mean:")
        print("   • The host is not on the same network")
        print("   • The IP address is incorrect")
        print("   • The host is blocking ping requests")
    print()
    
    # Test TCP port
    print(f"Testing TCP port {DEFAULT_TCP_PORT}...")
    if test_port_connectivity(server_ip, DEFAULT_TCP_PORT):
        print(f"✅ TCP port {DEFAULT_TCP_PORT} is open and accepting connections")
    else:
        print(f"❌ TCP port {DEFAULT_TCP_PORT} is not accessible")
        print("   This could mean:")
        print("   • The server is not running")
        print("   • A firewall is blocking the port")
        print("   • The server is using a different port")
    print()
    
    # Test UDP port
    print(f"Testing UDP port {DEFAULT_UDP_PORT}...")
    print(f"ℹ️  UDP port testing is limited (UDP is connectionless)")
    print(f"   If TCP works, UDP should work too")
    print()
    
    # Recommendations
    print("Troubleshooting Recommendations:")
    print("=" * 40)
    print("1. Ensure both devices are on the same network")
    print("2. Check that the host has started the session")
    print("3. Verify the IP address is correct")
    if sys.platform.startswith('win'):
        print("4. Check Windows Firewall settings:")
        print(f"   • Allow incoming connections on port {DEFAULT_TCP_PORT}")
        print(f"   • Allow incoming connections on port {DEFAULT_UDP_PORT}")
        print("5. Try temporarily disabling firewall for testing")
    else:
        print("4. Check Ubuntu Firewall (UFW) settings:")
        print(f"   • sudo ufw allow {DEFAULT_TCP_PORT}/tcp")
        print(f"   • sudo ufw allow {DEFAULT_UDP_PORT}/udp")
        print("5. Run: ./setup_firewall_ubuntu.sh")
    print("6. Ensure no other application is using these ports")
    print()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python network_diagnostics.py <server_ip>")
        print("Example: python network_diagnostics.py 192.168.1.100")
        sys.exit(1)
    
    server_ip = sys.argv[1]
    diagnose_connection(server_ip)