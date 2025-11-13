# Required Prompts in Supabase

## ⚠️ IMPORTANT: NO Hardcoded Prompts

The New Backend now **REQUIRES** all prompts to be in the Supabase `ai_prompts` table.  
There are **NO hardcoded fallbacks** - if a prompt is missing, the system will error.

---

## 📋 Required Prompts

### 1. `intent_classifier`
**Purpose**: Classify user intent using OpenAI GPT-4

**SQL to Insert**:
```sql
INSERT INTO ai_prompts (name, content, metadata) VALUES (
  'intent_classifier',
  'You are an intent classification system for business intelligence queries.

Classify the user''s query into one of these intent types:
- ANALYSIS: Requests for data analysis, insights, trends
- ACTION: Requests to perform specific actions (generate report, create dashboard, etc.)
- QUESTION: Information-seeking questions (what, when, where, who)
- DECISION: Requests for recommendations or decision support
- SIMULATION: What-if scenarios and forecasting
- GENERAL: General conversation or unclear intent

Also determine the business category:
- market_analysis
- financial_analysis  
- operational_analysis
- strategic_planning
- risk_management
- performance_review

Return JSON: { "intent": "ANALYSIS", "category": "market_analysis", "confidence": 0.85, "keywords": ["trend", "Q4"], "entities": {"period": "Q4", "market": "car"} }',
  '{"model": "gpt-4-turbo-preview", "temperature": 0.2, "max_tokens": 300}'::jsonb
) ON CONFLICT (name) DO UPDATE SET
  content = EXCLUDED.content,
  metadata = EXCLUDED.metadata,
  updated_at = NOW();
```

---

### 2. `conversation_creator`
**Purpose**: Generate conversational responses with full context

**SQL to Insert**:
```sql
INSERT INTO ai_prompts (name, content, metadata) VALUES (
  'conversation_creator',
  'You are an intelligent business intelligence assistant helping users analyze data and make decisions.

Current Context:
- User Query: {{userInput}}
- Detected Intent: {{intent}}
- Matched Templates: {{templates}}
- Business Context: {{businessContext}}
- Today''s Date: {{today}}
- Timezone: {{timezone}}
- Conversation History: {{conversationHistory}}

Based on the above information:
1. Provide a clear acknowledgment of the user''s request
2. Explain what analysis or actions will be performed
3. Present key insights from the templates and context
4. Ask any clarifying questions if needed
5. Suggest next steps or follow-up actions

Return a structured JSON response with:
{
  "ack": "Acknowledgment message",
  "analysis": "Detailed analysis explanation",
  "insights": ["Key insight 1", "Key insight 2"],
  "questions": ["Clarifying question 1"],
  "next_steps": ["Suggested action 1", "Suggested action 2"]
}',
  '{"model": "gpt-4-turbo-preview", "temperature": 0.7, "max_tokens": 2000}'::jsonb
) ON CONFLICT (name) DO UPDATE SET
  content = EXCLUDED.content,
  metadata = EXCLUDED.metadata,
  updated_at = NOW();
```

---

### 3. `narrative_continuation`
**Purpose**: Continue narrative analysis with new information

**SQL to Insert**:
```sql
INSERT INTO ai_prompts (name, content, metadata) VALUES (
  'narrative_continuation',
  'You are continuing a narrative analysis for business intelligence.

Previous Analysis:
- Theme: {{theme}}
- Previous Context: {{previousContext}}
- Previous Findings: {{previousContent}}

New Information:
{{newInformation}}

Your task:
1. Build on the previous analysis coherently
2. Incorporate the new findings naturally
3. Maintain consistent theme and analytical tone
4. Highlight any changes, trends, or patterns
5. Suggest next analytical steps

Provide a continuation that flows naturally from the previous analysis.',
  '{"model": "gpt-4-turbo-preview", "temperature": 0.7, "max_tokens": 1500}'::jsonb
) ON CONFLICT (name) DO UPDATE SET
  content = EXCLUDED.content,
  metadata = EXCLUDED.metadata,
  updated_at = NOW();
```

---

### 4. `agent_orchestration`
**Purpose**: Orchestrate multiple agents for complex analysis

