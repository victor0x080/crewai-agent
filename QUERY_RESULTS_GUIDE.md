# Query Results Documentation

## Overview

This document explains the query result structure and how to interpret the responses from the IMS Agent Backend.

## Query Endpoint

**POST** `/api/process-message`

### Request Format
```json
{
  "message": "Your query here",
  "conversationId": "unique-conversation-id",
  "context": {
    "userId": "user-id",
    "tenantId": "tenant-id"
  }
}
```

## Response Structure

### 1. Intent Classification

The system classifies the user's intent into one of these categories:
- **SIMULATION**: What-if scenarios, forecasting, simulations
- **DECISION**: Decision-making queries, optimization requests
- **QUESTION**: Direct questions requiring answers
- **ANALYSIS**: Data analysis requests

**Example:**
```json
{
  "intentClassification": {
    "intent": "SIMULATION",
    "confidence": 0.9,
    "type": "financial-analysis",
    "explanation": "Classified as SIMULATION with 90% confidence",
    "keywords": ["sales forecast", "next quarter"],
    "entities": {
      "period": "next quarter"
    }
  }
}
```

### 2. Templates Discovered

The system finds relevant workflow templates from Supabase that match the query.

**Example:**
```json
{
  "turnEnvelope": {
    "plan": {
      "declarative": [
        {
          "action": "execute_template_9e9f6951-e738-47e6-a745-c37d526fbe9d",
          "templateId": "9e9f6951-e738-47e6-a745-c37d526fbe9d",
          "templateName": "Demand Forecasting Workflow",
          "domain": "supply_chain",
          "relevance": 0.6
        }
      ]
    }
  }
}
```

### 3. Agents Selected

The system selects specific agents to execute tasks based on the templates and intent.

**Example:**
```json
{
  "turnEnvelope": {
    "plan": {
      "procedural": [
        {
          "id": "task-123",
          "title": "Activate fqa for analysis",
          "service": "fqa",
          "capability": "general_analysis",
          "direction": "system_directed",
          "deps": []
        }
      ]
    }
  }
}
```

### 4. Response Message

The acknowledgment message that explains what the system is doing.

**Example:**
```json
{
  "turnEnvelope": {
    "ack": "I'm analyzing your simulation query using the Demand Forecasting Workflow..."
  }
}
```

## Agent Types

### Skill Agents
- **sda**: Semantic Data Agent - Data retrieval and semantic search
- **fqa**: Forecast Q&A Agent - Forecasting questions and predictions
- **caa**: Causal & Attribution Agent - Causal analysis and attribution

### Extended Skill Agents
- **ssa**: Scenario Simulator Agent - What-if scenarios
- **ira**: Inventory Risk Agent - Inventory risk analysis
- **opt**: Optimizer Agent - Optimization tasks
- **asa**: Answer Synthesis Agent - Final answer synthesis

### Demand-Gen Agents
- **marketing-plan**: Marketing Plan Agent
- **sales-pipeline**: Sales Pipeline Agent
- **elasticity-uplift**: Elasticity & Uplift Agent
- **campaign-sku**: Campaign→SKU Mapper Agent

### Supply Chain Agents
- **inventory-position**: Inventory Position Agent
- **capacity-leadtime**: Capacity & Lead-Time Agent
- **supply-plan**: Supply Planning Agent
- **production**: Production Scheduling Agent
- **procurement**: Procurement Agent
- **logistics**: Logistics & Allocation Agent
- **atp-ctp**: ATP/CTP Agent

### Governance Agents
- **constraint-broadcast**: Constraint Broadcast Agent
- **price-promo-guardrail**: Price/Promo Guardrail Agent
- **policy-elicitation**: Policy Elicitation Agent
- **data-gap**: Data Gap & Mapping Agent
- **rca**: RCA / Change Detective Agent

### MCO Agents
- **ingress**: Ingress & Normalization Agent
- **catalog**: Catalog & Schema Agent
- **feature**: Feature & Forecast Agent
- **attribution**: Attribution & Causal Agent
- **budget**: Budget Optimizer Agent
- **bid**: Bid & Target Setter Agent
- And 14 more...

## Testing Queries

### Quick Test
```bash
./test-queries.sh
```

### Detailed Test
```bash
./query-detail.sh "What is the sales forecast for next quarter?"
```

### Custom Query
```bash
curl -X POST http://localhost:3001/api/process-message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Your query here",
    "conversationId": "test-001",
    "context": {
      "userId": "test-user",
      "tenantId": "default"
    }
  }' | python3 -m json.tool
```

## Understanding Results

1. **Intent Classification**: Shows how the system understood your query
2. **Templates**: Workflow templates that match your query (higher relevance = better match)
3. **Agents**: Specific agents that will be activated to handle your query
4. **Response**: The acknowledgment message explaining what's happening

## Query Examples

### Sales Forecast
```bash
./query-detail.sh "What is the sales forecast for next quarter?"
```
**Expected**: SIMULATION intent, Demand Forecasting templates, fqa, sda, ssa agents

### Budget Allocation
```bash
./query-detail.sh "How should I allocate my marketing budget?"
```
**Expected**: DECISION intent, Marketing Budget Optimization template, budget, marketing-plan agents

### Inventory Risk
```bash
./query-detail.sh "What are the inventory risks for product X?"
```
**Expected**: QUESTION intent, Inventory Optimization template, ira, inventory-position agents

### Scenario Simulation
```bash
./query-detail.sh "Run a scenario simulation for pricing strategy"
```
**Expected**: SIMULATION intent, What-If Scenario template, ssa, opt, elasticity-uplift agents

