#!/bin/bash

# Make this script executable
chmod +x "$0"

# ANSI color codes for prettier output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Parse command line arguments
SHARE_FLAG=""
PORT=7860

while [[ $# -gt 0 ]]; do
  case $1 in
    --share)
      SHARE_FLAG="--share"
      shift
      ;;
    --port=*)
      PORT="${1#*=}"
      shift
      ;;
    --port)
      PORT="$2"
      shift
      shift
      ;;
    *)
      echo -e "${YELLOW}Unknown option: $1${NC}"
      shift
      ;;
  esac
done

echo -e "${CYAN}======= Starting School Schedule Optimizer UI =======${NC}"

# Get IP information
PRIVATE_IP=$(hostname -I | awk '{print $1}')

# Display access information
echo -e "${CYAN}The UI will be accessible from:${NC}"
echo -e "1. Local access: ${GREEN}http://localhost:$PORT${NC}"
echo -e "2. Network access: ${GREEN}http://$PRIVATE_IP:$PORT${NC}"

if [[ -n "$SHARE_FLAG" ]]; then
  echo -e "3. ${YELLOW}Public access: A temporary public URL will be displayed below${NC}"
else
  echo -e "${YELLOW}Note: For a public access link, restart with --share flag${NC}"
fi

echo ""
echo -e "${CYAN}Starting server on port $PORT...${NC}"
python3 app.py --port $PORT $SHARE_FLAG