# Testing the Problem-First Conversational Workflow

## Status

✅ **Implementation Complete**: All code changes have been implemented and the ProblemTypeClassifier service is working correctly.

⚠️ **Server Restart Required**: The server needs to be restarted to pick up the new changes.

## Quick Test

The ProblemTypeClassifier has been tested directly and is working:

```bash
node scripts/test-problem-classifier-direct.js
```

Expected output shows correct classification for all problem types:
- `alert` - "alert me if there is a risk"
- `understand` - "help me understand the situation"
- `solve` - "solve this problem"
- `monitor` - "monitor this situation"
- `automate` - "automate this process"

## After Server Restart

### 1. Restart the Server

```bash
# Stop the current server (Ctrl+C if running in foreground)
# Then restart:
npm start
# or
node src/server.js
```

### 2. Verify Health Check

```bash
curl http://localhost:3001/api/health | jq '.services.problemTypeClassifier'
```

Should return: `true`

### 3. Test Problem Classification

```bash
curl -X POST http://localhost:3001/api/process-message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "alert me if there is a risk in sales",
    "conversationId": "test-123"
  }' | jq '{problem_type, workflow_stage, problem_space}'
```

Expected response:
```json
{
  "problem_type": "alert",
  "workflow_stage": "interpret",
  "problem_space": "Risk identification and notification for sales"
}
```

### 4. Run Full Test Suite

```bash
node scripts/test-problem-first-workflow.js
```

This will test:
- ✅ Server health (including ProblemTypeClassifier)
- ✅ Problem type classification for all types
- ✅ Workflow stage progression
- ✅ Complete conversation flow

## Expected Behavior

### Problem Type Classification

The system should classify queries into:
- **alert**: Risk alerts, notifications
- **understand**: Analysis, explanations, insights
- **solve**: Problem solving, decision making
- **monitor**: Tracking, watching, observing
- **automate**: Process automation, workflows
- **general**: General questions (fallback)

### Workflow Stages

Conversations progress through stages:
1. **interpret** - First stage: Interpret outputs
2. **recommend** - Second stage: Provide recommendations
3. **what-if** - Third stage: Run simulations
4. **full-llm** - Final stage: Full LLM capabilities

### Response Structure

Responses now include problem classification at multiple levels:

```json
{
  "problem_type": "alert",
  "workflow_stage": "interpret",
  "problem_space": "...",
  "metadata": {
    "problem_type": "alert",
    "workflow_stage": "interpret",
    "problem_space": "..."
  },
  "turnEnvelope": {
    "meta": {
      "problemType": "alert",
      "workflowStage": "interpret",
      "problemSpace": "..."
    }
  }
}
```

## Troubleshooting

### Problem Type is `undefined`

**Cause**: Server is running old code  
**Solution**: Restart the server

### ProblemTypeClassifier not in health check

**Cause**: Service not initialized  
**Solution**: Check server logs for initialization errors

### Classification always returns "general"

**Cause**: OpenAI API key not configured or classification failing  
**Solution**: 
1. Check `config/openai.apiKey` is set
2. Check server logs for classification errors
3. Fallback keyword matching should still work

## Implementation Files

- ✅ `src/services/ProblemTypeClassifier.js` - Problem type classification service
- ✅ `src/server.js` - Updated to use ProblemTypeClassifier
- ✅ `src/services/MemoryService.js` - Added `getConversationHistory` method
- ✅ `agents/crewai_python/agents/conversational_agent.py` - Updated system prompt
- ✅ `agents/crewai_python/runners/conversational_runner.py` - Updated to handle problem context

## Next Steps

1. **Restart the server** to apply changes
2. **Run the test suite** to verify everything works
3. **Test with real conversations** to see workflow stage progression
4. **Monitor logs** for any classification issues

