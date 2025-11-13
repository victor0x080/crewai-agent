# 📋 Workflow Templates Guide

## 🎯 Overview

I've created **20 production-ready workflow templates** based on your 54+ real agents. These templates define which agents get allocated for different types of queries.

---

## 🚀 **Quick Setup**

### **Step 1: Run the SQL File**

```bash
# Option 1: Via Supabase Dashboard
1. Go to Supabase Dashboard → SQL Editor
2. Copy contents of `supabase_workflow_templates.sql`
3. Click "Run"

# Option 2: Via psql (if you have direct DB access)
psql -h <your-db-host> -U postgres -d postgres -f supabase_workflow_templates.sql
```

### **Step 2: Verify Templates Were Created**

```sql
SELECT name, domain, template_schema->'agents' as agents
FROM workflow_templates
ORDER BY name;
```

You should see **20 templates**!

---

## 📊 **Template Categories**

### **1. Forecasting & Demand (2 templates)**

#### **Demand Forecasting Workflow**
- **Agents**: FQA, SDA, SSA, IRA
- **Use for**: "What is the forecast for Q3?", "Predict demand for Nike shoes"
- **Duration**: ~30 seconds

#### **Quick Forecast Q&A**
- **Agents**: FQA, ASA
- **Use for**: "When will we hit 10K sales?", "What's next month's forecast?"
- **Duration**: ~15 seconds

---

### **2. Marketing & Campaigns (3 templates)**

#### **Marketing Budget Optimization**
- **Agents**: Marketing Plan, Budget, Elasticity, Google Ads, Meta Ads
- **Use for**: "How should I allocate my $100K marketing budget?", "Optimize my ad spend"
- **Duration**: ~40 seconds

#### **Campaign Performance Analysis**
- **Agents**: Campaign-SKU Mapper, CAA, Elasticity, ASA
- **Use for**: "Why did my campaign underperform?", "What was the ROI of my promo?"
- **Duration**: ~35 seconds

#### **Multi-Platform Advertising Analysis**
- **Agents**: Google Ads, Meta Ads, TikTok, LinkedIn, Budget, ASA
- **Use for**: "Which platform has best ROI?", "Compare Google vs Meta performance"
- **Duration**: ~45 seconds

---

### **3. Inventory & Supply Chain (2 templates)**

#### **Inventory Optimization Workflow**
- **Agents**: Inventory Position, IRA, Capacity, OPT, ASA
- **Use for**: "Optimize my inventory levels", "When should I reorder?", "Stockout risk for SKU-123"
- **Duration**: ~35 seconds

#### **Supply Chain Planning Workflow**
- **Agents**: Supply Planning, Production, Procurement, Logistics, ATP-CTP
- **Use for**: "Plan production for Q3", "S&OP planning", "When can I promise delivery?"
- **Duration**: ~50 seconds

---

### **4. Scenario Analysis (2 templates)**

#### **What-If Scenario Analysis**
- **Agents**: SSA, IRA, OPT, Risk-Digital-Twin, ASA
- **Use for**: "What if we reduce prices by 10%?", "Simulate holiday demand surge"
- **Duration**: ~40 seconds

#### **Pricing Impact Analysis**
- **Agents**: Elasticity, SSA, IRA, Price-Guardrail, ASA
- **Use for**: "Impact of price increase?", "Should I discount by 15%?"
- **Duration**: ~35 seconds

---

### **5. Data Analysis (2 templates)**

#### **General Data Analysis**
- **Agents**: SDA, CAA, ASA
- **Use for**: "Analyze last quarter's performance", "Why did sales drop?"
- **Duration**: ~25 seconds

#### **Root Cause Analysis**
- **Agents**: RCA-Detective, SDA, CAA, Data-Gap, ASA
- **Use for**: "Why did KPI degrade?", "Find root cause of issue"
- **Duration**: ~40 seconds

---

### **6. Sales & Revenue (2 templates)**

