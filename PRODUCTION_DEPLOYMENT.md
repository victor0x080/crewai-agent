# Production Deployment Guide - REAL Agents & Redis

## 🎯 Goal

Configure the IMS Agent Backend to use **REAL Python CrewAI agents** via **Redis** in production mode.

---

## 🚀 Quick Start (Automated)

### Option 1: All-in-One Script (Easiest)

```powershell
.\start-production.ps1
```

This will:
1. ✅ Check prerequisites (Redis, Python, Node.js)
2. ✅ Start Redis on port 6379
3. ✅ Install Python dependencies
4. ✅ Start Python CrewAI agents in background
5. ✅ Start Node.js backend with real agents enabled

---

## 📋 Manual Setup (Step-by-Step)

### Step 1: Update `.env` File

**Edit `.env` and change:**

```env
# FROM (Development/Simulated):
ENABLE_REDIS=false

# TO (Production/Real):
ENABLE_REDIS=true
```

**Or simply delete this line** - Redis is now enabled by default!

---

### Step 2: Start Redis

```powershell
# Option A: Use helper script
.\start-redis.ps1

# Option B: Manual start
redis-server

# Verify
redis-cli ping  # Should return: PONG
```

---

### Step 3: Start Python CrewAI Agents

```powershell
# Option A: Use helper script
.\start-python-agents.ps1

# Option B: Manual start
cd agents\crewai
pip install crewai redis python-dotenv requests
python CrewAIManagerService.py
```

**Expected output:**
```
[pricing-translator-manager] Starting manager service...
[pricing-translator-manager] Created consumer group: translator
[pricing-translator-manager] Listening on stream:route.decisions:...
❤️ Heartbeat
```

---

### Step 4: Start Node.js Backend

```powershell
cd "New folder"
npm start
```

**Look for these logs:**
```
✅ AgentOrchestrator initialized with REAL CrewAI agents via Redis
🤖 Found X active Python agents: pricing-translator-manager, ...
   Mode: REAL Python CrewAI agents  ← SUCCESS!
🔗 Redis: ✅ Enabled
🚀 IMS Agent Backend running on port 3002
```

---

## ✅ Verification

### 1. Check All Services Running

```powershell
# Check Redis
redis-cli ping  # Should return: PONG

# Check Node.js
Invoke-WebRequest http://localhost:3002/api/health

# Check Python agents (look at logs)
Get-Content agents\crewai\*.log
```

### 2. Test Real Agent Execution

```powershell
# Send a test request
$body = @{
    message = "What are the Q4 market trends for electric cars?"
    conversationId = "test-production-123"
    context = @{
        userId = "test-user"
        tenantId = "production"
    }
} | ConvertTo-Json

Invoke-WebRequest -Uri http://localhost:3002/api/process-message `
    -Method POST `
    -ContentType "application/json" `
    -Body $body
```

**In the response, look for:**
```json
{
  "agentResults": {
    "results": [
      {
        "mode": "real_python_crewai",  ← REAL agents!
        "agentName": "Semantic Data Agent",
        "success": true,
        "result": {
          "output": "Real analysis from Python...",
          "simulated": false  ← NOT simulated!
        }
      }
    ]
  }
}
```

---

## 🏗️ Production Architecture

```
┌─────────────────────────────────────────────────┐
│         Node.js Backend (Port 3002)             │
│                                                 │
│  Services:                                      │
│  - PromptService → Supabase (ai_prompts)       │
│  - IntentRouter → OpenAI GPT-4                 │
│  - AgentOrchestrator → Redis Bridge            │
│  - CrewAIBridgeService → Redis Streams         │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│         Redis Server (Port 6379)                │
│                                                 │
│  Streams:                                       │
│  - stream:crewai:tasks:*        (Node → Python)│
│  - stream:crewai:responses      (Python → Node)│
│                                                 │
│  Keys:                                          │
│  - crewai:agent:*:heartbeat     (Agent status) │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│      Python CrewAI Agents (Background)          │
│                                                 │
│  Agents:                                        │
│  - 54 agents registered                         │
│  - Listening on Redis Streams                   │
│  - Executing real AI tasks                      │
│  - Publishing results back                      │
└─────────────────────────────────────────────────┘
```

---

## 📊 Configuration Comparison

| Setting | Development | Production |
|---------|-------------|------------|
| **ENABLE_REDIS** | `false` | `true` |
| **Agent Mode** | Simulated | Real Python |
| **Redis Required** | ❌ No | ✅ Yes |
| **Python Required** | ❌ No | ✅ Yes |
| **Response Quality** | Fake data | Real AI analysis |
| **Setup Complexity** | Simple | More complex |

---

## 🔧 Troubleshooting

### Redis not connecting

**Symptoms:**
```
Redis disabled - using simulated agent execution
```

**Solutions:**
1. Check Redis is running: `redis-cli ping`
2. Check `.env` has `ENABLE_REDIS=true` (or remove the line entirely)
3. Restart backend: `npm start`

### No Python agents found

**Symptoms:**
```
⚠️ No Python agents currently active - will use simulated execution
```

**Solutions:**
1. Check Python agent process is running
2. Check Redis connection from Python: `redis-cli KEYS "crewai:agent:*"`
3. Check Python agent logs for errors

### Agents timeout

**Symptoms:**
```
Agent execution timeout after 30000ms
```

**Solutions:**
1. Increase timeout in `.env`: `MAX_AGENT_TIMEOUT_MS=60000`
2. Check Python agents are healthy (look at heartbeats)
3. Check Redis latency: `redis-cli --latency`

---

## 📝 Environment Variables for Production

**Minimal (Simulated mode):**
```env
PORT=3002
OPENAI_API_KEY=your-key
SUPABASE_URL=your-url
SUPABASE_ANON_KEY=your-key
ENABLE_REDIS=false  # or omit
```

**Full (Real agents mode):**
```env
PORT=3002
NODE_ENV=production

