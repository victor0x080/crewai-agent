# Problem-First Conversational Workflow Implementation

## Overview

The conversational agent workflow has been updated to implement a **problem-first approach** for business executives, as specified in the requirements. The system now operates with a narrowly defined problem space rather than an open-ended "ask me anything" interface.

## Key Changes

### 1. Problem Type Classification

**New Service: `ProblemTypeClassifier.js`**
- Classifies executive queries into specific problem types:
  - **alert**: "alert me if there is a risk"
  - **understand**: "help me understand this situation"
  - **solve**: "solve this problem"
  - **monitor**: "monitor this situation"
  - **automate**: "automate this process"
  - **general**: Fallback for general questions

- Uses OpenAI for intelligent classification with fallback keyword matching
- Determines workflow stage progression based on problem type and conversation history

### 2. Workflow Stage Progression

The system now tracks and guides conversations through workflow stages:

1. **interpret** - First stage: Interpret outputs, explain what data/results mean
2. **recommend** - Second stage: Provide recommendations based on interpreted outputs
3. **what-if** - Third stage: Run simulations or "what if" scenarios
4. **full-llm** - Final stage: Full LLM capabilities for complex questions

**Stage Progression Logic:**
- Alerts and monitoring: `interpret` → `full-llm` (skip recommend/what-if)
- Automation: `interpret` → `recommend` → `full-llm`
- Other types: `interpret` → `recommend` → `what-if` → `full-llm`

### 3. Updated Conversational Agent

**Python Agent (`conversational_agent.py`)**
- Updated system prompt to reflect problem-first approach
- Receives problem context (type, space, workflow stage) from backend
- Guides conversations within the defined problem space
- Maintains workflow stage awareness throughout the conversation

**Key Features:**
- Problem space is always narrowly defined
- Conversations stay focused on the executive's specific problem
- Natural progression through workflow stages
- Still supports general questions but relates them to problem context when possible

### 4. Server Integration

**Updated `server.js`**
- Integrates `ProblemTypeClassifier` service
- Classifies problem type before routing to conversational agent
- Passes problem context (type, space, workflow stage) to agent
- Includes problem classification in response metadata

**Flow:**
1. User sends query with `conversationId`
2. Server classifies problem type using `ProblemTypeClassifier`
3. Retrieves conversation history for context
4. Determines workflow stage based on history and problem type
5. Passes problem context to CrewAI conversational agent
6. Agent processes query with problem-first approach
7. Response includes problem type and workflow stage metadata

### 5. Runner Updates

**Updated `conversational_runner.py`**
- Extracts problem context from inputs
- Passes enhanced context to agent with problem information
- Includes problem metadata in response payload

## Architecture

```
User Query
    ↓
Server (server.js)
    ↓
ProblemTypeClassifier.classifyProblemType()
    ↓
    ├─→ Problem Type (alert/understand/solve/monitor/automate/general)
    ├─→ Problem Space (narrowly defined)
    └─→ Workflow Stage (interpret/recommend/what-if/full-llm)
    ↓
CrewAI Conversational Agent
    ↓
    ├─→ Receives problem context
    ├─→ Uses problem-first system prompt
    └─→ Guides conversation through workflow stages
    ↓
Response with Problem Metadata
```

## API Response Format

The response now includes problem classification metadata:

```json
{
  "requestId": "...",
  "query": "alert me if there is a risk",
  "conversationId": "...",
  "response": "...",
  "metadata": {
    "conversation_id": "...",
    "problem_type": "alert",
    "workflow_stage": "interpret",
    "problem_space": "risk monitoring and alerting"
  },
  "turnEnvelope": {
    "meta": {
      "problemType": "alert",
      "workflowStage": "interpret",
      "problemSpace": "risk monitoring and alerting"
    }
  }
}
```

## Benefits

1. **Problem-Focused**: Conversations start with a specific problem, not open-ended questions
2. **Structured Workflow**: Natural progression through interpret → recommend → what-if → full-llm
3. **Context Awareness**: System understands the problem space and stays focused
4. **Executive-Friendly**: Designed for business executives with specific problem-solving needs
5. **Flexible**: Still supports general questions but within problem context

## Configuration

The `ProblemTypeClassifier` uses:
- OpenAI model from `config.openai.model` (default: `gpt-4-turbo-preview`)
- Temperature: `0.2` (low for consistent classification)
- Max tokens: `300` (sufficient for classification JSON)

## Future Enhancements

Potential improvements:
- Problem space persistence across conversation turns
- Automatic workflow stage transitions based on conversation flow
- Problem-specific agent routing (e.g., route "alert" queries to monitoring agents)
- Problem space refinement through conversation
- Integration with declarative/performative task agents (when available)

## Testing

To test the problem-first workflow:

1. Send a query with a `conversationId`:
```bash
curl -X POST http://localhost:3001/api/process-message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "alert me if there is a risk in sales",
    "conversationId": "test-conv-123"
  }'
```

2. Check response metadata for `problem_type` and `workflow_stage`

3. Continue conversation to see workflow stage progression

## Notes

- The system maintains backward compatibility - if problem classification fails, it falls back to "general" type
- Workflow stages are tracked in conversation context and metadata
- Problem space is defined from the initial query and can be refined through conversation
- The system still supports general questions but tries to relate them to the problem context