#### **Sales Pipeline Forecasting**
- **Agents**: Sales Pipeline, FQA, CAA, ASA
- **Use for**: "Forecast pipeline revenue", "When will deals close?"
- **Duration**: ~30 seconds

#### **Revenue Optimization**
- **Agents**: Elasticity, Price-Guardrail, Budget, OPT, ASA
- **Use for**: "How to increase revenue?", "Maximize profitability"
- **Duration**: ~35 seconds

---

### **7. Retail Media Networks (3 templates)**

#### **Amazon RMN Campaign Optimization**
- **Agents**: Amazon-RMN, Budget, Elasticity, ASA
- **Use for**: "Optimize Amazon ads", "Improve sponsored products performance"
- **Duration**: ~30 seconds

#### **Walmart Connect Campaign Analysis**
- **Agents**: Walmart-RMN, Budget, Campaign-SKU-Mapper, ASA
- **Use for**: "Analyze Walmart advertising", "Walmart Connect ROI"
- **Duration**: ~30 seconds

#### **Multi-Retailer RMN Comparison**
- **Agents**: Amazon-RMN, Walmart-RMN, Target-RMN, Instacart-RMN, Budget, ASA
- **Use for**: "Compare Amazon vs Walmart ads", "Which retailer to invest in?"
- **Duration**: ~45 seconds

---

### **8. Governance & Policy (2 templates)**

#### **Policy Compliance Check**
- **Agents**: Price-Guardrail, Guardrail-Compliance, Constraint-Broadcast, ASA
- **Use for**: "Is this pricing allowed?", "Check compliance", "Violates policy?"
- **Duration**: ~25 seconds

#### **Policy Creation & Negotiation**
- **Agents**: Policy-Elicitation, SOP-Orchestrator, Constraint-Broadcast, ASA
- **Use for**: "Create new pricing policy", "S&OP negotiation"
- **Duration**: ~35 seconds

---

### **9. MCO (Marketing Campaign Optimization) (2 templates)**

#### **End-to-End Campaign Optimization**
- **Agents**: Ingress, Feature-Forecast, Attribution, Budget, Bid-Setter, Creative-Ops
- **Use for**: "Full campaign optimization", "Optimize bids and creatives"
- **Duration**: ~50 seconds

#### **Campaign Opportunity Scanning**
- **Agents**: Opportunity-Scanner, RCA-Detective, Budget, ASA
- **Use for**: "Find optimization opportunities", "Scan for issues"
- **Duration**: ~30 seconds

---

### **10. Quick Answers (2 templates)**

#### **Quick Question Answering**
- **Agents**: FQA, ASA
- **Use for**: "What is...?", "How many...?", Simple questions
- **Duration**: ~10 seconds

#### **Data Retrieval Query**
- **Agents**: SDA, ASA
- **Use for**: "Show me data for...", "Get sales numbers"
- **Duration**: ~10 seconds

---

## 🎯 **How Template Matching Works**

### **1. Semantic Search** (Best Match)

```
User: "What is the demand forecast for Nike Air Max in Q3?"
        ↓
TemplateEngine searches by semantic similarity
        ↓
Finds: "Demand Forecasting Workflow" (89% match)
        ↓
Allocates agents: [FQA, SDA, SSA, IRA]
```

### **2. Keyword Matching** (Fallback)

```
User: "Optimize my marketing budget"
        ↓
TemplateEngine searches by keywords
        ↓
Finds: "Marketing Budget Optimization" (contains "budget", "marketing")
        ↓
Allocates agents: [Marketing-Plan, Budget, Elasticity, Google-Ads, Meta-Ads]
```

### **3. Intent-Based** (Last Resort)

```
User: "Random query with no matching template"
        ↓
TemplateEngine uses intent: "QUESTION"
        ↓
Uses fallback template
        ↓
Allocates agents: [FQA, ASA]
```

---

## 📊 **Template Performance by Use Case**

