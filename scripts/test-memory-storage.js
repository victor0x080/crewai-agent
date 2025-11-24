#!/usr/bin/env node
/**
 * Test Memory Storage
 * Verifies that memory is being stored in Supabase knowledge_base table
 */

import { createClient } from '@supabase/supabase-js';
import dotenv from 'dotenv';

dotenv.config();

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseKey) {
  console.error('❌ Missing SUPABASE_URL or SUPABASE_ANON_KEY/SERVICE_ROLE_KEY');
  process.exit(1);
}

const supabase = createClient(supabaseUrl, supabaseKey);

async function testMemoryStorage() {
  console.log('🔍 Testing Memory Storage...\n');

  // Test 1: Check if knowledge_base table exists
  console.log('1. Checking knowledge_base table...');
  const { data: tables, error: tableError } = await supabase
    .from('knowledge_base')
    .select('*')
    .limit(1);

  if (tableError) {
    console.error('❌ knowledge_base table error:', tableError.message);
    console.error('   Code:', tableError.code);
    console.error('   Details:', tableError.details);
    console.error('   Hint:', tableError.hint);
    return;
  }
  console.log('✅ knowledge_base table exists\n');

  // Test 2: Check recent memories
  console.log('2. Checking recent memories...');
  const { data: recentMemories, error: memoryError } = await supabase
    .from('knowledge_base')
    .select('*')
    .order('created_at', { ascending: false })
    .limit(10);

  if (memoryError) {
    console.error('❌ Error querying memories:', memoryError.message);
    return;
  }

  console.log(`✅ Found ${recentMemories?.length || 0} recent memories\n`);

  if (recentMemories && recentMemories.length > 0) {
    console.log('Recent memories:');
    recentMemories.forEach((mem, idx) => {
      console.log(`\n  ${idx + 1}. Memory ID: ${mem.id}`);
      console.log(`     User ID: ${mem.user_id}`);
      console.log(`     Conversation ID: ${mem.conversation_id || 'N/A'}`);
      console.log(`     Type: ${mem.memory_type}`);
      console.log(`     Content: ${mem.content?.substring(0, 100)}...`);
      console.log(`     Created: ${mem.created_at}`);
    });
  } else {
    console.log('⚠️  No memories found in knowledge_base table');
    console.log('   This could mean:');
    console.log('   - Memory storage is not being called');
    console.log('   - Memory storage is failing silently');
    console.log('   - No queries have been processed yet');
  }

  // Test 3: Check by user_id
  console.log('\n3. Testing query by user_id...');
  const testUserId = process.argv[2] || 'anonymous';
  console.log(`   Searching for user_id: ${testUserId}`);
  
  const { data: userMemories, error: userError } = await supabase
    .from('knowledge_base')
    .select('*')
    .eq('user_id', testUserId)
    .order('created_at', { ascending: false })
    .limit(5);

  if (userError) {
    console.error('❌ Error querying by user_id:', userError.message);
  } else {
    console.log(`✅ Found ${userMemories?.length || 0} memories for user ${testUserId}`);
    if (userMemories && userMemories.length > 0) {
      userMemories.forEach((mem) => {
        console.log(`   - ${mem.memory_type}: ${mem.content?.substring(0, 60)}...`);
      });
    }
  }

  // Test 4: Check conversations table
  console.log('\n4. Checking conversations table...');
  const { data: conversations, error: convError } = await supabase
    .from('conversations')
    .select('*')
    .order('created_at', { ascending: false })
    .limit(5);

  if (convError) {
    console.error('❌ Error querying conversations:', convError.message);
  } else {
    console.log(`✅ Found ${conversations?.length || 0} recent conversations`);
    if (conversations && conversations.length > 0) {
      conversations.forEach((conv) => {
        console.log(`   - ${conv.id} (user: ${conv.user_id}): ${conv.message?.substring(0, 60)}...`);
      });
    }
  }

  console.log('\n✅ Memory storage test complete!');
}

testMemoryStorage().catch(console.error);

