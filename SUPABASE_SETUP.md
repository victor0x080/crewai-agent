# Supabase Setup Guide

## 🎯 Quick Start

Your backend requires Supabase tables to be set up. Follow these steps:

---

## Step 1: Access Supabase SQL Editor

1. Go to your Supabase project: https://supabase.com/dashboard
2. Select your project
3. Click on **SQL Editor** in the left sidebar
4. Click **"+ New query"**

---

## Step 2: Run Setup Script

**Choose ONE of these options:**

### Option A: Minimal Setup (RECOMMENDED - No pgvector needed)

Use `supabase_setup_minimal.sql` - Only creates essential `ai_prompts` table with 5 prompts.

1. Open `supabase_setup_minimal.sql`
2. Copy ALL contents
3. Paste into Supabase SQL Editor
4. Click **"Run"**

✅ **This will work on ANY Supabase project!**

### Option B: Full Setup (Requires pgvector extension)

Use `supabase_setup.sql` - Creates all tables including vector search support.

1. Open `supabase_setup.sql`
2. Copy ALL contents
3. Paste into Supabase SQL Editor
4. Click **"Run"**

⚠️ **Note**: If you get "type 'vector' does not exist" error, use Option A instead.

Or manually run this:

```sql
-- 1. Create ai_prompts table (REQUIRED)
CREATE TABLE IF NOT EXISTS ai_prompts (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT UNIQUE NOT NULL,
  content TEXT NOT NULL,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_prompts_name ON ai_prompts(name);

-- 2. Create other tables (OPTIONAL but recommended)
CREATE TABLE IF NOT EXISTS workflow_templates (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL,
  description TEXT,
  domain TEXT,
  template_schema JSONB DEFAULT '{}',
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS conversations (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  message TEXT NOT NULL,
  intent TEXT,
  response JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS knowledge_base (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id TEXT NOT NULL,
  memory_type TEXT NOT NULL CHECK (memory_type IN ('short_term', 'long_term')),
  content TEXT NOT NULL,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMP DEFAULT NOW()
);

-- 3. Insert 5 REQUIRED prompts
INSERT INTO ai_prompts (name, content, metadata) VALUES 
('intent_classifier', 
 'You are an intent classification system for business intelligence queries...', 
 '{"model": "gpt-4-turbo-preview", "temperature": 0.2, "max_tokens": 300}'::jsonb),
('conversation_creator', 
 'You are an intelligent business intelligence assistant...', 
 '{"model": "gpt-4-turbo-preview", "temperature": 0.7, "max_tokens": 2000}'::jsonb),
('narrative_continuation', 
 'You are continuing a narrative analysis...', 
 '{"model": "gpt-4-turbo-preview", "temperature": 0.7, "max_tokens": 1500}'::jsonb),
('agent_orchestration', 
 'You are an agent orchestration system...', 
 '{"model": "gpt-4-turbo-preview", "temperature": 0.3, "max_tokens": 800}'::jsonb),
('response_synthesis', 
 'You are synthesizing results from multiple AI agents...', 
 '{"model": "gpt-4-turbo-preview", "temperature": 0.6, "max_tokens": 2500}'::jsonb)
ON CONFLICT (name) DO UPDATE SET
  content = EXCLUDED.content,
  metadata = EXCLUDED.metadata,
  updated_at = NOW();
```

---

## Step 3: Verify Setup

Run this verification query in Supabase SQL Editor:

```sql
-- Check tables exist
SELECT tablename 
FROM pg_tables 
WHERE schemaname = 'public' 
  AND tablename IN ('ai_prompts', 'workflow_templates', 'conversations', 'knowledge_base')
ORDER BY tablename;

-- Check prompts are installed
SELECT 
  name,
  LENGTH(content) as content_length,
  metadata->>'model' as model
FROM ai_prompts
ORDER BY name;
```

**Expected output:**

