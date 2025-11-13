/**
 * Direct test of Supabase template search
 */

import { createClient } from '@supabase/supabase-js';
import dotenv from 'dotenv';

dotenv.config();

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseAnonKey = process.env.SUPABASE_ANON_KEY;
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
const supabaseKey = supabaseServiceKey || supabaseAnonKey;

console.log('\n🧪 Testing Supabase Template Search\n');
console.log('Configuration:');
console.log(`  URL: ${supabaseUrl}`);
console.log(`  Anon Key: ${supabaseAnonKey ? '✅ Set' : '❌ Missing'}`);
console.log(`  Service Key: ${supabaseServiceKey ? '✅ Set' : '❌ Missing'}`);
console.log(`  Effective Key: ${supabaseKey ? '✅ Set' : '❌ Missing'}\n`);

if (!supabaseUrl || !supabaseKey) {
  console.error('❌ Missing Supabase credentials!');
  process.exit(1);
}

const supabase = createClient(supabaseUrl, supabaseKey);

async function testTemplateSearch() {
  console.log('📝 Test 1: Count all templates');
  const { data: allTemplates, error: countError } = await supabase
    .from('workflow_templates')
    .select('id, name');
  
  if (countError) {
    console.error('❌ Error:', countError);
  } else {
    console.log(`✅ Found ${allTemplates.length} templates:`);
    allTemplates.forEach(t => console.log(`   - ${t.name} (ID: ${t.id})`));
  }

  console.log('\n📝 Test 2: Search for "demand" keyword');
  const { data: demandResults, error: demandError } = await supabase
    .from('workflow_templates')
    .select('*')
    .ilike('description', '%demand%');
  
  if (demandError) {
    console.error('❌ Error:', demandError);
  } else {
    console.log(`✅ Found ${demandResults.length} templates matching "demand":`);
    demandResults.forEach(t => {
      console.log(`   - ${t.name}`);
      console.log(`     Description: ${t.description.substring(0, 80)}...`);
      if (t.template_schema?.keywords) {
        console.log(`     Keywords: ${t.template_schema.keywords.join(', ')}`);
      }
    });
  }

  console.log('\n📝 Test 3: Search for "forecast" keyword');
  const { data: forecastResults, error: forecastError } = await supabase
    .from('workflow_templates')
    .select('*')
    .ilike('name', '%forecast%');
  
  if (forecastError) {
    console.error('❌ Error:', forecastError);
  } else {
    console.log(`✅ Found ${forecastResults.length} templates matching "forecast" in name:`);
    forecastResults.forEach(t => {
      console.log(`   - ${t.name}`);
      console.log(`     Agents: ${t.template_schema?.agents?.join(', ') || 'N/A'}`);
    });
  }

  console.log('\n📝 Test 4: Complex OR search (like TemplateEngine uses)');
  const intent = 'SIMULATION';
  const keywords = 'what is the demand forecast for nike air max in q3 2025';
  
  console.log(`  Intent: ${intent}`);
  console.log(`  Keywords: ${keywords}`);
  
  const { data: complexResults, error: complexError } = await supabase
    .from('workflow_templates')
    .select('*')
    .or(`name.ilike.%${intent}%,description.ilike.%${keywords.substring(0, 50)}%,template_schema->>keywords::text.ilike.%${keywords.substring(0, 30)}%`)
    .limit(5);
  
  if (complexError) {
    console.error('❌ Error:', complexError);
    console.error('   Details:', JSON.stringify(complexError, null, 2));
  } else {
    console.log(`✅ Found ${complexResults.length} templates:`);
    complexResults.forEach(t => {
      console.log(`   - ${t.name} (relevance calculation needed)`);
    });
  }

  console.log('\n✅ Test complete!\n');
}

testTemplateSearch().catch(err => {
  console.error('\n❌ Test failed:', err);
  process.exit(1);
});

