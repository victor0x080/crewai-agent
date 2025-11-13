# 🧪 Testing Guide - Complete Flow

## Overview

Test the complete backend flow from business query → intent classification → template discovery → agent allocation.

---

## 🚀 **Prerequisites**

### **1. Setup Supabase Templates**

```bash
# Run the SQL file in Supabase Dashboard → SQL Editor
# File: supabase_workflow_templates.sql
```

### **2. Start the Backend**

```powershell
cd "New folder"
npm start
```

### **3. (Optional) Start Real Agents**

```powershell
# For REAL agent execution (not simulated):

# Terminal 1: Start Redis
.\start-redis.ps1

# Terminal 2: Start Python Agents
python agents\start_all_agents.py

# Terminal 3: Start Node.js Backend
npm start
```

---

## 📊 **Test Options**

### **Option 1: Full Test Suite** (Recommended)

Tests 10 different business scenarios automatically.

```powershell
.\test-complete-flow.ps1
```

**What it tests**:
1. Forecasting queries
2. Marketing budget questions
3. Inventory optimization
4. What-if scenarios
5. Campaign analysis
6. Sales pipeline
7. Amazon RMN
8. Root cause analysis
9. Quick questions
10. Multi-platform comparison

**Output**:
```
============================================
🧪 Complete Backend Flow Test
============================================

📡 Checking backend health...
   ✅ Backend is healthy

🚀 Starting Tests
============================================

─────────────────────────────────────────
🔍 Test: Forecasting Query
   Query: "What is the demand forecast for Nike Air Max shoes in Q3 2025?"

   ⏱️  Response Time: 2340ms

   📊 Results:
      Intent Classified: forecasting
      Agents Allocated: 4
      Execution Mode: real_python_crewai

   🤖 Agents Used:
      ✅ Forecast Q&A Agent (fqa)
      ✅ Semantic Data Agent (sda)
      ✅ Scenario Simulator Agent (ssa)
      ✅ Inventory Risk Agent (ira)

   ✓ Validation:
      ✅ Agent 'fqa' allocated
      ✅ Agent 'sda' allocated
      ✅ Agent 'ssa' allocated
      ✅ Agent 'ira' allocated
      ✅ Acknowledgment present
      ✅ Execution plan generated

   ✅ TEST PASSED

... (9 more tests)

============================================
📊 Test Summary
============================================

Total Tests:        10
Passed:            10
Failed:            0
Avg Response Time: 1850ms
Total Agents Used: 42

Detailed Results:

Test Name                     | Agents | Mode              | Time    | Status
─────────────────────────────────────────────────────────────────────────────
Forecasting Query            | 4/4    | real_python_crewai | 2340ms  | ✅
Marketing Budget Query       | 5/5    | real_python_crewai | 3120ms  | ✅
Inventory Query              | 5/5    | real_python_crewai | 2890ms  | ✅
...

✅ ALL TESTS PASSED!
```

---

### **Option 2: Single Query Test**

Test one specific query at a time.

```powershell
# Default query
.\test-single-query.ps1

# Custom query
.\test-single-query.ps1 -Query "What is my sales forecast for next quarter?"

# With custom URL
.\test-single-query.ps1 -Query "Optimize my marketing budget" -BaseUrl "http://localhost:3002"
```

**Output**:
```
🔍 Testing Query: "What is the demand forecast for Q3 2025?"

📤 Sending request...
✅ Response received in 1850ms

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 RESULTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 Intent Classification:
   Intent: forecasting

🤖 Agents Allocated: 4
   ✅ REAL - Forecast Q&A Agent
       ID: fqa
       Role: Generate demand forecast with confidence intervals
   ✅ REAL - Semantic Data Agent
       ID: sda
       Role: Query historical sales and demand data
   ✅ REAL - Scenario Simulator Agent
       ID: ssa
       Role: Simulate optimistic/baseline/pessimistic scenarios
   ✅ REAL - Inventory Risk Agent
       ID: ira
       Role: Calculate stockout and overstock probabilities

💬 Acknowledgment:
   I've analyzed the demand forecast for Q3 2025 using 4 specialized agents.

📋 Execution Plan:
   Declarative:
      • Q3 2025 forecast: 45,000 units
      • Confidence interval: [42,000 - 48,000]
      • Growth vs Q3 2024: +12%
   Procedural:
      • Monitor inventory levels weekly
      • Place reorder when stock reaches 20,000 units

✅ Test completed successfully!
```

---

### **Option 3: Manual cURL Test**

```bash
# Test forecasting query
curl -X POST http://localhost:3002/api/process-message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the demand forecast for Q3?",
    "conversationId": "test-123",
    "userId": "user-001"
  }'

# Test marketing query
curl -X POST http://localhost:3002/api/process-message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How should I allocate my $100K marketing budget?",
    "conversationId": "test-456",
    "userId": "user-001"
  }'
```

---

## 🎯 **Test Business Queries**

### **Forecasting**
```
"What is the demand forecast for Nike Air Max shoes in Q3 2025?"
"When will we reach 100,000 units sold?"
"Predict sales for next quarter"
```