# OpenAI (REQUIRED)
OPENAI_API_KEY=your-key
OPENAI_MODEL=gpt-4-turbo-preview

# Supabase (REQUIRED)
SUPABASE_URL=your-url
SUPABASE_ANON_KEY=your-key
SUPABASE_SERVICE_ROLE_KEY=your-service-key

# Redis (REQUIRED for real agents)
REDIS_HOST=localhost
REDIS_PORT=6379
ENABLE_REDIS=true

# Agent Configuration
MAX_AGENT_TIMEOUT_MS=30000
ENABLE_BACKGROUND_PROCESSING=true
LOG_LEVEL=info
```

---

## 🎯 Quick Commands

### Start Everything
```powershell
.\start-production.ps1
```

### Stop Everything
```powershell
.\stop-all.ps1
```

### Check Status
```powershell
# Redis
redis-cli ping

# Backend health
Invoke-WebRequest http://localhost:3002/api/health

# Agent list
Invoke-WebRequest http://localhost:3002/api/agents
```

### View Logs
```powershell
# Node.js logs (console)
# Python agent logs
Get-Content logs\python-agents.log

# Redis logs
redis-cli MONITOR
```

---

## 🚀 Production Checklist

Before deploying to production:

- [ ] ✅ Redis installed and running
- [ ] ✅ Python 3.8+ installed
- [ ] ✅ Python dependencies installed (`pip install -r requirements.txt`)
- [ ] ✅ `.env` configured with production credentials
- [ ] ✅ `ENABLE_REDIS=true` in `.env`
- [ ] ✅ Supabase prompts installed (run `supabase_setup_minimal.sql`)
- [ ] ✅ Test with real request to verify agents are working
- [ ] ✅ Monitor logs for "Mode: REAL Python CrewAI agents"
- [ ] ✅ Set up process manager (PM2) for Node.js
- [ ] ✅ Set up systemd/supervisor for Python agents (Linux)
- [ ] ✅ Configure firewall rules if needed
- [ ] ✅ Set up monitoring/alerting
- [ ] ✅ Configure log rotation

---

## 🔄 Process Management (Advanced)

### Using PM2 for Node.js (Recommended for production)

```bash
# Install PM2
npm install -g pm2

# Start backend with PM2
pm2 start src/server.js --name ims-backend

# View logs
pm2 logs ims-backend

# Restart
pm2 restart ims-backend

# Auto-start on system boot
pm2 startup
pm2 save
```

### Using systemd for Python agents (Linux)

Create `/etc/systemd/system/ims-agents.service`:

```ini
[Unit]
Description=IMS CrewAI Agents
After=redis.service

[Service]
Type=simple
User=ims
WorkingDirectory=/path/to/New folder/agents/crewai
ExecStart=/usr/bin/python3 CrewAIManagerService.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl enable ims-agents
sudo systemctl start ims-agents
sudo systemctl status ims-agents
```

---

## 🎉 Summary

**Current Status:**
- ✅ Code: Ready for production
- ✅ Config: Redis enabled by default
- ✅ Scripts: Created startup/shutdown scripts
- ⚠️ Deployment: Needs Redis + Python running

**To go production:**
1. Run `.\start-production.ps1`
2. Verify logs show "REAL Python CrewAI agents"
3. Test with actual request
4. Monitor performance

**Your system is now configured for REAL agent execution!** 🚀

