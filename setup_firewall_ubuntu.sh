#!/bin/bash

echo "============================================================"
echo "LAN Communicator - Ubuntu Firewall Setup"
echo "============================================================"
echo
echo "This script will configure UFW (Ubuntu Firewall) to allow"
echo "LAN Communicator to accept incoming connections on ports"
echo "5555 (TCP) and 5556 (UDP)."
echo
echo "IMPORTANT: Run this script on the HOST computer!"
echo
read -p "Press Enter to continue or Ctrl+C to cancel..."

echo
echo "Setting up firewall rules..."

# Check if UFW is installed
if ! command -v ufw &> /dev/null; then
    echo "Installing UFW (Ubuntu Firewall)..."
    sudo apt update
    sudo apt install -y ufw
fi

# Allow TCP port 5555
echo "Adding rule for TCP port 5555..."
sudo ufw allow 5555/tcp comment "LAN Communicator TCP"

# Allow UDP port 5556
echo "Adding rule for UDP port 5556..."
sudo ufw allow 5556/udp comment "LAN Communicator UDP"

# Enable firewall
echo "Enabling firewall..."
sudo ufw --force enable

echo
echo "============================================================"
echo "Firewall setup complete!"
echo "============================================================"
echo
echo "The following rules were added:"
echo "- TCP port 5555 (LAN Communicator TCP)"
echo "- UDP port 5556 (LAN Communicator UDP)"
echo
echo "Current firewall status:"
sudo ufw status numbered
echo
echo "You can now start hosting sessions and others should be able to connect."
echo
echo "To remove these rules later (if needed):"
echo "  sudo ufw delete allow 5555/tcp"
echo "  sudo ufw delete allow 5556/udp"
echo