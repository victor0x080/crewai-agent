-- ============================================================================
-- Supabase Database Setup for IMS Agent Backend
-- Run this entire script in Supabase SQL Editor
-- ============================================================================

-- ============================================================================
-- 1. AI PROMPTS TABLE (REQUIRED)
-- Stores all OpenAI prompts for the system
-- ============================================================================

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

-- Add comment
COMMENT ON TABLE ai_prompts IS 'OpenAI system prompts for various agent functions';

-- ============================================================================
-- 2. WORKFLOW TEMPLATES TABLE (OPTIONAL - used by TemplateEngine)
-- Stores workflow templates for agent orchestration
-- ============================================================================

-- Try to enable pgvector extension (will fail silently if not available)
-- Note: pgvector is OPTIONAL - templates work without it
DO $$ 
BEGIN
  CREATE EXTENSION IF NOT EXISTS vector;
  RAISE NOTICE '✅ pgvector extension enabled (for semantic search)';
EXCEPTION
  WHEN OTHERS THEN
    RAISE NOTICE '⚠️  pgvector extension not available (semantic search disabled)';
    RAISE NOTICE '   Templates will still work with keyword search';
END $$;

-- Create table without vector column first
CREATE TABLE IF NOT EXISTS workflow_templates (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL,
  description TEXT,
  domain TEXT,
  template_schema JSONB DEFAULT '{}',
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Add vector column only if extension is available
DO $$
BEGIN
  -- Check if vector type exists
  IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'vector') THEN
    -- Add embedding column if it doesn't exist
    IF NOT EXISTS (
      SELECT 1 FROM information_schema.columns 
      WHERE table_name = 'workflow_templates' 
      AND column_name = 'embedding'
    ) THEN
      ALTER TABLE workflow_templates ADD COLUMN embedding VECTOR(1536);
      RAISE NOTICE '✅ Added embedding column for semantic search';
    END IF;
  ELSE
    RAISE NOTICE 'ℹ️  Skipping embedding column (pgvector not available)';
  END IF;
END $$;

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_workflow_templates_domain ON workflow_templates(domain);

-- Add vector index only if column exists
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'workflow_templates' 
    AND column_name = 'embedding'
  ) THEN
    CREATE INDEX IF NOT EXISTS idx_workflow_templates_embedding 
    ON workflow_templates USING ivfflat (embedding vector_cosine_ops);
    RAISE NOTICE '✅ Created vector index for fast semantic search';
  END IF;
EXCEPTION
  WHEN OTHERS THEN
    RAISE NOTICE 'ℹ️  Vector index not created (using standard indexes)';
END $$;

-- Add comment
COMMENT ON TABLE workflow_templates IS 'Workflow templates for agent orchestration';

-- ============================================================================
-- 3. CONVERSATIONS TABLE (OPTIONAL - used by MemoryService)
-- Stores conversation history
-- ============================================================================

CREATE TABLE IF NOT EXISTS conversations (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  message TEXT NOT NULL,
  intent TEXT,
  response JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at DESC);

-- Add comment
COMMENT ON TABLE conversations IS 'Conversation history for memory context';

-- ============================================================================
-- 4. KNOWLEDGE BASE TABLE (OPTIONAL - used by MemoryService)
-- Stores short-term and long-term memory
-- ============================================================================