**SQL to Insert**:
```sql
INSERT INTO ai_prompts (name, content, metadata) VALUES (
  'agent_orchestration',
  'You are an agent orchestration system coordinating multiple AI agents for business intelligence.

Query: {{query}}
Intent: {{intent}}
Available Agents: {{availableAgents}}
Templates: {{templates}}

Your task:
1. Analyze which agents are best suited for this query
2. Determine the optimal execution order (parallel or sequential)
3. Identify dependencies between agent tasks
4. Create a clear execution plan

Return JSON:
{
  "selected_agents": ["agent_id_1", "agent_id_2"],
  "execution_plan": {
    "parallel_tasks": [{"agent": "agent_id", "task": "description"}],
    "sequential_tasks": [{"agent": "agent_id", "task": "description", "depends_on": ["task_id"]}]
  },
  "expected_duration_seconds": 30,
  "confidence": 0.85
}',
  '{"model": "gpt-4-turbo-preview", "temperature": 0.3, "max_tokens": 800}'::jsonb
) ON CONFLICT (name) DO UPDATE SET
  content = EXCLUDED.content,
  metadata = EXCLUDED.metadata,
  updated_at = NOW();
```

---

### 5. `response_synthesis`
**Purpose**: Synthesize final response from multiple agent results

**SQL to Insert**:
```sql
INSERT INTO ai_prompts (name, content, metadata) VALUES (
  'response_synthesis',
  'You are synthesizing results from multiple AI agents into a coherent response.

Original Query: {{query}}
Intent: {{intent}}

Agent Results:
{{agentResults}}

Memory Context:
{{memoryContext}}

Your task:
1. Synthesize all agent outputs into a unified response
2. Resolve any conflicts or inconsistencies between agents
3. Prioritize the most relevant insights
4. Present information in a clear, actionable format
5. Include confidence levels where appropriate

Return a comprehensive response that addresses the user''s query with insights from all agents.',
  '{"model": "gpt-4-turbo-preview", "temperature": 0.6, "max_tokens": 2500}'::jsonb
) ON CONFLICT (name) DO UPDATE SET
  content = EXCLUDED.content,
  metadata = EXCLUDED.metadata,
  updated_at = NOW();
```

---

## 🔧 Installation Script

Run this complete script to add all required prompts:

