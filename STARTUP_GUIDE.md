# Project Startup Guide

## Quick Start

### Start Everything
```bash
./start.sh
```

This will:
1. ✅ Check prerequisites (Redis, Python 3, Node.js)
2. ✅ Setup Python virtual environment
3. ✅ Start Python agents (54 agents)
4. ✅ Start Node.js backend
5. ✅ Wait for all services to be ready
6. ✅ Show system status

### Stop Everything
```bash
./stop.sh
```

## What Gets Started

### 1. Redis Server
- **Port**: 6379 (default)
- **Purpose**: Communication between Node.js and Python agents
- **Status**: Automatically started if not running

### 2. Python Agents (54 agents)
- **Process**: `agents/start_all_agents.py`
- **Logs**: `logs/python-agents.log`
- **Error Logs**: `logs/python-agents-error.log`
- **Heartbeats**: Stored in Redis as `crewai:agent:*:heartbeat`

### 3. Node.js Backend
- **Port**: 3001 (default, configurable via `.env`)
- **Process**: `npm start`
- **Logs**: `logs/node-backend.log`
- **Error Logs**: `logs/node-backend-error.log`

## Endpoints

Once started, you can access:

- **Health Check**: `http://localhost:3001/api/health`
- **Process Query**: `http://localhost:3001/api/process-message`
- **List Agents**: `http://localhost:3001/api/agents`

## Testing

### Quick Test
```bash
# Test health
curl http://localhost:3001/api/health

# Test query
./query-detail.sh "What is the sales forecast for next quarter?"
```

### Multiple Queries
```bash
./test-queries.sh
```

## Environment Variables

Create `.env` file to customize:
```bash
PORT=3001
API_URL=http://localhost:3001
REDIS_HOST=localhost
REDIS_PORT=6379
OPENAI_API_KEY=your-key-here
SUPABASE_URL=your-url
SUPABASE_ANON_KEY=your-key
```

## Troubleshooting

### Backend Not Starting
```bash
# Check logs
tail -f logs/node-backend-error.log

# Check if port is in use
lsof -i :3001
```

### Agents Not Starting
```bash
# Check logs
tail -f logs/python-agents-error.log

# Check Redis
redis-cli ping

# Check active agents
redis-cli KEYS "crewai:agent:*:heartbeat" | wc -l
```

### Restart Everything
```bash
./stop.sh
sleep 2
./start.sh
```

## Manual Start (Alternative)

If you prefer to start services manually:

```bash
# Terminal 1: Redis
redis-server

# Terminal 2: Python Agents
cd /home/KJB
source venv/bin/activate
export API_URL=http://localhost:3001
python agents/start_all_agents.py

# Terminal 3: Node.js Backend
cd /home/KJB
npm start
```

## Process Management

### Check Running Processes
```bash
# Python agents
ps aux | grep "start_all_agents"

# Node.js backend
ps aux | grep "node.*server"

# Redis
redis-cli ping
```

### View Logs
```bash
# Tail all logs
tail -f logs/*.log

# Specific log
tail -f logs/node-backend.log
tail -f logs/python-agents.log
```

## System Requirements

- **Redis**: Redis server (port 6379)
- **Python**: Python 3.8+ with venv
- **Node.js**: Node.js 18+ (20+ recommended)
- **npm**: npm 8+

## Expected Startup Time

- **Redis**: Instant (< 1 second)
- **Python Agents**: 5-10 seconds to initialize
- **Node.js Backend**: 30-60 seconds (initialization includes Supabase connections, OpenAI API test, etc.)

**Total**: ~1-2 minutes for full startup

## Status Indicators

After running `./start.sh`, you should see:
- ✅ Redis: Running
- ✅ Python Agents: 54 active (or close to it)
- ✅ Node.js Backend: Running on port 3001

If any service shows ❌ or ⚠️, check the logs for details.