```
Tables:
- ai_prompts           ✅ REQUIRED
- conversations        ✅ Optional
- knowledge_base       ✅ Optional
- workflow_templates   ✅ Optional

Prompts (5 required):
- agent_orchestration     ✅
- conversation_creator    ✅
- intent_classifier       ✅
- narrative_continuation  ✅
- response_synthesis      ✅
```

---

## Step 4: Configure Environment

Update your `.env` file:

```env
# Supabase Configuration (REQUIRED)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here
```

**Where to find these values:**
1. Go to Supabase Dashboard
2. Click on **Settings** → **API**
3. Copy:
   - **Project URL** → `SUPABASE_URL`
   - **anon/public key** → `SUPABASE_ANON_KEY`
   - **service_role key** → `SUPABASE_SERVICE_ROLE_KEY`

---

## Step 5: Test Connection

Start your backend:

```bash
cd "New folder"
npm start
```

**Look for these log messages:**

```
✅ PromptService initialized
✅ IntentRouter initialized with OpenAI
✅ Using intent_classifier prompt from Supabase
```

If you see:
```
❌ intent_classifier prompt not found in database
```

→ Go back to Step 2 and run the prompt INSERT script again.

---

## 🔍 What Each Table Does

### 1. `ai_prompts` (REQUIRED)
**Purpose**: Stores all OpenAI system prompts  
**Used by**: IntentRouter, ResponseBuilder, all services  
**Critical**: YES - system won't work without this

### 2. `workflow_templates` (Optional)
**Purpose**: Stores workflow templates for agent orchestration  
**Used by**: TemplateEngine  
**Fallback**: Uses default templates if table empty

### 3. `conversations` (Optional)
**Purpose**: Stores conversation history  
**Used by**: MemoryService  
**Fallback**: Uses in-memory cache only

### 4. `knowledge_base` (Optional)
**Purpose**: Stores user memories (short-term, long-term)  
**Used by**: MemoryService  
**Fallback**: Works without persistent memory

---

## 🛠️ Troubleshooting

### Error: "type 'vector' does not exist"

**Cause**: Your Supabase project doesn't have the pgvector extension enabled.

**Solution**: Use `supabase_setup_minimal.sql` instead of `supabase_setup.sql`. It doesn't require pgvector.

### Error: "relation 'ai_prompts' does not exist"

**Solution**: Run the CREATE TABLE commands from Step 2

### Error: "Prompt not found in database"

**Solution**: Run the INSERT commands from Step 2 to add prompts

### Error: "Failed to initialize Supabase client"

**Solution**: Check your `.env` file has correct Supabase credentials

### Prompts are in database but still getting errors

**Solution**: Restart your backend server:
```bash
# Stop server (Ctrl+C)
npm start
```

### Do I need pgvector?

**No!** pgvector is optional and only used for semantic template search. The system works perfectly fine without it using keyword search instead.

Use `supabase_setup_minimal.sql` if you don't have pgvector.

---

## 📝 Adding Custom Prompts

To add more prompts:

```sql
INSERT INTO ai_prompts (name, content, metadata) VALUES (
  'my_custom_prompt',
  'Your prompt content here with {{variables}}',
  '{"model": "gpt-4-turbo-preview", "temperature": 0.7, "max_tokens": 1000}'::jsonb
);
```

Then in your code:

```javascript
const prompt = await promptService.getPrompt('my_custom_prompt');
const populatedPrompt = promptService.populatePrompt(prompt.content, {
  variables: 'your values here'
});
```

---

## 🎯 Minimum Required Setup

If you're in a hurry, you ONLY need:

1. ✅ Create `ai_prompts` table
2. ✅ Insert 5 required prompts
3. ✅ Configure `.env` with Supabase credentials

Everything else is optional!

---

## ✅ Verification Checklist

- [ ] `ai_prompts` table created
- [ ] 5 prompts installed (run verification query)
- [ ] `.env` configured with Supabase credentials
- [ ] Backend starts without errors
- [ ] Logs show "✅ Using intent_classifier prompt from Supabase"

Once all checked, you're ready to go! 🚀

