#!/bin/bash

# Make this script executable
chmod +x "$0"

# ANSI color codes for prettier output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}======= School Schedule Optimizer Server Setup =======${NC}"
echo -e "${CYAN}This script will prepare your server for external access${NC}"
echo ""

# Get server information
HOSTNAME=$(hostname)
PRIVATE_IP=$(hostname -I | awk '{print $1}')

echo -e "${CYAN}Server Information:${NC}"
echo -e "Hostname: ${GREEN}$HOSTNAME${NC}"
echo -e "Private IP: ${GREEN}$PRIVATE_IP${NC}"

# Check if we can get public IP
echo -e "${CYAN}Checking for public IP...${NC}"
if which wget > /dev/null; then
  PUBLIC_IP=$(wget -qO- http://checkip.amazonaws.com || echo "Not available")
  echo -e "Public IP: ${GREEN}$PUBLIC_IP${NC}"
elif which curl > /dev/null; then
  PUBLIC_IP=$(curl -s http://checkip.amazonaws.com || echo "Not available")
  echo -e "Public IP: ${GREEN}$PUBLIC_IP${NC}"
else
  echo -e "${YELLOW}Unable to determine public IP - wget or curl not available${NC}"
  PUBLIC_IP="Not available"
fi

echo ""
echo -e "${CYAN}======= Firewall Configuration =======${NC}"
# Open port 7860 for Gradio web interface
echo -e "${CYAN}Opening port 7860 in iptables...${NC}"
sudo iptables -C INPUT -p tcp --dport 7860 -j ACCEPT 2>/dev/null
if [ $? -ne 0 ]; then
  sudo iptables -A INPUT -p tcp --dport 7860 -j ACCEPT
  echo -e "${GREEN}✓ Port 7860 opened successfully${NC}"
else
  echo -e "${YELLOW}✓ Port 7860 was already open${NC}"
fi

# Install dependencies
echo ""
echo -e "${CYAN}======= Installing Dependencies =======${NC}"
echo -e "${CYAN}Installing required packages...${NC}"
pip install -r ui_requirements.txt
echo -e "${GREEN}✓ Dependencies installed successfully${NC}"

# Set permissions
echo ""
echo -e "${CYAN}======= Setting Permissions =======${NC}"
echo -e "${CYAN}Setting appropriate permissions for output directory...${NC}"
sudo chown -R ec2-user:ec2-user output/
echo -e "${GREEN}✓ Permissions set successfully${NC}"

# Final information
echo ""
echo -e "${CYAN}======= Access Information =======${NC}"
echo -e "Your server is now configured for external access."
echo -e ""
echo -e "You can access the optimizer UI via:"
echo -e "1. Local access: ${GREEN}http://localhost:7860${NC}"
echo -e "2. Private network: ${GREEN}http://$PRIVATE_IP:7860${NC}"
if [ "$PUBLIC_IP" != "Not available" ]; then
  echo -e "3. Public access (if port 7860 is open in security group): ${GREEN}http://$PUBLIC_IP:7860${NC}"
fi
echo -e "4. Temporary public URL (generated when you start the app with --share)"
echo -e ""
echo -e "${CYAN}======= AWS Security Group Information =======${NC}"
echo -e "${YELLOW}Important:${NC} If running on AWS EC2, you must also configure your security group:"
echo -e "1. Go to EC2 Dashboard → Security Groups"
echo -e "2. Select the security group for this instance"
echo -e "3. Edit Inbound Rules"
echo -e "4. Add Rule: Custom TCP, Port 7860, Source: 0.0.0.0/0 (or your IP for better security)"
echo -e ""
echo -e "${CYAN}======= Starting the Server =======${NC}"
echo -e "To start the server with a public share link:"
echo -e "${GREEN}./start_ui.sh --share${NC}"
echo -e ""
echo -e "To start the server on the local network only:"
echo -e "${GREEN}./start_ui.sh${NC}"
echo -e ""
echo -e "${CYAN}=============================================${NC}"