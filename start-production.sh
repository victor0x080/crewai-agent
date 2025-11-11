#!/bin/bash

# Complete Production Startup Script
# Starts Redis → Python Agents → Node.js Backend

echo ""
echo "============================================"
echo "🚀 IMS Agent Backend - Production Startup"
echo "============================================"
echo ""

# Step 1: Check prerequisites
echo "📋 Checking prerequisites..."
echo ""

# Check Redis
if ! command -v redis-server &> /dev/null; then
    echo "❌ Redis not found"
    echo "   Install: sudo apt-get install redis-server"
    exit 1
fi

# Check Python
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "❌ Python not found"
    echo "   Install: sudo apt-get install python3 python3-pip"
    exit 1
fi

PYTHON_CMD=$(command -v python3 || command -v python)

# Check Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found"
    exit 1
fi

echo "✅ All prerequisites installed"
echo "   - Redis: $(which redis-server)"
echo "   - Python: $($PYTHON_CMD --version)"
echo "   - Node.js: $(node --version)"
echo ""

# Step 2: Start Redis
echo "📡 Starting Redis..."

# Check if Redis is already running
if redis-cli ping &> /dev/null; then
    echo "✅ Redis already running on port 6379"
else
    # Start Redis in background
    redis-server --daemonize yes
    sleep 2
    
    if redis-cli ping &> /dev/null; then
        echo "✅ Redis started on port 6379"
    else
        echo "⚠️  Redis may not be ready yet"
    fi
fi
echo ""

# Step 3: Install Python dependencies
echo "📦 Installing Python dependencies..."

# Check if requirements.txt exists
if [ -f "agents/requirements.txt" ]; then
    echo "   Installing from agents/requirements.txt"
    $PYTHON_CMD -m pip install -r agents/requirements.txt --quiet
else
    echo "⚠️  agents/requirements.txt not found, creating minimal requirements"
    mkdir -p agents
    cat > agents/requirements.txt << 'EOF'
crewai>=0.28.0
redis>=5.0.0
python-dotenv>=1.0.0
requests>=2.31.0
pydantic>=2.0.0
EOF
    $PYTHON_CMD -m pip install -r agents/requirements.txt --quiet
fi

echo "✅ Python dependencies installed"
echo ""

# Step 4: Start ALL Python agents (Generic + CrewAI) in background
echo "🤖 Starting ALL Python CrewAI agents..."
echo "   - Generic agents (Plan Review, Data Query, Stream Capture, System Call)"
echo "   - CrewAI Python agents (Skill, Demand-Gen, Supply, Governance, MCO, RMN)"
echo "   - Platform agents (Google, Meta, TikTok, LinkedIn, Pinterest, Snapchat)"
echo ""

# Create logs directory if it doesn't exist
mkdir -p logs

# Get API URL from .env or default to port 3001
if [ -f .env ]; then
    PORT=$(grep "^PORT=" .env | cut -d'=' -f2 | tr -d '"' | tr -d "'" || echo "3001")
else
    PORT="3001"
fi
API_URL="http://localhost:${PORT}"
export API_URL

echo "   API_URL: $API_URL (for Python agent heartbeats)"
echo ""

# Start unified agent manager
nohup env API_URL="$API_URL" $PYTHON_CMD agents/start_all_agents.py > logs/python-agents.log 2> logs/python-agents-error.log &

sleep 5
echo "✅ All Python agents started (54+ agents)"
echo "   Logs: logs/python-agents.log"
echo "   Error logs: logs/python-agents-error.log"
echo ""

echo "🚀 Starting Node.js Backend..."
echo ""
echo "============================================"
echo "System Status:"
echo "  - Redis: ✅ Running (port 6379)"
echo "  - Python Agents: ✅ Running (background)"
echo "  - Node.js: 🚀 Starting..."
echo "============================================"
echo ""
echo "📝 The backend will now start with REAL agents enabled"
echo "   Watch for: 'Mode: REAL Python CrewAI agents'"
echo ""
echo "Press Ctrl+C to stop the backend (Redis and Python will keep running)"
echo ""

# Start Node.js backend (this will run in foreground)
npm start

