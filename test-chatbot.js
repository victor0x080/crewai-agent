/**
 * Test script for LangChain Chatbot Service
 * Tests the chatbot functionality with Pinecone memory
 */

import http from 'http';
import { logger } from './src/utils/logger.js';

const SERVER_URL = process.env.SERVER_URL || 'http://localhost:3001';
const TEST_CONVERSATION_ID = `test-chatbot-${Date.now()}`;

// Colors for console output
const colors = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m'
};

function log(message, color = 'reset') {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

function makeRequest(path, method = 'GET', body = null) {
  return new Promise((resolve, reject) => {
    const url = new URL(path, SERVER_URL);
    const options = {
      hostname: url.hostname,
      port: url.port || 3002,
      path: url.pathname,
      method,
      headers: {
        'Content-Type': 'application/json'
      }
    };

    const req = http.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => {
        try {
          const parsed = data ? JSON.parse(data) : {};
          resolve({ status: res.statusCode, headers: res.headers, body: parsed });
        } catch (e) {
          resolve({ status: res.statusCode, headers: res.headers, body: data });
        }
      });
    });

    req.on('error', reject);
    
    if (body) {
      req.write(JSON.stringify(body));
    }
    
    req.end();
  });
}

async function testHealthCheck() {
  log('\n🧪 Test 1: Health Check', 'cyan');
  try {
    const response = await makeRequest('/api/health');
    if (response.status === 200 || response.status === 503) {
      log(`   ✅ Status: ${response.status}`, 'green');
      if (response.body.services) {
        log(`   📊 Services:`, 'blue');
        Object.entries(response.body.services).forEach(([name, healthy]) => {
          const status = healthy ? '✅' : '❌';
          log(`      ${status} ${name}: ${healthy}`, healthy ? 'green' : 'yellow');
        });
        if (response.body.services.langChainChatbot !== undefined) {
          log(`   ✅ LangChain Chatbot service found in health check`, 'green');
        } else {
          log(`   ⚠️  LangChain Chatbot service not found in health check`, 'yellow');
        }
      }
      return true;
    } else {
      log(`   ❌ Unexpected status: ${response.status}`, 'red');
      return false;
    }
  } catch (error) {
    log(`   ❌ Error: ${error.message}`, 'red');
    return false;
  }
}

async function testChatbotMessage(message, conversationId, testNumber) {
  log(`\n🧪 Test ${testNumber}: Chatbot Message Processing`, 'cyan');
  log(`   Message: "${message}"`, 'blue');
  log(`   Conversation ID: ${conversationId}`, 'blue');
  
  try {
    const startTime = Date.now();
    const response = await makeRequest('/api/process-message', 'POST', {
      message,
      conversationId,
      context: {
        userId: 'test-user',
        tenantId: 'test-tenant'
      }
    });
    const elapsed = Date.now() - startTime;
    
    if (response.status === 200) {
      log(`   ✅ Status: 200 (${elapsed}ms)`, 'green');
      
      // Check response structure
      if (response.body.response) {
        log(`   ✅ Response received: "${response.body.response.substring(0, 100)}${response.body.response.length > 100 ? '...' : ''}"`, 'green');
      } else {
        log(`   ⚠️  No response field in body`, 'yellow');
      }
      
      if (response.body.turnEnvelope) {
        log(`   ✅ TurnEnvelope present`, 'green');
        if (response.body.turnEnvelope.meta) {
          log(`   📊 Mode: ${response.body.turnEnvelope.meta.mode || 'unknown'}`, 'blue');
          log(`   📊 Memory Backend: ${response.body.turnEnvelope.meta.memoryBackend || 'unknown'}`, 'blue');
        }
      } else {
        log(`   ⚠️  No turnEnvelope in response`, 'yellow');
      }
      
      if (response.body.conversationId) {
        log(`   ✅ Conversation ID preserved: ${response.body.conversationId}`, 'green');
      }
      
      if (response.body.processingTime) {
        log(`   ⏱️  Processing time: ${response.body.processingTime}ms`, 'blue');
      }
      
      return { success: true, response: response.body };
    } else {
      log(`   ❌ Unexpected status: ${response.status}`, 'red');
      log(`   Response: ${JSON.stringify(response.body, null, 2)}`, 'red');
      return { success: false, response: response.body };
    }
  } catch (error) {
    log(`   ❌ Error: ${error.message}`, 'red');
    if (error.stack) {
      log(`   Stack: ${error.stack}`, 'red');
    }
    return { success: false, error: error.message };
  }
}

