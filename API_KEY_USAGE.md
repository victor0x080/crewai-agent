# OpenAI API Key Usage in Agents

## 📁 Storage Location

**File:** `.env` (project root)  
**Variable:** `OPENAI_API_KEY`  
**Value:** `sk-proj-WcTwqCCqjkwVan4E_NVLXqAk_I8...`

## 🔧 Where It's Used

### 1. CrewAI Agents (Automatic - No Explicit Code)

**Files:**
- `agents/crewai_python/agents/skill_agents.py`
- `agents/crewai_python/agents/mco_agents.py`
- `agents/crewai_python/agents/rmn_agents.py`
- `agents/crewai_python/agents/extended_skill_agents.py`
- All other agent definition files

**How it works:**
- CrewAI framework **automatically reads** `OPENAI_API_KEY` from environment
- No explicit API key configuration needed in agent code
- Example:
  ```python
  from crewai import Agent
  agent = Agent(
      role='Forecast Specialist',
      goal='Generate forecasts',
      # No API key needed - CrewAI reads OPENAI_API_KEY automatically!
  )
  ```

### 2. Direct Usage (Explicit)

**File:** `agents/crewai_python/plan_monitoring_agents.py`  
**Line 34:**
```python
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
```
**Used for:** OpenAI embeddings API calls (lines 62, 128, 195)

### 3. Factory Agents

**File:** `agents/crewai_python/factory/agent_factory.py`  
**Line 65:**
```python
self.llm_client = llm_client or openai.OpenAI()
# Reads OPENAI_API_KEY from environment automatically
```

## 🔄 How Environment Variables Are Loaded

### `start.sh` Script
- Lines 24-45: Loads `.env` file and exports variables
- All child processes inherit these environment variables
- Agents started by `start_all_agents.py` receive `OPENAI_API_KEY` automatically

### `start_all_agents.py`
- Line 226: `env = os.environ.copy()` - Copies parent's environment
- Line 235: Passes `env` to child processes
- Agents inherit `OPENAI_API_KEY` from parent process

## ⚠️ Current Issue

**Problem:** OpenAI quota exceeded (429 errors)  
**Cause:** API key is valid but quota limit exceeded  
**Solution:** Upgrade OpenAI plan or add credits

## ✅ Verification

To check if API key is loaded:
```bash
# Check environment
echo $OPENAI_API_KEY

# Check in Python
python3 -c "import os; print(os.getenv('OPENAI_API_KEY', 'NOT SET'))"
```

## 🔍 Key Points

1. **No explicit API key in agent code** - CrewAI handles it automatically
2. **Environment variable must be set** - From `.env` file via `start.sh`
3. **All agents use same key** - Shared via environment
4. **Quota errors = billing issue** - Not a code configuration issue
