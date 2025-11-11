# Expected Result Format - Complete Guide

## 🎯 Overview

When you send a query to the system, here's what you should expect as a result.

---

## 📊 Complete Workflow

```
User Query
    ↓
1. Intent Classification (OpenAI GPT-4)
    ↓
2. Memory Retrieval (Context from previous conversations)
    ↓
3. Template Discovery (Find relevant workflows)
    ↓
4. Agent Selection (Choose agents based on templates)
    ↓
5. Build Execution Plan (Declarative + Procedural tasks)
    ↓
6. Immediate Response (Sent to user in 1-5 seconds)
    ↓
7. Background Processing (Agents execute in background)
```

---

## 📋 Expected Response Structure

### **Complete Response Format**

```json
{
  "query": "What is the demand forecast for Q3 2025?",
  "intentClassification": {
    "type": "market-analysis",
    "intent": "SIMULATION",
    "confidence": 0.9,
    "explanation": "Classified as SIMULATION with 90% confidence",
    "keywords": ["demand forecast", "Q3 2025"],
    "entities": {
      "period": "Q3 2025"
    },
    "category": "market_analysis"
  },
  "conversationalResponse": "```json\n{...}\n```",
  "response": "```json\n{...}\n```",
  "turnEnvelope": {
    "ack": "I'm analyzing your simulation query...",
    "plan": {
      "declarative": [...],
      "procedural": [...]
    },
    "ask": [],
    "memory": {...},
    "delta": null,
    "decisions": [],
    "meta": {...}
  },
  "processedAt": "2025-11-05T14:03:23.783Z",
  "requestId": "req-1762351400830-gkyvnu",
  "conversationId": "test-20251105140320",
  "templates": [...]
}
```

---

## 🔍 Detailed Breakdown

### **1. Query**
**What:** Original user query  
**Format:** `string`  
**Example:** `"What is the demand forecast for Q3 2025?"`

---

### **2. Intent Classification**
**What:** How the system understood your query

**Structure:**
```json
{
  "type": "market-analysis",           // Domain category
  "intent": "SIMULATION",              // Intent type
  "confidence": 0.9,                    // 0.0 - 1.0 (90% confident)
  "explanation": "Classified as...",   // Human-readable explanation
  "keywords": ["demand forecast", "Q3 2025"],
  "entities": {
    "period": "Q3 2025"                // Extracted entities
  },
  "category": "market_analysis"
}
```

**Quality Indicators:**
- ✅ **Good:** Confidence > 0.8, Provenance = "OpenAI-GPT4"
- ⚠️ **Acceptable:** Confidence 0.6-0.8, Provenance = "OpenAI-GPT4"
- ❌ **Poor:** Confidence < 0.6, Provenance = "Fallback"

---

### **3. Templates**
**What:** Workflow templates matched to your query

**Structure:**
```json
[
  {
    "id": "9e9f6951-e738-47e6-a745-c37d526fbe9d",
    "name": "Demand Forecasting Workflow",
    "relevance": 0.6                      // How well it matches (0.0 - 1.0)
  },
  ...
]
```

**Expected:**
- ✅ **Good:** 2-5 templates, relevance > 0.6
- ⚠️ **Acceptable:** 1-2 templates, relevance > 0.5
- ❌ **Poor:** 0 templates or all relevance < 0.5

---

### **4. Turn Envelope** (ACT-R Compatible Format)

#### **4.1. Acknowledgment (`ack`)**
**What:** Confirmation message  
**Format:** `string`  
**Example:** `"I'm analyzing your simulation query using the Demand Forecasting Workflow, Quick Forecast Q&A..."`

---

#### **4.2. Execution Plan (`plan`)**

**Declarative Actions** (What needs to be done):
```json
[
  {
    "action": "execute_template_9e9f6951-e738-47e6-a745-c37d526fbe9d",
    "templateId": "9e9f6951-e738-47e6-a745-c37d526fbe9d",
    "templateName": "Demand Forecasting Workflow",
    "domain": "supply_chain",
    "relevance": 0.6,
    "direction": "user_directed"
  },
  ...
]
```

**Procedural Tasks** (How it will be done):
```json
[
  {
    "id": "task-1762351403782-0",
    "title": "Activate fqa for analysis",
    "service": "fqa",
    "capability": "general_analysis",
    "direction": "system_directed",
    "deps": []                              // Dependencies (empty = can start immediately)
  },
  {
    "id": "task-1762351403782-1",
    "title": "Activate sda for analysis",
    "service": "sda",
    "capability": "general_analysis",
    "direction": "system_directed",
    "deps": ["task-1762351403782-0"]      // Must wait for task-0 to complete
  },
  ...
]
```

**Expected:**
- ✅ **Good:** Multiple declarative actions, procedural tasks with proper dependencies
- ⚠️ **Acceptable:** At least 1 declarative action, some procedural tasks
- ❌ **Poor:** No plan or empty plan

---

#### **4.3. Clarification Questions (`ask`)**
**What:** Questions if system needs clarification

**Structure:**
```json
[
  {
    "id": "clarify-1762347278377",
    "question": "To provide the best analysis, could you clarify...",
    "reason": "low_confidence",
    "confidence": 0.5
  }
]
```

**Expected:**
- ✅ **Good:** Empty array (no questions needed - high confidence)
- ⚠️ **Acceptable:** 1-2 clarifying questions
- ❌ **Poor:** Many questions (system uncertain)