CREATE TABLE IF NOT EXISTS knowledge_base (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id TEXT NOT NULL,
  memory_type TEXT NOT NULL CHECK (memory_type IN ('short_term', 'long_term')),
  content TEXT NOT NULL,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Add indexes
CREATE INDEX IF NOT EXISTS idx_knowledge_base_user_id ON knowledge_base(user_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_base_memory_type ON knowledge_base(memory_type);

-- Add comment
COMMENT ON TABLE knowledge_base IS 'User memory storage (short-term and long-term)';

-- ============================================================================
-- 5. INSERT REQUIRED PROMPTS
-- These 5 prompts are REQUIRED for the system to function
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

-- Update if already exists
ON CONFLICT (name) DO UPDATE SET
  content = EXCLUDED.content,
  metadata = EXCLUDED.metadata,
  updated_at = NOW();

-- ============================================================================
-- 6. VERIFICATION QUERIES
-- Run these to verify everything is set up correctly
-- ============================================================================

-- Check tables exist
SELECT 
  schemaname,
  tablename
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN ('ai_prompts', 'workflow_templates', 'conversations', 'knowledge_base')
ORDER BY tablename;

-- Check prompts are installed
SELECT 
  name,
  LENGTH(content) as content_length,
  metadata->>'model' as model,
  metadata->>'temperature' as temperature,
  created_at
FROM ai_prompts
ORDER BY name;

-- Expected output: 5 prompts
-- agent_orchestration
-- conversation_creator
-- intent_classifier
-- narrative_continuation
-- response_synthesis

-- ============================================================================
-- 7. OPTIONAL: CREATE RPC FUNCTION FOR SEMANTIC SEARCH
-- This is used by TemplateEngine for template discovery
-- Only created if pgvector extension is available
-- ============================================================================

-- Function for semantic search (only if vector column exists)
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'workflow_templates' 
    AND column_name = 'embedding'
  ) THEN
    -- Create the semantic search function
    CREATE OR REPLACE FUNCTION match_decision_templates(
      query_embedding VECTOR(1536),
      match_threshold FLOAT DEFAULT 0.7,
      match_count INT DEFAULT 5
    )
    RETURNS TABLE (
      id UUID,
      name TEXT,
      description TEXT,
      domain TEXT,
      template_schema JSONB,
      similarity FLOAT
    )
    LANGUAGE plpgsql
    AS $func$
    BEGIN
      RETURN QUERY
      SELECT
        workflow_templates.id,
        workflow_templates.name,
        workflow_templates.description,
        workflow_templates.domain,
        workflow_templates.template_schema,
        1 - (workflow_templates.embedding <=> query_embedding) as similarity
      FROM workflow_templates
      WHERE 1 - (workflow_templates.embedding <=> query_embedding) > match_threshold
      ORDER BY workflow_templates.embedding <=> query_embedding
      LIMIT match_count;
    END;
    $func$;
    
    RAISE NOTICE '✅ Created match_decision_templates() function for semantic search';
  ELSE
    RAISE NOTICE 'ℹ️  Semantic search function not created (pgvector not available)';
    RAISE NOTICE '   TemplateEngine will use keyword search instead';
  END IF;
END $$;

-- ============================================================================
-- SETUP COMPLETE!
-- ============================================================================

-- Final verification
DO $$
DECLARE
  prompt_count INT;
  table_count INT;
BEGIN
  SELECT COUNT(*) INTO prompt_count FROM ai_prompts;
  SELECT COUNT(*) INTO table_count 
  FROM pg_tables 
  WHERE schemaname = 'public' 
    AND tablename IN ('ai_prompts', 'workflow_templates', 'conversations', 'knowledge_base');
  
  RAISE NOTICE '============================================';
  RAISE NOTICE 'Supabase Setup Complete!';
  RAISE NOTICE '============================================';
  RAISE NOTICE 'Tables created: %', table_count;
  RAISE NOTICE 'Prompts installed: %', prompt_count;
  RAISE NOTICE '';
  RAISE NOTICE 'Required prompts: 5 (MUST HAVE)';
  RAISE NOTICE 'Other tables: Optional (for full features)';
  RAISE NOTICE '';
  
  IF prompt_count >= 5 THEN
    RAISE NOTICE '✅ SUCCESS: All required prompts installed!';
    RAISE NOTICE 'Your backend is ready to use.';
  ELSE
    RAISE NOTICE '⚠️  WARNING: Only % prompts found (need 5)', prompt_count;
    RAISE NOTICE 'Please check the ai_prompts table.';
  END IF;
  
  RAISE NOTICE '============================================';
END $$;