### **Marketing**
```
"How should I allocate my $100,000 marketing budget across Google Ads and Meta?"
"Which advertising platform has the best ROI?"
"Why did my Black Friday campaign underperform?"
```

### **Inventory**
```
"Do I have enough inventory for the holiday season?"
"When should I reorder SKU-12345?"
"Optimize my inventory levels"
```

### **Scenarios**
```
"What if we reduce prices by 15%?"
"Simulate demand if we launch 3 new products"
"What happens if competitor increases prices?"
```

### **Sales**
```
"What is my sales pipeline forecast?"
"How to increase revenue by 20%?"
"When will deals close?"
```

### **Analysis**
```
"Why did revenue drop 20% last month?"
"Analyze Q4 performance"
"Find root cause of KPI degradation"
```

---

## ✅ **What to Check**

### **1. Intent Classification**
```
Query: "What is the forecast for Q3?"
Expected: intent = "forecasting" or "QUESTION"
```

### **2. Template Matching**
```
Query: "What is the forecast for Q3?"
Expected Template: "Demand Forecasting Workflow" or similar
```

### **3. Agent Allocation**
```
Query: "What is the forecast for Q3?"
Expected Agents: ["fqa", "sda", "ssa", "ira"] or subset
Minimum: At least FQA (Forecast Q&A Agent)
```

### **4. Execution Mode**
```
With Redis + Python: mode = "real_python_crewai" ✅
Without Redis: mode = "simulated" 🎭
```

### **5. Response Structure**
```json
{
  "turnId": "...",
  "conversationId": "...",
  "intent": "forecasting",
  "ack": "...",
  "plan": {
    "declarative": [...],
    "procedural": [...]
  },
  "memory": {...},
  "meta": {
    "agents": [
      {
        "agentId": "fqa",
        "agentName": "Forecast Q&A Agent",
        "mode": "real_python_crewai"
      }
    ]
  }
}
```

---

## 🐛 **Troubleshooting**

### **Issue 1: "Backend not reachable"**

```powershell
# Check if backend is running
Get-Process node

# If not, start it
npm start
```

### **Issue 2: "Using SIMULATED agents"**

**Cause**: Redis or Python agents not running

**Solution**:
```powershell
# Start Redis
.\start-redis.ps1

# Start Python agents
python agents\start_all_agents.py

# Restart backend
npm start
```

### **Issue 3: "No templates found"**

**Cause**: Supabase templates not loaded

**Solution**:
```bash
# Run in Supabase Dashboard → SQL Editor
# File: supabase_workflow_templates.sql

# Verify templates
SELECT COUNT(*) FROM workflow_templates;
-- Should return: 20
```

### **Issue 4: "Agent not allocated"**

**Cause**: Agent ID mismatch between template and registry

**Solution**:
```javascript
// Check agent registry
// File: src/agents/registry.js

// Ensure agent IDs match template agent IDs
// Example: "fqa", "sda", "ssa", etc. (lowercase, hyphenated)
```

### **Issue 5: "Timeout"**

**Cause**: Python agents too slow or crashed

**Solution**:
```powershell
# Check Python agent logs
Get-Content logs\python-agents.log -Tail 50

# Restart Python agents
python agents\start_all_agents.py
```

---

## 📊 **Expected Results**

### **Test Scenario 1: Forecasting**
```
Query: "What is the demand forecast for Q3?"
Intent: forecasting
Agents: 2-4 agents (FQA, SDA, SSA, IRA)
Time: 2-5 seconds
Mode: real_python_crewai (with Redis) or simulated
```

### **Test Scenario 2: Marketing**
```
Query: "Optimize my marketing budget"
Intent: marketing / decision
Agents: 3-5 agents (Marketing-Plan, Budget, Elasticity, Platform agents)
Time: 3-6 seconds
Mode: real_python_crewai or simulated
```

### **Test Scenario 3: Quick Question**
```
Query: "What was revenue last quarter?"
Intent: QUESTION / general
Agents: 2 agents (SDA, ASA)
Time: 1-2 seconds
Mode: real_python_crewai or simulated
```

---

## 🎉 **Success Criteria**

- ✅ Backend responds within 5 seconds
- ✅ Intent correctly classified
- ✅ At least 2 agents allocated
- ✅ Response includes `ack`, `plan`, and `meta.agents`
- ✅ Agent mode shows (real or simulated)
- ✅ No errors in console

---

## 📝 **Test Checklist**

```
Prerequisites:
[ ] Supabase templates loaded (20 templates)
[ ] Backend running (port 3002)
[ ] .env file configured (OpenAI, Supabase keys)
[ ] (Optional) Redis running
[ ] (Optional) Python agents running

Run Tests:
[ ] Run full test suite: .\test-complete-flow.ps1
[ ] All 10 tests passed
[ ] Check agent allocation for each test
[ ] Verify execution mode (real or simulated)

Validate:
[ ] Intent classification working
[ ] Template discovery working
[ ] Agent allocation working
[ ] Response structure correct
[ ] Performance acceptable (<5s)
```

---

**You're now ready to test the complete flow!** 🚀

Run: `.\test-complete-flow.ps1` to start testing!