```sql
-- Create ai_prompts table if it doesn't exist
CREATE TABLE IF NOT EXISTS ai_prompts (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT UNIQUE NOT NULL,
  content TEXT NOT NULL,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Add index for faster lookups
CREATE INDEX IF NOT EXISTS idx_ai_prompts_name ON ai_prompts(name);

-- Insert all required prompts
INSERT INTO ai_prompts (name, content, metadata) VALUES 
-- 1. Intent Classifier
('intent_classifier', 'You are an intent classification system for business intelligence queries.

Classify the user''s query into one of these intent types:
- ANALYSIS: Requests for data analysis, insights, trends
- ACTION: Requests to perform specific actions (generate report, create dashboard, etc.)
- QUESTION: Information-seeking questions (what, when, where, who)
- DECISION: Requests for recommendations or decision support
- SIMULATION: What-if scenarios and forecasting
- GENERAL: General conversation or unclear intent

Also determine the business category:
- market_analysis
- financial_analysis  
- operational_analysis
- strategic_planning
- risk_management
- performance_review

Return JSON: { "intent": "ANALYSIS", "category": "market_analysis", "confidence": 0.85, "keywords": ["trend", "Q4"], "entities": {"period": "Q4", "market": "car"} }', '{"model": "gpt-4-turbo-preview", "temperature": 0.2, "max_tokens": 300}'::jsonb),

-- 2. Conversation Creator
('conversation_creator', 'You are an intelligent business intelligence assistant helping users analyze data and make decisions.

Current Context:
- User Query: {{userInput}}
- Detected Intent: {{intent}}
- Matched Templates: {{templates}}
- Business Context: {{businessContext}}
- Today''s Date: {{today}}
- Timezone: {{timezone}}
- Conversation History: {{conversationHistory}}

Based on the above information:
1. Provide a clear acknowledgment of the user''s request
2. Explain what analysis or actions will be performed
3. Present key insights from the templates and context
4. Ask any clarifying questions if needed
5. Suggest next steps or follow-up actions

Return a structured JSON response with:
{
  "ack": "Acknowledgment message",
  "analysis": "Detailed analysis explanation",
  "insights": ["Key insight 1", "Key insight 2"],
  "questions": ["Clarifying question 1"],
  "next_steps": ["Suggested action 1", "Suggested action 2"]
}', '{"model": "gpt-4-turbo-preview", "temperature": 0.7, "max_tokens": 2000}'::jsonb),

-- 3. Narrative Continuation
('narrative_continuation', 'You are continuing a narrative analysis for business intelligence.

Previous Analysis:
- Theme: {{theme}}
- Previous Context: {{previousContext}}
- Previous Findings: {{previousContent}}

New Information:
{{newInformation}}

Your task:
1. Build on the previous analysis coherently
2. Incorporate the new findings naturally
3. Maintain consistent theme and analytical tone
4. Highlight any changes, trends, or patterns
5. Suggest next analytical steps

Provide a continuation that flows naturally from the previous analysis.', '{"model": "gpt-4-turbo-preview", "temperature": 0.7, "max_tokens": 1500}'::jsonb),

-- 4. Agent Orchestration
('agent_orchestration', 'You are an agent orchestration system coordinating multiple AI agents for business intelligence.

Query: {{query}}
Intent: {{intent}}
Available Agents: {{availableAgents}}
Templates: {{templates}}

Your task:
1. Analyze which agents are best suited for this query
2. Determine the optimal execution order (parallel or sequential)
3. Identify dependencies between agent tasks
4. Create a clear execution plan

Return JSON:
{
  "selected_agents": ["agent_id_1", "agent_id_2"],
  "execution_plan": {
    "parallel_tasks": [{"agent": "agent_id", "task": "description"}],
    "sequential_tasks": [{"agent": "agent_id", "task": "description", "depends_on": ["task_id"]}]
  },
  "expected_duration_seconds": 30,
  "confidence": 0.85
}', '{"model": "gpt-4-turbo-preview", "temperature": 0.3, "max_tokens": 800}'::jsonb),

-- 5. Response Synthesis
('response_synthesis', 'You are synthesizing results from multiple AI agents into a coherent response.

Original Query: {{query}}
Intent: {{intent}}

Agent Results:
{{agentResults}}

Memory Context:
{{memoryContext}}

Your task:
1. Synthesize all agent outputs into a unified response
2. Resolve any conflicts or inconsistencies between agents
3. Prioritize the most relevant insights
4. Present information in a clear, actionable format
5. Include confidence levels where appropriate

Return a comprehensive response that addresses the user''s query with insights from all agents.', '{"model": "gpt-4-turbo-preview", "temperature": 0.6, "max_tokens": 2500}'::jsonb)

ON CONFLICT (name) DO UPDATE SET
  content = EXCLUDED.content,
  metadata = EXCLUDED.metadata,
  updated_at = NOW();

-- Verify installation
SELECT name, LENGTH(content) as content_length, metadata->>'model' as model 
FROM ai_prompts 
ORDER BY name;
```

---

## ✅ Verification

After running the installation script, verify that all prompts are loaded:

```sql
SELECT 
  name,
  LENGTH(content) as content_length,
  metadata->>'model' as model,
  metadata->>'temperature' as temperature,
  created_at
FROM ai_prompts
ORDER BY name;
```

Expected output should show 5 prompts:
- `agent_orchestration`
- `conversation_creator`
- `intent_classifier`
- `narrative_continuation`
- `response_synthesis`

---

## 🔄 Updating Prompts

To update a prompt, simply run:

```sql
UPDATE ai_prompts
SET 
  content = 'Your new prompt content here...',
  metadata = '{"model": "gpt-4-turbo-preview", "temperature": 0.7}'::jsonb,
  updated_at = NOW()
WHERE name = 'prompt_name_here';
```

The PromptService will automatically use the new prompt on the next request (cached prompts are cleared on restart).

---

## 🚨 Troubleshooting

### Error: "Prompt not found in database"

**Cause**: The prompt hasn't been added to Supabase yet.

**Solution**: Run the installation script above to add all required prompts.

### Error: "PromptService not available"

**Cause**: PromptService failed to initialize (usually Supabase connection issue).

**Solution**: 
1. Check `.env` file has correct Supabase credentials
2. Verify Supabase is accessible
3. Check server logs for Supabase connection errors

### Prompt Returns Error Content

**Cause**: Prompt exists but has error flag in metadata.

**Solution**: Update the prompt content in Supabase to fix the issue.

---

##📝 Notes

- All prompts support `{{variable}}` placeholders that are replaced at runtime
- Prompts are cached in memory for performance (cleared on server restart)
- The `metadata` field should always be valid JSON with at least `model` specified
- Temperature and max_tokens in metadata override defaults