async function testConversationHistory() {
  log('\n🧪 Test 4: Conversation History', 'cyan');
  
  const conversationId = TEST_CONVERSATION_ID;
  
  // Send first message
  log('   Sending first message...', 'blue');
  const result1 = await testChatbotMessage(
    'Hello, my name is Alice. What is 2+2?',
    conversationId,
    4
  );
  
  if (!result1.success) {
    log('   ❌ First message failed, skipping history test', 'red');
    return false;
  }
  
  // Wait a bit
  await new Promise(resolve => setTimeout(resolve, 1000));
  
  // Send second message that references the first
  log('   Sending second message (should remember name)...', 'blue');
  const result2 = await testChatbotMessage(
    'What is my name?',
    conversationId,
    4
  );
  
  if (result2.success) {
    const responseText = result2.response?.response || '';
    if (responseText.toLowerCase().includes('alice')) {
      log('   ✅ Chatbot remembered the name from previous message!', 'green');
      return true;
    } else {
      log('   ⚠️  Chatbot response does not seem to remember the name', 'yellow');
      log(`   Response: "${responseText.substring(0, 200)}"`, 'yellow');
      return false;
    }
  } else {
    log('   ❌ Second message failed', 'red');
    return false;
  }
}

async function runTests() {
  log('\n═══════════════════════════════════════════════════════', 'cyan');
  log('🧪 LangChain Chatbot Service Test Suite', 'cyan');
  log('═══════════════════════════════════════════════════════\n', 'cyan');
  
  const results = {
    passed: 0,
    failed: 0,
    warnings: 0
  };
  
  // Test 1: Health Check
  const healthOk = await testHealthCheck();
  if (healthOk) results.passed++;
  else results.failed++;
  
  // Test 2: Simple message
  const test2 = await testChatbotMessage(
    'What is artificial intelligence?',
    `${TEST_CONVERSATION_ID}-2`,
    2
  );
  if (test2.success) results.passed++;
  else results.failed++;
  
  // Test 3: Another message
  const test3 = await testChatbotMessage(
    'Explain machine learning in simple terms',
    `${TEST_CONVERSATION_ID}-3`,
    3
  );
  if (test3.success) results.passed++;
  else results.failed++;
  
  // Test 4: Conversation history
  const historyOk = await testConversationHistory();
  if (historyOk) results.passed++;
  else results.warnings++;
  
  // Summary
  log('\n═══════════════════════════════════════════════════════', 'cyan');
  log('📊 Test Summary', 'cyan');
  log('═══════════════════════════════════════════════════════', 'cyan');
  log(`   ✅ Passed: ${results.passed}`, 'green');
  log(`   ❌ Failed: ${results.failed}`, results.failed > 0 ? 'red' : 'green');
  log(`   ⚠️  Warnings: ${results.warnings}`, results.warnings > 0 ? 'yellow' : 'green');
  log('═══════════════════════════════════════════════════════\n', 'cyan');
  
  if (results.failed === 0) {
    log('✅ All critical tests passed!', 'green');
    process.exit(0);
  } else {
    log('❌ Some tests failed. Please check the errors above.', 'red');
    process.exit(1);
  }
}

// Check if server is running
log('🔍 Checking if server is running...', 'blue');
makeRequest('/api/health')
  .then(() => {
    log('✅ Server is running\n', 'green');
    runTests().catch(error => {
      log(`\n❌ Test suite error: ${error.message}`, 'red');
      if (error.stack) {
        log(`Stack: ${error.stack}`, 'red');
      }
      process.exit(1);
    });
  })
  .catch(error => {
    log(`\n❌ Cannot connect to server at ${SERVER_URL}`, 'red');
    log('   Make sure the server is running: npm start', 'yellow');
    log(`   Error: ${error.message}`, 'red');
    process.exit(1);
  });

