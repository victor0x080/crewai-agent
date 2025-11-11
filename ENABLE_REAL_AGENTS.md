# How to Enable REAL Python CrewAI Agents

## 🎯 Current Status

**Right now:**
- ✅ Server is running
- ✅ All services healthy
- ✅ Prompts from Supabase ✅
- 🎭 **Agents: SIMULATED** (not real Python agents)
- ❌ **Redis: DISABLED**

---

## 🔄 To Enable REAL Python Agents

You need to follow these 3 steps:

---

### Step 1: Install and Start Redis

#### Option A: Windows (using Chocolatey)
```powershell
# Install Chocolatey if you don't have it
# Then install Redis:
choco install redis-64

# Start Redis
redis-server
```

#### Option B: Windows (using Docker)
```powershell
# Install Docker Desktop, then:
docker run -d -p 6379:6379 --name redis redis:latest
```

#### Option C: WSL (Windows Subsystem for Linux)
```bash
# In WSL terminal:
sudo apt update
sudo apt install redis-server
redis-server
```

#### Verify Redis is Running:
```powershell
# Test connection
redis-cli ping
# Should return: PONG
```

---

### Step 2: Enable Redis in `.env`

Edit your `.env` file and change:

```env
# FROM:
ENABLE_REDIS=false

# TO:
ENABLE_REDIS=true

# Also verify these are set:
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
```

---

### Step 3: Start Python CrewAI Agents

#### Install Python Dependencies First:
```bash
cd "C:\Users\Administrator\Documents\KJB\Loverble_task_1\IMS\New folder\agents\crewai"

# Install required packages
pip install crewai redis python-dotenv
```

#### Start the Python Agent Service:
```bash
python CrewAIManagerService.py
```

**Expected output:**
```
[pricing-translator-manager] Starting manager service...
[pricing-translator-manager] Listening on stream:route.decisions:pricing-translator-manager...
❤️ Heartbeat
```

---

### Step 4: Restart Node.js Backend

```bash
# Stop current server (Ctrl+C)
cd "New folder"
npm start
```

**Look for this in logs:**
```
✅ AgentOrchestrator initialized with REAL CrewAI agents via Redis
🤖 Found X active Python agents: ...
   Mode: REAL Python CrewAI agents
```

---

## 🧪 Test Real vs Simulated

### Test with Simulated Agents (Current)
```bash
curl -X POST http://localhost:3002/api/process-message \
  -H "Content-Type: application/json" \
  -d '{"message": "Test query", "conversationId": "test-1"}'
```

**Response will include:**
```json
{
  "agentResults": {
    "results": [
      {
        "mode": "simulated",
        "result": {
          "output": "[SIMULATED] Analysis completed...",
          "simulated": true
        }
      }
    ]
  }
}
```

### Test with Real Agents (After enabling Redis)
```bash
# Same request
```

**Response will include:**
```json
{
  "agentResults": {
    "results": [
      {
        "mode": "real_python_crewai",
        "result": {
          "output": "Real analysis from Python CrewAI agent...",
          "simulated": false
        }
      }
    ]
  }
}
```

---

## 📊 Comparison

| Feature | Simulated Mode (Current) | Real Agent Mode |
|---------|-------------------------|-----------------|
| **Redis Required** | ❌ No | ✅ Yes |
| **Python Required** | ❌ No | ✅ Yes |
| **Agent Results** | Fake/simulated | Real AI analysis |
| **Response Time** | Fast (~1-2s) | Variable (5-30s) |
| **Setup Complexity** | Simple ✅ | More complex ⚠️ |
| **Good For** | Development/testing | Production |

---

## 🎯 Do You NEED Real Agents?

### Use **Simulated Mode** (current) if:
- ✅ Just testing the API
- ✅ Developing the frontend
- ✅ Don't have Redis/Python set up yet
- ✅ Want fast responses for prototyping

### Use **Real Agent Mode** if:
- ✅ Need actual AI analysis results
- ✅ Running in production
- ✅ Have Redis and Python infrastructure
- ✅ Quality of results matters more than speed

---

## 🔍 How to Check Current Mode

### Via Health Endpoint:
```bash
curl http://localhost:3002/api/health
```

Look for:
```json
{
  "config": {
    "redisEnabled": false  ← Simulated mode
    // OR
    "redisEnabled": true   ← Real mode (if configured)
  }
}
```

### Via Server Logs:
Look for these lines when server starts:
```
✅ AgentOrchestrator initialized with REAL CrewAI agents via Redis  ← Real mode
// OR
Redis disabled - using simulated agent execution  ← Simulated mode
```

---

## 🚀 Quick Summary

**Current Setup:**
```
✅ Prompts: FROM SUPABASE (working!)
❌ Redis: DISABLED
🎭 Agents: SIMULATED
```

**To enable real agents:**
```bash
# 1. Start Redis
redis-server

# 2. Update .env
ENABLE_REDIS=true

# 3. Start Python agents
cd agents/crewai
python CrewAIManagerService.py

# 4. Restart backend
npm start
```

**Result:**
```
✅ Prompts: FROM SUPABASE
✅ Redis: ENABLED
🤖 Agents: REAL PYTHON CREWAI
```

---

## 📝 Note

The **simulated mode works perfectly** for development and testing. You don't NEED to enable real agents unless you want actual AI analysis results.

Your system is **fully functional** right now with simulated agents! 🎉

