# How to Get "Interpret" Responses

## Understanding the "Interpret" Stage

The **"interpret"** workflow stage is used when there are **existing outputs, data, or results** to interpret. It's NOT for setup tasks or questions without data.

## When You Get "Interpret" Responses

### ✅ Interpret Stage is Used When:
1. You have data/results/outputs to analyze
2. You're asking "what does this data mean?"
3. You're asking "help me understand these results"
4. You're asking about existing analysis or reports

### ❌ Interpret Stage is NOT Used When:
1. Setting up alerts ("alert me if...")
2. Configuring monitoring ("monitor...")
3. Asking general questions without data
4. Setup/configuration tasks

## How to Get Interpret Responses

### Method 1: Reference Existing Data/Results

Ask to interpret data that already exists:

```bash
# Example 1: Interpret existing sales data
curl -X POST "http://localhost:3001/api/process-message" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "help me understand this sales data: Q1 revenue was $2M, Q2 was $1.5M, Q3 was $1.8M",
    "conversationId": "test-interpret-1"
  }'
```

### Method 2: Ask About Results from Previous Queries

If you've already run analysis or queries, ask to interpret those results:

```bash
# Step 1: Get some data/analysis first
curl -X POST "http://localhost:3001/api/process-message" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "what are our sales numbers for the last quarter?",
    "conversationId": "test-interpret-2"
  }'

# Step 2: Then ask to interpret those results (same conversationId)
curl -X POST "http://localhost:3001/api/process-message" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "what does this sales data mean?",
    "conversationId": "test-interpret-2"
  }'
```

### Method 3: Use "Understand" Problem Type with Data

The "understand" problem type with actual data will trigger interpret:

```bash
# Example: Understanding existing results
curl -X POST "http://localhost:3001/api/process-message" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "help me understand why our inventory turnover rate is 4.2 compared to industry average of 6.0",
    "conversationId": "test-interpret-3"
  }'
```

### Method 4: Reference Previous Analysis

Reference something that was analyzed before:

```bash
# Example: Interpreting a trend that was mentioned
curl -X POST "http://localhost:3001/api/process-message" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "earlier you mentioned sales dropped 15%. what does that mean for our business?",
    "conversationId": "test-interpret-4"
  }'
```

## Example Queries That Trigger "Interpret"

### ✅ These Will Use "Interpret" Stage:

1. **With explicit data:**
   - "help me understand this data: [data here]"
   - "what does this report mean: [report details]"
   - "interpret these results: [results]"

2. **Referencing existing analysis:**
   - "what does the sales trend show?"
   - "explain what this inventory analysis means"
   - "what insights can we draw from these metrics?"

3. **Understanding existing outputs:**
   - "help me understand the forecast results"
   - "what does this dashboard tell us?"
   - "explain the meaning of these KPIs"

### ❌ These Will Use "Full-LLM" Stage (Setup):

1. **Setup/configuration:**
   - "alert me if there is a risk"
   - "monitor sales performance"
   - "automate order processing"

2. **General questions without data:**
   - "what is inventory management?"
   - "how do I set up alerts?"

## Workflow Progression Example

Here's a complete example showing how to get through all stages:

```bash
CONV_ID="workflow-example-$(date +%s)"

# Stage 1: FULL-LLM (setup/configuration)
curl -X POST "http://localhost:3001/api/process-message" \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"set up monitoring for sales performance\", \"conversationId\": \"$CONV_ID\"}"

# Stage 2: INTERPRET (after data is available)
curl -X POST "http://localhost:3001/api/process-message" \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"help me understand this sales data: Q1=$2M, Q2=$1.5M, Q3=$1.8M\", \"conversationId\": \"$CONV_ID\"}"

# Stage 3: RECOMMEND (based on interpreted data)
curl -X POST "http://localhost:3001/api/process-message" \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"what do you recommend I do about the declining sales?\", \"conversationId\": \"$CONV_ID\"}"

# Stage 4: WHAT-IF (simulation)
curl -X POST "http://localhost:3001/api/process-message" \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"what if we increase marketing budget by 20%?\", \"conversationId\": \"$CONV_ID\"}"
```

## Quick Test Script

```bash
#!/bin/bash
# Test getting interpret responses

CONV_ID="interpret-test-$(date +%s)"
BASE_URL="http://localhost:3001/api/process-message"

echo "Testing INTERPRET stage responses..."
echo ""

# Test 1: Interpret with explicit data
echo "1. Interpret with explicit data:"
curl -s -X POST "$BASE_URL" \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"help me understand this sales data: Q1 revenue was \$2M, Q2 was \$1.5M, Q3 was \$1.8M. What does this trend mean?\", \"conversationId\": \"$CONV_ID\"}" \
  | grep -o '"workflow_stage":"[^"]*"'
echo ""

# Test 2: Interpret existing results
echo "2. Interpret existing results (after providing context):"
curl -s -X POST "$BASE_URL" \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"our inventory turnover is 4.2 vs industry average of 6.0. what does this mean?\", \"conversationId\": \"$CONV_ID\"}" \
  | grep -o '"workflow_stage":"[^"]*"'
echo ""

echo "✅ Test complete!"
```

## Key Takeaways

1. **"Interpret" requires data**: You need existing outputs/data/results to interpret
2. **Include data in query**: Provide the data explicitly in your query
3. **Reference previous results**: Ask to interpret results from earlier in the conversation
4. **Use "understand" with data**: "Help me understand [data]" triggers interpret
5. **Setup queries use "full-llm"**: Configuration tasks skip interpret stage

## Troubleshooting

**Q: Why am I getting "full-llm" instead of "interpret"?**
- A: You're likely asking a setup/configuration question without data. Include actual data in your query or reference existing results.

**Q: How do I know if my query will trigger "interpret"?**
- A: If your query includes data to analyze or references existing results, it should use "interpret". If it's asking to set something up, it will use "full-llm".

**Q: Can I force "interpret" stage?**
- A: Not directly, but you can ensure your query includes data to interpret, which will naturally trigger the interpret stage.

