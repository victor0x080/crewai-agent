#!/bin/bash
# Start IMS Agent Backend Project
# Starts Redis, Python Agents, and Node.js Backend

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
PID_FILE="$SCRIPT_DIR/.pids"

# Create directories
mkdir -p "$LOG_DIR"
rm -f "$PID_FILE" 2>/dev/null || true

# Load environment variables
if [ -f "$SCRIPT_DIR/.env" ]; then
    # Use a more robust method that handles comments and empty lines
    while IFS= read -r line; do
        # Skip empty lines and lines starting with #
        [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue
        # Skip lines that don't contain =
        [[ ! "$line" =~ = ]] && continue
        
        # Extract key and value
        key=$(echo "$line" | cut -d'=' -f1 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        value=$(echo "$line" | cut -d'=' -f2- | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        
        # Skip if key is empty or starts with #
        [[ -z "$key" || "$key" =~ ^# ]] && continue
        
        # Remove quotes from value if present
        value=$(echo "$value" | sed -e 's/^["'\'']//' -e 's/["'\'']$//')
        
        # Export the variable
        export "$key=$value"
    done < "$SCRIPT_DIR/.env"
fi

# Default runtime flags to keep agents idle unless requested
# - RUN_MINIMAL_AGENTS=true starts only core CrewAI runners
# - RUN_GENERIC_AGENTS=false skips legacy generic agents by default
export RUN_MINIMAL_AGENTS=${RUN_MINIMAL_AGENTS:-false}
export RUN_GENERIC_AGENTS=${RUN_GENERIC_AGENTS:-true}
# Default whitelist: core agents only (can be overridden by env)
export AGENTS_WHITELIST=${AGENTS_WHITELIST:-}

PORT=${PORT:-3001}
API_URL="http://localhost:${PORT}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Starting IMS Agent Backend Project${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Runtime flags: RUN_MINIMAL_AGENTS=${RUN_MINIMAL_AGENTS} RUN_GENERIC_AGENTS=${RUN_GENERIC_AGENTS} AGENTS_WHITELIST=${AGENTS_WHITELIST}"

# Function to wait for service
wait_for_service() {
    local name=$1
    local check_cmd=$2
    local max_wait=$3
    local waited=0
    
    echo -n "Waiting for $name... "
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

# Save PID helper
save_pid() {
    local name=$1
    local pid=$2
    echo "$name:$pid" >> "$PID_FILE"
}

# Step 1: Check Prerequisites
echo -e "${YELLOW}[1/4] Checking Prerequisites...${NC}"
echo ""

# Check Redis
if ! command -v redis-server &> /dev/null; then
    echo -e "${RED}❌ Redis not found${NC}"
    echo "   Install: sudo apt-get install redis-server"
    exit 1
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 not found${NC}"
    echo "   Install: sudo apt-get install python3 python3-pip"
    exit 1
fi

# Check Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js not found${NC}"
    exit 1
fi

# Check npm
if ! command -v npm &> /dev/null; then
    echo -e "${RED}❌ npm not found${NC}"
    exit 1
fi

echo -e "${GREEN}✅ All prerequisites installed${NC}"
echo ""

# Step 2: Start Redis
echo -e "${YELLOW}[2/4] Starting Redis...${NC}"

if redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Redis already running${NC}"
else
    redis-server --daemonize yes --port 6379 2>/dev/null || {
        echo -e "${RED}❌ Failed to start Redis${NC}"
        exit 1
    }
    wait_for_service "Redis" "redis-cli ping" 10
fi

echo ""

# Step 3: Setup Python Environment
echo -e "${YELLOW}[3/4] Setting up Python Environment...${NC}"

cd "$SCRIPT_DIR"

if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip -q
    if [ -f "agents/requirements.txt" ]; then
        pip install -r agents/requirements.txt -q
    else
        pip install crewai redis requests python-dotenv pydantic pandas -q
    fi
    echo -e "${GREEN}✅ Virtual environment created${NC}"
else
    echo -e "${GREEN}✅ Virtual environment exists${NC}"
fi

echo ""

# Step 4: Start Node.js Backend
echo -e "${YELLOW}[4/5] Starting Node.js Backend...${NC}"

# Stop existing backend
pkill -f "node.*server.js" 2>/dev/null || pkill -f "npm.*start" 2>/dev/null || true
sleep 2

cd "$SCRIPT_DIR"

# Install Node.js dependencies if needed
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}Installing Node.js dependencies...${NC}"
    npm install --silent
fi

# Start backend with logs visible
echo "Starting backend..."
npm start > "$LOG_DIR/node-backend.log" 2>&1 &
BACKEND_PID=$!
save_pid "node-backend" "$BACKEND_PID"

echo "Backend started (PID: $BACKEND_PID)"
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}📋 Backend Logs (latest 20 lines):${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
sleep 2
tail -n 20 "$LOG_DIR/node-backend.log" 2>/dev/null || echo "Logs will appear here..."
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "Waiting for backend to initialize (this may take 30-60 seconds)..."
echo -e "${YELLOW}💡 Tip: To see logs in real-time, run: tail -f $LOG_DIR/node-backend.log${NC}"
echo ""
wait_for_service "Node.js Backend" "curl -s $API_URL/api/health 2>/dev/null | python3 -c 'import sys, json; d=json.load(sys.stdin); exit(0 if d.get(\"status\")==\"healthy\" else 1)'" 90 || {
    echo -e "${YELLOW}⚠️  Health check timeout, but checking if backend is responding...${NC}"
    if curl -s "$API_URL/api/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Backend is responding${NC}"
    else
        echo -e "${RED}❌ Backend not responding. Check logs: $LOG_DIR/node-backend.log${NC}"
        echo ""
        echo -e "${RED}Last 10 lines of error log:${NC}"
        tail -n 10 "$LOG_DIR/node-backend.log" 2>/dev/null || echo "No logs available"
    fi
}
echo ""

echo ""

# Final Status
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  ✅ System Started Successfully!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "📊 System Status:"
echo ""

# Check Redis
if redis-cli ping > /dev/null 2>&1; then
    echo -e "  ${GREEN}✅ Redis: Running${NC}"
else
    echo -e "  ${RED}❌ Redis: Not running${NC}"
fi

# Check Node.js Backend
if curl -s "$API_URL/api/health" > /dev/null 2>&1; then
    echo -e "  ${GREEN}✅ Node.js Backend: Running on port $PORT${NC}"
else
    echo -e "  ${RED}❌ Node.js Backend: Not responding${NC}"
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  📋 Endpoints${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "  Health Check:    $API_URL/api/health"
echo "  Process Query:  $API_URL/api/process-message"
echo "  List Agents:    $API_URL/api/agents"
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  📝 Logs${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "  Python Agents:   $LOG_DIR/python-agents.log"
echo "  Python Errors:   $LOG_DIR/python-agents-error.log"
echo "  Node Backend:   $LOG_DIR/node-backend.log"
echo "  Node Errors:    $LOG_DIR/node-backend-error.log"
echo ""
echo -e "${BLUE}========================================${NC}"
echo ""
echo "To stop all services: ./stop.sh"
echo "To test queries: ./query-detail.sh 'Your question here'"
echo ""

# Step 5: Start Python Agents
echo -e "${YELLOW}[5/5] Starting Python Agents...${NC}"

# Stop existing agents
pkill -f "start_all_agents.py" 2>/dev/null || true
pkill -f "runners/.*\.py" 2>/dev/null || true
sleep 2

source venv/bin/activate
export API_URL="$API_URL"

# Start agents
python3 agents/start_all_agents.py > "$LOG_DIR/python-agents.log" 2> "$LOG_DIR/python-agents-error.log" &
AGENTS_PID=$!
save_pid "python-agents" "$AGENTS_PID"

echo "Python agents started (PID: $AGENTS_PID)"
echo "Waiting for agents to initialize..."
sleep 10

# Check agent heartbeats
ACTIVE_AGENTS=$(redis-cli KEYS "crewai:agent:*:heartbeat" 2>/dev/null | wc -l)
echo -e "${GREEN}✅ Found $ACTIVE_AGENTS active agents${NC}"

if [ "$ACTIVE_AGENTS" -gt 0 ]; then
    echo "Active agents (showing first 10):"
    redis-cli KEYS "crewai:agent:*:heartbeat" 2>/dev/null | sed 's/crewai:agent://g' | sed 's/:heartbeat//g' | sort | head -10 | sed 's/^/  ✅ /'
    if [ "$ACTIVE_AGENTS" -gt 10 ]; then
        echo "  ... and $((ACTIVE_AGENTS - 10)) more"
    fi
fi

echo ""