| Use Case | Template | Agents | Time | Keywords |
|----------|----------|--------|------|----------|
| **Forecasting** | Demand Forecasting | 4 | 30s | forecast, demand, predict |
| **Marketing** | Budget Optimization | 5 | 40s | budget, campaign, ads |
| **Inventory** | Inventory Optimization | 5 | 35s | inventory, stock, reorder |
| **What-If** | Scenario Analysis | 5 | 40s | what if, simulate, test |
| **Analysis** | Root Cause | 5 | 40s | why, cause, problem |
| **Sales** | Pipeline Forecasting | 4 | 30s | pipeline, sales, revenue |
| **RMN** | Amazon RMN | 4 | 30s | amazon, sponsored |
| **Quick** | Quick Q&A | 2 | 10s | what, how, when |

---

## 🔧 **Customizing Templates**

### **Add a New Template**

```sql
INSERT INTO workflow_templates (name, description, domain, template_schema)
VALUES (
  'My Custom Workflow',
  'Description of what this does',
  'marketing',  -- or 'supply_chain', 'analytics', 'sales', etc.
  '{
    "agents": ["agent1", "agent2", "agent3"],
    "steps": [
      {"agent": "agent1", "action": "do_something", "description": "Step 1"},
      {"agent": "agent2", "action": "do_another", "description": "Step 2"}
    ],
    "parallel_execution": true,
    "timeout_ms": 30000,
    "keywords": ["keyword1", "keyword2", "keyword3"]
  }'::jsonb
);
```

### **Update Existing Template**

```sql
UPDATE workflow_templates
SET template_schema = '{
  "agents": ["new_agent_list"],
  "steps": [...]
}'::jsonb
WHERE name = 'Demand Forecasting Workflow';
```

### **Delete Template**

```sql
DELETE FROM workflow_templates
WHERE name = 'Unwanted Template';
```

---

## 🧪 **Testing Templates**

### **Test 1: Check Template Match**

```sql
-- See which template would match your query
SELECT name, description, 
       template_schema->'agents' as agents,
       template_schema->'keywords' as keywords
FROM workflow_templates
WHERE template_schema->>'keywords' LIKE '%forecast%'
ORDER BY name;
```

### **Test 2: Verify Agent IDs**

```sql
-- Make sure all agent IDs in templates exist in your agent registry
SELECT DISTINCT jsonb_array_elements_text(template_schema->'agents') as agent_id
FROM workflow_templates
ORDER BY agent_id;
```

---

## 📈 **Expected Results**

### **Before (No Templates)**

```
User: "What is the forecast for Q3?"
  ↓
AgentOrchestrator uses default intent-based agents
  ↓
Allocates: [FQA, ASA]  (basic)
  ↓
Limited insights
```

### **After (With Templates)**

```
User: "What is the forecast for Q3?"
  ↓
TemplateEngine finds "Demand Forecasting Workflow"
  ↓
Allocates: [FQA, SDA, SSA, IRA]  (comprehensive!)
  ↓
Rich insights with historical data, scenarios, and risk assessment
```

---

## ✅ **Verification Checklist**

- [ ] Run `supabase_workflow_templates.sql` in Supabase
- [ ] Verify 20 templates created: `SELECT COUNT(*) FROM workflow_templates;`
- [ ] Test a query: Send "What is the forecast?" to your backend
- [ ] Check logs: Should show "Found templates via semantic search"
- [ ] Verify agents allocated match template definition

---

## 🎉 **Summary**

You now have:
- ✅ **20 production-ready templates** covering all major use cases
- ✅ **Based on your 54+ real agents** (not generic!)
- ✅ **Semantic search enabled** (best template matching)
- ✅ **Keyword fallback** (works without pgvector)
- ✅ **Customizable** (easy to add/modify templates)
- ✅ **Ready to use** (just run the SQL file!)

**Your system will now intelligently allocate agents based on query type!** 🚀

