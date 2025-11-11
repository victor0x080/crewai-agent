#!/bin/bash
# Stop IMS Agent Backend Project
# Stops all services started by start.sh

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/.pids"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Stopping IMS Agent Backend Project${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Stop Python Agents
echo -e "${YELLOW}Stopping Python Agents...${NC}"
if [ -f "$PID_FILE" ]; then
    if grep -q "python-agents:" "$PID_FILE"; then
        PID=$(grep "python-agents:" "$PID_FILE" | cut -d: -f2)
        if ps -p "$PID" > /dev/null 2>&1; then
            kill "$PID" 2>/dev/null || true
            echo -e "${GREEN}✅ Stopped Python Agents (PID: $PID)${NC}"
        fi
    fi
fi
pkill -f "start_all_agents.py" 2>/dev/null && echo -e "${GREEN}✅ Stopped remaining Python agents${NC}" || true
pkill -f "runners/.*\.py" 2>/dev/null && echo -e "${GREEN}✅ Stopped Python agent runners${NC}" || true
sleep 2

# Stop Node.js Backend
echo -e "${YELLOW}Stopping Node.js Backend...${NC}"
if [ -f "$PID_FILE" ]; then
    if grep -q "node-backend:" "$PID_FILE"; then
        PID=$(grep "node-backend:" "$PID_FILE" | cut -d: -f2)
        if ps -p "$PID" > /dev/null 2>&1; then
            kill "$PID" 2>/dev/null || true
            echo -e "${GREEN}✅ Stopped Node.js Backend (PID: $PID)${NC}"
        fi
    fi
fi
pkill -f "node.*server.js" 2>/dev/null && echo -e "${GREEN}✅ Stopped Node.js server${NC}" || true
pkill -f "npm.*start" 2>/dev/null && echo -e "${GREEN}✅ Stopped npm process${NC}" || true
sleep 2

# Clean up PID file
if [ -f "$PID_FILE" ]; then
    rm "$PID_FILE"
fi

echo ""
echo -e "${GREEN}✅ All services stopped${NC}"
echo ""

# Optional: Stop Redis (comment out if you want Redis to keep running)
read -p "Stop Redis as well? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    redis-cli shutdown 2>/dev/null && echo -e "${GREEN}✅ Redis stopped${NC}" || echo -e "${YELLOW}⚠️  Redis was not running${NC}"
fi

echo ""

