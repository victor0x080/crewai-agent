-- Add conversation_id column to conversations and knowledge_base tables
-- Run this in Supabase SQL Editor

-- Add conversation_id to knowledge_base table (if it doesn't exist)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'knowledge_base' 
    AND column_name = 'conversation_id'
  ) THEN
    ALTER TABLE knowledge_base ADD COLUMN conversation_id TEXT;
    CREATE INDEX IF NOT EXISTS idx_knowledge_base_conversation_id ON knowledge_base(conversation_id);
    RAISE NOTICE '✅ Added conversation_id column to knowledge_base';
  ELSE
    RAISE NOTICE 'ℹ️  conversation_id column already exists in knowledge_base';
  END IF;
END $$;

-- Note: conversations table already has 'id' column which is the conversationId
-- But let's verify the structure is correct
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'conversations' 
    AND column_name = 'user_id'
  ) THEN
    RAISE EXCEPTION 'conversations table missing user_id column - please run supabase_setup.sql first';
  ELSE
    RAISE NOTICE '✅ conversations table has user_id column';
  END IF;
END $$;

-- Verify knowledge_base has user_id
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns 
    WHERE table_name = 'knowledge_base' 
    AND column_name = 'user_id'
  ) THEN
    RAISE EXCEPTION 'knowledge_base table missing user_id column - please run supabase_setup.sql first';
  ELSE
    RAISE NOTICE '✅ knowledge_base table has user_id column';
  END IF;
END $$;

