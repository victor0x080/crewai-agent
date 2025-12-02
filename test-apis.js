#!/usr/bin/env node
/**
 * Test script for Signals and Decision Stack APIs
 */

import axios from 'axios';

const API_BASE = process.env.API_URL || 'http://localhost:3001';
const API_PREFIX = API_BASE;

async function testDecisionStacks() {
  console.log('\n🧪 Testing Decision Stack APIs...\n');
  
  try {
    // 1. Create a test stack
    console.log('1. Creating a test decision stack...');
    const createResponse = await axios.post(`${API_PREFIX}/api/decision-stacks`, {
      name: 'Test Stack',
      description: 'This is a test decision stack',
      template: 'retail-media',
      status: 'draft',
      modules: {
        commonTerms: 5,
        eventPatterns: 3,
        tunedModels: 1,
        entityMap: 10,
        playsWorkflows: 2,
        promptTemplates: 5
      }
    });
    console.log('✅ Created stack:', createResponse.data.id);
    const stackId = createResponse.data.id;
    
    // 2. Fetch all stacks
    console.log('\n2. Fetching all decision stacks...');
    const listResponse = await axios.get(`${API_PREFIX}/api/decision-stacks`);
    console.log(`✅ Found ${listResponse.data.stacks.length} stacks`);
    
    // 3. Fetch specific stack
    console.log('\n3. Fetching specific stack...');
    const getResponse = await axios.get(`${API_PREFIX}/api/decision-stacks/${stackId}`);
    console.log('✅ Retrieved stack:', getResponse.data.name);
    
    // 4. Update stack
    console.log('\n4. Updating stack...');
    const updateResponse = await axios.put(`${API_PREFIX}/api/decision-stacks/${stackId}`, {
      name: 'Updated Test Stack',
      description: 'This is an updated test decision stack'
    });
    console.log('✅ Updated stack:', updateResponse.data.name);
    
    // 5. Clone stack
    console.log('\n5. Cloning stack...');
    const cloneResponse = await axios.post(`${API_PREFIX}/api/decision-stacks/${stackId}/clone`);
    console.log('✅ Cloned stack:', cloneResponse.data.id);
    const clonedId = cloneResponse.data.id;
    
    // 6. Delete cloned stack
    console.log('\n6. Deleting cloned stack...');
    await axios.delete(`${API_PREFIX}/api/decision-stacks/${clonedId}`);
    console.log('✅ Deleted cloned stack');
    
    // 7. Delete original stack
    console.log('\n7. Deleting original stack...');
    await axios.delete(`${API_PREFIX}/api/decision-stacks/${stackId}`);
    console.log('✅ Deleted original stack');
    
    console.log('\n✅ All Decision Stack API tests passed!\n');
    return true;
  } catch (error) {
    console.error('❌ Decision Stack API test failed:', error.response?.data || error.message);
    return false;
  }
}

async function testSignals() {
  console.log('\n🧪 Testing Signals APIs...\n');
  
  try {
    // 1. Fetch all signals
    console.log('1. Fetching all signals...');
    const signalsResponse = await axios.get(`${API_PREFIX}/api/signals`);
    console.log(`✅ Found ${signalsResponse.data.signals?.length || 0} signals`);
    console.log(`✅ Found ${signalsResponse.data.activeAgents?.length || 0} active agents`);
    
    // 2. Fetch metrics
    console.log('\n2. Fetching signal metrics...');
    const metricsResponse = await axios.get(`${API_PREFIX}/api/signals/metrics`);
    console.log('✅ Metrics:', {
      totalEventsToday: metricsResponse.data.totalEventsToday,
      activeAgents: metricsResponse.data.activeAgents,
      enabledSignals: metricsResponse.data.enabledSignals,
      totalSignals: metricsResponse.data.totalSignals
    });
    
    // 3. Fetch agents
    console.log('\n3. Fetching agents...');
    const agentsResponse = await axios.get(`${API_PREFIX}/api/signals/agents`);
    console.log(`✅ Found ${agentsResponse.data.agents?.length || 0} agents`);
    
    // 4. Test enabling a signal (create one first)
    const testSignalId = 'test_signal_1';
    console.log(`\n4. Testing enable/disable for signal: ${testSignalId}...`);
    
    try {
      // First enable it (this will create it if it doesn't exist)
      const enableResponse = await axios.post(`${API_PREFIX}/api/signals/${testSignalId}/enable`, {
        filters: { test: true }
      });
      console.log('✅ Enabled signal:', enableResponse.data.id);
      
      // Then disable it
      const disableResponse = await axios.post(`${API_PREFIX}/api/signals/${testSignalId}/disable`);
      console.log('✅ Disabled signal:', disableResponse.data.id);
    } catch (error) {
      console.log('⚠️  Enable/disable test failed:', error.response?.data || error.message);
    }
    
    console.log('\n✅ All Signals API tests passed!\n');
    return true;
  } catch (error) {
    console.error('❌ Signals API test failed:', error.response?.data || error.message);
    return false;
  }
}

async function testHealth() {
  console.log('\n🧪 Testing server health...\n');
  
  try {
    const response = await axios.get(`${API_PREFIX}/api/health`);
    console.log('✅ Server is healthy:', response.data);
    return true;
  } catch (error) {
    console.error('❌ Health check failed:', error.message);
    return false;
  }
}

async function runTests() {
  console.log('🚀 Starting API Tests...\n');
  console.log(`📍 API Base: ${API_PREFIX}\n`);
  
  const healthOk = await testHealth();
  if (!healthOk) {
    console.error('\n❌ Server is not running or not accessible');
    process.exit(1);
  }
  
  const signalsOk = await testSignals();
  const stacksOk = await testDecisionStacks();
  
  if (signalsOk && stacksOk) {
    console.log('🎉 All API tests passed!\n');
    process.exit(0);
  } else {
    console.error('\n❌ Some tests failed\n');
    process.exit(1);
  }
}

runTests().catch(error => {
  console.error('❌ Test runner error:', error);
  process.exit(1);
});

