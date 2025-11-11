# Complete Workflow Testing Guide

## 🎯 Overview

This guide helps you test the complete workflow of your IMS Agent Backend system.

---

## 📋 Prerequisites

### 1. **Server Running**
```bash
# Make sure server is running
npm start
# Or use production script
./start-production.sh
```

### 2. **Services Available**
- ✅ Node.js Backend (port 3001)
- ✅ Supabase (for templates and prompts)
- ✅ OpenAI (for intent classification)
- ✅ Redis (optional - for real agents)

---

## 🧪 Test Options

### **Option 1: Complete Workflow Test (Recommended)**

Tests all major components automatically:

```bash
./test-workflow.sh
```

**What it tests:**
1. ✅ Health endpoint
2. ✅ Agents list endpoint
3. ✅ Intent classification (3 different queries)
4. ✅ Template discovery
5. ✅ Agent allocation
6. ✅ Execution plan generation
7. ✅ Response time performance
8. ✅ Multiple query types (5 different types)

**Output:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TEST 1: Health Check
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ PASS: Health endpoint returns healthy status
   promptService: ✅
   intentRouter: ✅
   templateEngine: ✅
   agentOrchestrator: ✅
   memoryService: ✅

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TEST 2: Agents List
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ PASS: Agents endpoint returns agents
   54 agents found

... (more tests)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 TEST SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Tests: 15
Passed: 15
Failed: 0
Success Rate: 100%
✅ All tests passed!
```

---

### **Option 2: Single Query Test**

Test a specific query:

```bash
./test-single-query.sh "What is the demand forecast for Q3 2025?"
```

**What it shows:**
- Intent classification (type, intent, confidence)
- Templates used
- Agents allocated
- Execution plan
- Full JSON response

---

### **Option 3: Intent Debug Test**

Diagnose intent classification issues:

```bash
./test-intent-debug.sh
```

**What it checks:**
- Server health
- OpenAI configuration
- Intent classification success/failure
- Possible causes of issues

---

## 🔍 Manual Testing

### **Test 1: Health Check**

```bash
curl http://localhost:3001/api/health | jq
```

**Expected:**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-05T...",
  "services": {
    "promptService": true,
    "intentRouter": true,
    "templateEngine": true,
    "agentOrchestrator": true,
    "memoryService": true
  }
}
```

---

### **Test 2: List Agents**

```bash
curl http://localhost:3001/api/agents | jq '.agents | length'
```

**Expected:** `54` (number of agents)

---

### **Test 3: Process Query**

```bash
curl -X POST http://localhost:3001/api/process-message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the demand forecast for Q3 2025?",
    "conversationId": "test-123",
    "userId": "user-1"
  }' | jq
```

**Expected:**
```json
{
  "query": "What is the demand forecast for Q3 2025?",
  "intentClassification": {
    "intent": "SIMULATION",
    "confidence": 0.9,
    ...
  },
  "templates": [...],
  "turnEnvelope": {
    "ack": "...",
    "plan": {...},
    ...
  }
}
```

---

## 📊 Test Query Examples

### **Forecasting Queries**
```bash
./test-single-query.sh "What is the demand forecast for Q3 2025?"
./test-single-query.sh "Predict sales for next quarter"
./test-single-query.sh "When will we reach 100,000 units sold?"
```

### **Marketing Queries**
```bash
./test-single-query.sh "How should I allocate my $100,000 marketing budget?"
./test-single-query.sh "Which advertising platform has the best ROI?"
./test-single-query.sh "Should I increase my Google Ads budget?"
```

### **Inventory Queries**
```bash
./test-single-query.sh "Do I have enough inventory for the holiday season?"
./test-single-query.sh "What is my inventory risk level?"
./test-single-query.sh "When should I reorder stock?"
```

### **Pricing Queries**
```bash
./test-single-query.sh "What if we reduce prices by 15%?"
./test-single-query.sh "What is the price elasticity for product X?"
./test-single-query.sh "Should we run a promotional discount?"
```

### **Sales Queries**
```bash
./test-single-query.sh "What is the revenue forecast for next quarter?"
./test-single-query.sh "How is my sales pipeline looking?"
./test-single-query.sh "What is my conversion rate?"
```

---

## ✅ What to Verify

### **1. Intent Classification**
- ✅ Confidence > 0.5 (ideally > 0.8)
- ✅ Intent is meaningful (not "GENERAL_QUERY")
- ✅ Provenance shows "OpenAI-GPT4" (not "Fallback")

### **2. Templates**
- ✅ At least 1 template found
- ✅ Templates are relevant to query
- ✅ Relevance scores are reasonable (0.5-1.0)

### **3. Agents**
- ✅ Agents are allocated (at least 1)
- ✅ Agent IDs match expected agents
- ✅ Agents match selected templates

### **4. Execution Plan**
- ✅ Declarative actions present
- ✅ Procedural tasks present
- ✅ Task dependencies are valid
- ✅ Acknowledgment message present

### **5. Performance**
- ✅ Response time < 10 seconds (ideally < 5 seconds)
- ✅ No timeouts
- ✅ No errors in response

---

## 🐛 Troubleshooting

### **Issue: Timeouts**
**Symptoms:** Intent classification timeout, confidence 0.5, fallback

**Solutions:**
1. Check server is running with latest code (5s timeout)
2. Verify OpenAI API key is valid
3. Check network connectivity
4. Increase timeout if needed (edit `src/server.js`)

### **Issue: No Templates Found**
**Symptoms:** Empty templates array

**Solutions:**
1. Verify Supabase is configured
2. Check templates exist in database
3. Verify template search is working

### **Issue: No Agents Allocated**
**Symptoms:** Empty agents array

**Solutions:**
1. Check templates include agent definitions
2. Verify agent registry is loaded
3. Check agent selection logic

### **Issue: Slow Response**
**Symptoms:** Response time > 10 seconds

**Solutions:**
1. Check OpenAI API latency
2. Check Supabase query performance
3. Verify prompts are cached (not loading from DB each time)

---

## 📈 Success Criteria

### **Minimum Requirements:**
- ✅ Health endpoint returns 200
- ✅ Agents endpoint returns agents
- ✅ Intent classification works (confidence > 0.5)
- ✅ Templates discovered
- ✅ Agents allocated
- ✅ Response time < 10 seconds

### **Optimal Performance:**
- ✅ Intent confidence > 0.8
- ✅ Response time < 5 seconds
- ✅ Multiple templates found
- ✅ Multiple agents allocated
- ✅ No timeouts or errors

---

## 🚀 Quick Start

```bash
# 1. Start server
npm start

# 2. Run complete workflow test
./test-workflow.sh

# 3. Check results
# All tests should pass ✅
```

---

## 📝 Next Steps

After testing:

1. **Review Results:** Check which tests passed/failed
2. **Check Logs:** Review server logs for any errors
3. **Verify Performance:** Ensure response times are acceptable
4. **Test Edge Cases:** Try unusual queries, long queries, etc.
5. **Production Ready:** If all tests pass, system is ready!

---

## 💡 Tips

- **Run tests regularly** to catch regressions
- **Test different query types** to ensure coverage
- **Monitor response times** for performance issues
- **Check logs** for detailed error information
- **Use debug script** if intent classification fails

Good luck with your testing! 🧪