---

#### **4.4. Memory Context (`memory`)**
**What:** Conversation history and context

**Structure:**
```json
{
  "workingMemory": [],
  "retrieved": 0,
  "conversationTurns": 0
}
```

**Expected:**
- ✅ **Good:** Some retrieved context (if not first conversation)
- ⚠️ **Acceptable:** Empty for new conversations
- ❌ **Poor:** N/A (always acceptable)

---

#### **4.5. Metadata (`meta`)**
**What:** Processing information

**Structure:**
```json
{
  "concepts": ["SIMULATION", "demand forecast", "Q3 2025"],
  "provenance": "OpenAI-GPT4",              // "OpenAI-GPT4" or "Fallback"
  "processingMode": "immediate_response",
  "templatesUsed": ["Demand Forecasting Workflow", ...]
}
```

**Expected:**
- ✅ **Good:** Provenance = "OpenAI-GPT4", concepts extracted
- ⚠️ **Acceptable:** Provenance = "OpenAI-GPT4", some concepts
- ❌ **Poor:** Provenance = "Fallback"

---

### **5. Metadata Fields**

**`processedAt`:** Timestamp when response was created  
**`requestId`:** Unique identifier for this request  
**`conversationId`:** Unique identifier for this conversation

---

## 🎯 Expected Quality Metrics

### **High Quality Response (Ideal)**
- ✅ Intent confidence: **> 0.8** (80%+)
- ✅ Provenance: **"OpenAI-GPT4"** (not fallback)
- ✅ Templates found: **2-5 templates**
- ✅ Templates relevance: **> 0.6**
- ✅ Agents allocated: **3-9 agents**
- ✅ Response time: **< 5 seconds**
- ✅ Clarification questions: **0** (high confidence)
- ✅ Execution plan: **Complete** (declarative + procedural)

### **Acceptable Response**
- ✅ Intent confidence: **0.6-0.8**
- ✅ Provenance: **"OpenAI-GPT4"**
- ✅ Templates found: **1-2 templates**
- ✅ Response time: **< 10 seconds**
- ✅ Clarification questions: **0-1**

### **Poor Response (Needs Attention)**
- ❌ Intent confidence: **< 0.6**
- ❌ Provenance: **"Fallback"**
- ❌ Templates found: **0**
- ❌ Response time: **> 10 seconds**
- ❌ Many clarification questions

---

## 📊 Example: Good Response

**Query:** `"What is the demand forecast for Q3 2025?"`

**Result:**
```json
{
  "query": "What is the demand forecast for Q3 2025?",
  "intentClassification": {
    "intent": "SIMULATION",
    "confidence": 0.9,                    ← ✅ High confidence
    "provenance": "OpenAI-GPT4"          ← ✅ Real AI
  },
  "templates": [
    {"name": "Demand Forecasting Workflow", "relevance": 0.6},
    {"name": "Quick Forecast Q&A", "relevance": 0.6}
  ],                                      ← ✅ Multiple templates
  "turnEnvelope": {
    "ack": "I'm analyzing...",
    "plan": {
      "declarative": [4 actions],         ← ✅ Complete plan
      "procedural": [15 tasks]            ← ✅ Agent tasks
    },
    "ask": [],                            ← ✅ No questions needed
    "meta": {
      "provenance": "OpenAI-GPT4",        ← ✅ Real AI
      "concepts": ["SIMULATION", "demand forecast", "Q3 2025"]
    }
  },
  "processedAt": "2025-11-05T14:03:23.783Z"
}
```

**Response Time:** 3026ms (3 seconds) ← ✅ Fast

---

## 🔄 What Happens Next

### **Immediate (Synchronous)**
1. ✅ Response sent to user (1-5 seconds)
2. ✅ User sees acknowledgment and plan
3. ✅ System ready for next query

### **Background (Asynchronous)**
1. 🔄 Agents execute tasks (5-30 seconds)
2. 🔄 Results synthesized
3. 🔄 Results stored in memory
4. 🔄 (Future) WebSocket/SSE updates to frontend

---

## 📈 Response Time Expectations

| Component | Expected Time |
|-----------|---------------|
| Intent Classification | 2-3 seconds |
| Template Discovery | < 100ms |
| Agent Selection | < 50ms |
| Plan Building | < 50ms |
| **Total Response** | **2-5 seconds** |

---

## ✅ Success Criteria

### **Minimum Requirements:**
- ✅ HTTP 200 status
- ✅ Intent classification present
- ✅ At least 1 template found
- ✅ Execution plan generated
- ✅ Response time < 10 seconds

### **Optimal Performance:**
- ✅ Intent confidence > 0.8
- ✅ 2-5 templates found
- ✅ 3-9 agents allocated
- ✅ Response time < 5 seconds
- ✅ No clarification questions needed
- ✅ Provenance = "OpenAI-GPT4"

---

## 🎯 Summary

**When you send a query, you get:**

1. **Fast Response** (2-5 seconds)
   - Intent classification
   - Templates matched
   - Agents selected
   - Execution plan

2. **Structured Format** (ACT-R compatible)
   - Acknowledgment
   - Declarative plan (what)
   - Procedural plan (how)
   - Memory context
   - Metadata

3. **Background Processing**
   - Agents execute tasks
   - Results synthesized
   - Stored for future context

**The system is designed to give you immediate feedback while processing in the background!**

