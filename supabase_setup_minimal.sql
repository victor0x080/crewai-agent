-- ============================================================================
-- MINIMAL Supabase Setup (No pgvector required)
-- This is the FASTEST way to get started - only creates essential tables
-- ============================================================================

-- ============================================================================
-- 1. AI PROMPTS TABLE (REQUIRED - System won't work without this!)
-- ============================================================================

CREATE TABLE IF NOT EXISTS ai_prompts (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT UNIQUE NOT NULL,
  content TEXT NOT NULL,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_prompts_name ON ai_prompts(name);

-- ============================================================================
-- 2. INSERT 5 REQUIRED PROMPTS
-- ============================================================================

INSERT INTO ai_prompts (name, content, metadata) VALUES 

-- Prompt 1: Intent Classifier
('intent_classifier', 
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
'{"model": "gpt-4-turbo-preview", "temperature": 0.2, "max_tokens": 300}'::jsonb),

-- Prompt 2: Conversation Creator
('conversation_creator',
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
'{"model": "gpt-4-turbo-preview", "temperature": 0.7, "max_tokens": 2000}'::jsonb),

-- Prompt 3: Narrative Continuation
('narrative_continuation',
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
'{"model": "gpt-4-turbo-preview", "temperature": 0.7, "max_tokens": 1500}'::jsonb),

-- Prompt 4: Agent Orchestration
('agent_orchestration',
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
'{"model": "gpt-4-turbo-preview", "temperature": 0.3, "max_tokens": 800}'::jsonb),

-- Prompt 5: Response Synthesis
('response_synthesis',
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
'{"model": "gpt-4-turbo-preview", "temperature": 0.6, "max_tokens": 2500}'::jsonb)

ON CONFLICT (name) DO UPDATE SET
  content = EXCLUDED.content,
  metadata = EXCLUDED.metadata,
  updated_at = NOW();

-- ============================================================================
-- 3. VERIFY SETUP
-- ============================================================================

DO $$
DECLARE
  prompt_count INT;
BEGIN
  SELECT COUNT(*) INTO prompt_count FROM ai_prompts;
  
  RAISE NOTICE '';
  RAISE NOTICE '============================================';
  RAISE NOTICE '✅ MINIMAL SETUP COMPLETE!';
  RAISE NOTICE '============================================';
  RAISE NOTICE 'Prompts installed: % / 5 required', prompt_count;
  RAISE NOTICE '';
  
  IF prompt_count >= 5 THEN
    RAISE NOTICE '✅ SUCCESS: All required prompts installed!';
    RAISE NOTICE '   Your backend is ready to use.';
    RAISE NOTICE '';
    RAISE NOTICE '📝 Next steps:';
    RAISE NOTICE '   1. Update .env with Supabase credentials';
    RAISE NOTICE '   2. Run: npm start';
    RAISE NOTICE '   3. Test with: POST /api/process-message';
  ELSE
    RAISE NOTICE '⚠️  WARNING: Only % prompts found (need 5)', prompt_count;
  END IF;
  
  RAISE NOTICE '============================================';
  RAISE NOTICE '';
END $$;

-- Show what was created
SELECT 
  name,
  LENGTH(content) as content_length,
  metadata->>'model' as model,
  metadata->>'temperature' as temperature
FROM ai_prompts
ORDER BY name;

