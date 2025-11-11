#!/bin/bash
#
# Production Simulation Script
# Simulates a complete production environment and tests the full workflow
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PORT=${PORT:-3001}
API_URL="http://localhost:${PORT}"
LOG_DIR="logs"
MAX_WAIT=90  # Maximum wait time for services to start (backend needs 30-60s for initialization)

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Production Environment Simulation${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Helper functions
check_service() {
    local service=$1
    local check_cmd=$2
    local name=$3
    
    echo -n "Checking $name... "
    if eval "$check_cmd" > /dev/null 2>&1; then
        echo -e "${GREEN}✅${NC}"
        return 0
    else
        echo -e "${RED}❌${NC}"
        return 1
    fi
}

wait_for_service() {
    local name=$1
    local check_cmd=$2
    local max_wait=$3
    local waited=0
    
    echo -n "Waiting for $name to be ready... "
    while [ $waited -lt $max_wait ]; do
        if eval "$check_cmd" > /dev/null 2>&1; then
            echo -e "${GREEN}✅${NC}"
            return 0
        fi
        sleep 2
        waited=$((waited + 2))
        if [ $((waited % 10)) -eq 0 ]; then
            echo -n " ($waited/$max_wait)s"
        else
            echo -n "."
        fi
    done
    echo -e "${YELLOW}⚠️  Timeout${NC}"
    return 1
}

# Step 1: Prerequisites Check
echo -e "${YELLOW}[1/8] Checking Prerequisites...${NC}"
echo ""

check_service "Redis" "redis-cli ping" "Redis Server" || {
    echo -e "${RED}Redis is not running. Starting Redis...${NC}"
    redis-server --daemonize yes --port 6379
    sleep 2
    check_service "Redis" "redis-cli ping" "Redis Server" || {
        echo -e "${RED}Failed to start Redis${NC}"
        exit 1
    }
}

check_service "Python" "python3 --version" "Python 3" || {
    echo -e "${RED}Python 3 is not installed${NC}"
    exit 1
}

check_service "Node.js" "node --version" "Node.js" || {
    echo -e "${RED}Node.js is not installed${NC}"
    exit 1
}

check_service "Virtual Environment" "[ -f venv/bin/python3 ]" "Python Virtual Environment" || {
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip -q
    pip install crewai redis requests python-dotenv pydantic -q
    echo -e "${GREEN}✅ Virtual environment created${NC}"
}

echo ""

# Step 2: Install Dependencies
echo -e "${YELLOW}[2/8] Installing Dependencies...${NC}"
echo ""

if [ -f venv/bin/python3 ]; then
    source venv/bin/activate
    echo -n "Checking CrewAI installation... "
    if python3 -c "import crewai" 2>/dev/null; then
        echo -e "${GREEN}✅${NC}"
    else
        echo -e "${YELLOW}Installing...${NC}"
        pip install crewai redis requests python-dotenv pydantic -q
        echo -e "${GREEN}✅ Installed${NC}"
    fi
else
    echo -e "${RED}Virtual environment not found${NC}"
    exit 1
fi

echo ""

# Step 3: Start Redis (if not running)
echo -e "${YELLOW}[3/8] Starting Redis...${NC}"
if ! redis-cli ping > /dev/null 2>&1; then
    redis-server --daemonize yes --port 6379
    wait_for_service "Redis" "redis-cli ping" 10
else
    echo -e "${GREEN}✅ Redis already running${NC}"
fi
echo ""

# Step 4: Start Python Agents
echo -e "${YELLOW}[4/8] Starting Python Agents...${NC}"

# Stop existing agents
pkill -f "start_all_agents.py" 2>/dev/null || true
sleep 2

# Create logs directory
mkdir -p $LOG_DIR

# Start agents with API_URL
export API_URL
nohup venv/bin/python3 agents/start_all_agents.py > $LOG_DIR/python-agents.log 2> $LOG_DIR/python-agents-error.log &
AGENT_PID=$!

echo "Python agents started (PID: $AGENT_PID)"
echo "Waiting for agents to initialize and send heartbeats..."

# Wait for heartbeats
echo -n "Waiting for agent heartbeats... "
for i in {1..30}; do
    heartbeat_count=$(redis-cli KEYS "crewai:agent:*:heartbeat" 2>/dev/null | wc -l)
    if [ "$heartbeat_count" -gt 0 ]; then
        echo -e "${GREEN}✅ Found $heartbeat_count agents${NC}"
        break
    fi
    sleep 2
    echo -n "."
done

if [ "$heartbeat_count" -eq 0 ]; then
    echo -e "${YELLOW}⚠️  No heartbeats yet (agents may still be starting)${NC}"
fi

# Show active agents
echo ""
echo "Active agents:"
redis-cli KEYS "crewai:agent:*:heartbeat" 2>/dev/null | sed 's/crewai:agent://' | sed 's/:heartbeat//' | while read agent; do
    echo -e "  ${GREEN}✅ $agent${NC}"
done

echo ""

# Step 5: Start Node.js Backend
echo -e "${YELLOW}[5/8] Starting Node.js Backend...${NC}"

# Check if backend is already running
if curl -s "$API_URL/api/health" > /dev/null 2>&1; then
    echo -e "${YELLOW}Backend already running. Restarting...${NC}"
    pkill -f "node.*server.js" 2>/dev/null || pkill -f "npm.*start" 2>/dev/null || true
    sleep 3
fi

# Start backend in background
cd "$(dirname "$0")"
npm start > $LOG_DIR/node-backend.log 2> $LOG_DIR/node-backend-error.log &
BACKEND_PID=$!

echo "Backend started (PID: $BACKEND_PID)"
echo "Waiting for backend initialization (this may take 30-60 seconds)..."
# Wait for backend to respond with healthy status
wait_for_service "Node.js Backend" "curl -s $API_URL/api/health 2>/dev/null | python3 -c 'import sys, json; d=json.load(sys.stdin); exit(0 if d.get(\"status\")==\"healthy\" else 1)'" $MAX_WAIT || {
    echo -e "${YELLOW}⚠️  Health check timeout, but checking if backend is responding...${NC}"
    if curl -s "$API_URL/api/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Backend is responding${NC}"
    else
        echo -e "${RED}❌ Backend not responding. Check logs: $LOG_DIR/node-backend-error.log${NC}"
        echo "Last 10 lines of backend log:"
        tail -10 $LOG_DIR/node-backend.log 2>/dev/null || echo "No log file found"
    fi
}
echo ""

# Step 6: Verify System Health
echo -e "${YELLOW}[6/8] Verifying System Health...${NC}"
echo ""

# Check backend health
health_response=$(curl -s "$API_URL/api/health" 2>/dev/null)
if echo "$health_response" | grep -q '"status":"healthy"'; then
    echo -e "${GREEN}✅ Backend health: OK${NC}"
else
    echo -e "${RED}❌ Backend health check failed${NC}"
    echo "$health_response"
fi

# Check Redis connection
if redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Redis connection: OK${NC}"
else
    echo -e "${RED}❌ Redis connection failed${NC}"
fi

# Check agent count
agent_count=$(redis-cli KEYS "crewai:agent:*:heartbeat" 2>/dev/null | wc -l)
echo -e "${GREEN}✅ Active agents: $agent_count${NC}"

# Check agent list endpoint
agents_response=$(curl -s "$API_URL/api/agents" 2>/dev/null)
if echo "$agents_response" | grep -q '"count"'; then
    echo -e "${GREEN}✅ Agent registry: OK${NC}"
else
    echo -e "${RED}❌ Agent registry failed${NC}"
fi

echo ""

# Step 7: Test Workflow
echo -e "${YELLOW}[7/8] Testing Production Workflow...${NC}"
echo ""

test_queries=(
    "What is the sales forecast for next quarter?"
    "How should I allocate my marketing budget?"
    "What are the inventory risks for product X?"
    "Run a scenario simulation for pricing strategy"
)

for query in "${test_queries[@]}"; do
    echo -n "Testing: \"$query\"... "
    
    response=$(curl -s -X POST "$API_URL/api/process-message" \
        -H "Content-Type: application/json" \
        -d "{\"message\": \"$query\", \"conversationId\": \"test-$(date +%s)\"}" \
        2>/dev/null)
    
    if echo "$response" | grep -q "turnEnvelope\|intentClassification"; then
        echo -e "${GREEN}✅${NC}"
        
        # Check if real agents are being used
        if echo "$response" | grep -q "mode.*real\|REAL"; then
            echo -e "  ${GREEN}✓ Using REAL agents${NC}"
        elif echo "$response" | grep -q "mode.*simulated\|SIMULATED"; then
            echo -e "  ${YELLOW}⚠ Using simulated agents${NC}"
        fi
    else
        echo -e "${RED}❌${NC}"
        echo "  Response: $response"
    fi
    
    sleep 1
done

echo ""

# Step 8: Production Status Summary
echo -e "${YELLOW}[8/8] Production Status Summary${NC}"
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  System Status${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Service status
echo -e "${BLUE}Services:${NC}"
echo -e "  Redis:        $(redis-cli ping 2>/dev/null | grep -q PONG && echo -e "${GREEN}✅ Running${NC}" || echo -e "${RED}❌ Stopped${NC}")"
echo -e "  Node.js:      $(curl -s "$API_URL/api/health" > /dev/null 2>&1 && echo -e "${GREEN}✅ Running${NC}" || echo -e "${RED}❌ Stopped${NC}")"
echo -e "  Python Agents: $(ps aux | grep -q "[s]tart_all_agents.py" && echo -e "${GREEN}✅ Running${NC}" || echo -e "${RED}❌ Stopped${NC}")"
echo ""

# Agent status
echo -e "${BLUE}Agents:${NC}"
active_agents=$(redis-cli KEYS "crewai:agent:*:heartbeat" 2>/dev/null | wc -l)
echo -e "  Active:       ${GREEN}$active_agents agents${NC}"
echo -e "  Mode:         $(curl -s "$API_URL/api/health" 2>/dev/null | grep -q "redisEnabled.*true" && echo -e "${GREEN}Real Agents${NC}" || echo -e "${YELLOW}Simulated${NC}")"
echo ""

# Endpoints
echo -e "${BLUE}Endpoints:${NC}"
echo -e "  API:          ${GREEN}$API_URL${NC}"
echo -e "  Health:       ${GREEN}$API_URL/api/health${NC}"
echo -e "  Agents:       ${GREEN}$API_URL/api/agents${NC}"
echo -e "  Process:      ${GREEN}$API_URL/api/process-message${NC}"
echo ""

# Logs
echo -e "${BLUE}Logs:${NC}"
echo -e "  Backend:      ${GREEN}$LOG_DIR/node-backend.log${NC}"
echo -e "  Agents:       ${GREEN}$LOG_DIR/python-agents.log${NC}"
echo -e "  Errors:       ${GREEN}$LOG_DIR/python-agents-error.log${NC}"
echo ""

# PIDs
echo -e "${BLUE}Process IDs:${NC}"
echo -e "  Backend PID:  ${GREEN}$BACKEND_PID${NC}"
echo -e "  Agents PID:   ${GREEN}$AGENT_PID${NC}"
echo ""

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Production Simulation Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}To stop all services:${NC}"
echo -e "  pkill -f 'start_all_agents.py'"
echo -e "  pkill -f 'node.*server.js'"
echo -e "  redis-cli shutdown"
echo ""
echo -e "${YELLOW}Or use:${NC} ./stop-production.sh"
echo ""

