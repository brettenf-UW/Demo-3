#!/bin/bash

# Make script executable
chmod +x "$0"

# Print server information
echo "====== Server Information ======"
echo "Hostname: $(hostname)"
echo "IP Address: $(hostname -I | awk '{print $1}')"
echo "==============================="
echo

# Open port 7860 for Gradio web interface
echo "Opening port 7860 for external access..."
sudo iptables -A INPUT -p tcp --dport 7860 -j ACCEPT

# Check if port is open
echo "Checking if port 7860 is open..."
if nc -z localhost 7860; then
  echo "✅ Port 7860 is open locally"
else
  echo "❌ Port 7860 is closed locally (this is normal if the app isn't running yet)"
fi

# Show access URLs
echo
echo "====== Access URLs ======"
echo "Local access: http://localhost:7860"
echo "Network access: http://$(hostname -I | awk '{print $1}'):7860"
echo "========================="
echo
echo "To start the web interface, run: ./start_ui.sh"
echo "The interface will also generate a temporary public URL when started."