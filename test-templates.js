import dotenv from 'dotenv';
import { createClient } from '@supabase/supabase-js';

dotenv.config();

const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_ANON_KEY
);

console.log('Testing template search...\n');

// Test 1: Get all templates
const { data: allTemplates, error: allError } = await supabase
  .from('workflow_templates')
  .select('name, domain, template_schema')
  .limit(20);

if (allError) {
  console.log('❌ Error getting templates:', allError.message);
} else {
  console.log(`✅ Found ${allTemplates.length} templates in Supabase:\n`);
  allTemplates.forEach((t, i) => {
    const agents = t.template_schema?.agents || [];
    console.log(`${i+1}. ${t.name} (${t.domain})`);
    console.log(`   Agents: ${agents.join(', ')}`);
  });
}

console.log('\n' + '='.repeat(60) + '\n');

// Test 2: Search for "forecast" templates
const { data: forecastTemplates, error: forecastError } = await supabase
  .from('workflow_templates')
  .select('*')
  .or('name.ilike.%forecast%,description.ilike.%forecast%')
  .limit(5);

if (forecastError) {
  console.log('❌ Error searching forecast templates:', forecastError.message);
} else {
  console.log(`✅ Found ${forecastTemplates.length} templates matching "forecast":\n`);
  forecastTemplates.forEach((t, i) => {
    const agents = t.template_schema?.agents || [];
    console.log(`${i+1}. ${t.name}`);
    console.log(`   Domain: ${t.domain}`);
    console.log(`   Agents: ${agents.join(', ')}`);
    console.log(`   Description: ${t.description?.substring(0, 80)}...`);
    console.log('');
  });
}

process.exit(0);

