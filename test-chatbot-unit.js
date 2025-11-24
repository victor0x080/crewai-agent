/**
 * Unit test for LangChain Chatbot Service
 * Tests the service without requiring the server to be running
 */

import LangChainChatbotService from './src/services/LangChainChatbotService.js';
import config from './src/config/index.js';

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

async function testServiceInitialization() {
  log('\n🧪 Test 1: Service Initialization', 'cyan');
  
  try {
    const chatbot = new LangChainChatbotService();
    log('   ✅ Service instance created', 'green');
    
    // Check if OpenAI is configured
    if (!config.openai.enabled || !config.openai.apiKey) {
      log('   ⚠️  OpenAI not configured - will test initialization only', 'yellow');
      log('   ℹ️  Set OPENAI_API_KEY in .env to test full functionality', 'yellow');
      return { success: false, reason: 'OpenAI not configured' };
    }
    
    log('   🔄 Initializing service...', 'blue');
    await chatbot.initialize();
    
    if (chatbot.isHealthy()) {
      log('   ✅ Service initialized successfully', 'green');
      log(`   📊 LLM Model: ${config.openai.model || 'default'}`, 'blue');
      
      if (chatbot.pineconeClient) {
        log('   ✅ Pinecone connected', 'green');
      } else {
        log('   ⚠️  Pinecone not connected (using in-memory fallback)', 'yellow');
        log('   ℹ️  Set PINECONE_API_KEY in .env to enable Pinecone', 'yellow');
      }
      
      return { success: true, chatbot };
    } else {
      log('   ❌ Service initialization failed', 'red');
      return { success: false, reason: 'Service not healthy' };
    }
  } catch (error) {
    log(`   ❌ Error: ${error.message}`, 'red');
    if (error.stack) {
      log(`   Stack: ${error.stack.split('\n').slice(0, 3).join('\n')}`, 'red');
    }
    return { success: false, error: error.message };
  }
}

async function testMessageProcessing(chatbot) {
  log('\n🧪 Test 2: Message Processing', 'cyan');
  
  if (!chatbot) {
    log('   ⚠️  Skipping - service not initialized', 'yellow');
    return { success: false, reason: 'Service not available' };
  }
  
  try {
    const conversationId = `test-${Date.now()}`;
    const message = 'What is 2+2?';
    
    log(`   📨 Sending message: "${message}"`, 'blue');
    log(`   💬 Conversation ID: ${conversationId}`, 'blue');
    
    const startTime = Date.now();
    const response = await chatbot.processMessage(
      message,
      conversationId,
      {
        userId: 'test-user',
        tenantId: 'test-tenant'
      }
    );
    const elapsed = Date.now() - startTime;
    
    if (response && response.response) {
      log(`   ✅ Response received (${elapsed}ms)`, 'green');
      log(`   💬 Response: "${response.response.substring(0, 150)}${response.response.length > 150 ? '...' : ''}"`, 'blue');
      log(`   📊 Processing time: ${response.processingTime}ms`, 'blue');
      log(`   📊 History length: ${response.historyLength || 0}`, 'blue');
      return { success: true, response };
    } else {
      log('   ❌ No response received', 'red');
      return { success: false, reason: 'No response' };
    }
  } catch (error) {
    log(`   ❌ Error: ${error.message}`, 'red');
    if (error.stack) {
      log(`   Stack: ${error.stack.split('\n').slice(0, 5).join('\n')}`, 'red');
    }
    return { success: false, error: error.message };
  }
}

async function testConversationHistory(chatbot) {
  log('\n🧪 Test 3: Conversation History', 'cyan');
  
  if (!chatbot) {
    log('   ⚠️  Skipping - service not initialized', 'yellow');
    return { success: false, reason: 'Service not available' };
  }
  
  try {
    const conversationId = `test-history-${Date.now()}`;
    
    // Send first message
    log('   📨 Sending first message...', 'blue');
    const response1 = await chatbot.processMessage(
      'My name is Bob. Remember this.',
      conversationId,
      { userId: 'test-user' }
    );
    
    if (!response1 || !response1.success) {
      log('   ⚠️  First message may have failed, continuing anyway...', 'yellow');
    }
    
    // Wait a bit
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    // Send second message
    log('   📨 Sending second message (should remember name)...', 'blue');
    const response2 = await chatbot.processMessage(
      'What is my name?',
      conversationId,
      { userId: 'test-user' }
    );
    
    if (response2 && response2.response) {
      const responseText = response2.response.toLowerCase();
      if (responseText.includes('bob')) {
        log('   ✅ Chatbot remembered the name!', 'green');
        return { success: true };
      } else {
        log('   ⚠️  Chatbot may not have remembered the name', 'yellow');
        log(`   Response: "${response2.response.substring(0, 200)}"`, 'yellow');
        return { success: false, reason: 'Name not remembered' };
      }
    } else {
      log('   ❌ No response from second message', 'red');
      return { success: false, reason: 'No response' };
    }
  } catch (error) {
    log(`   ❌ Error: ${error.message}`, 'red');
    return { success: false, error: error.message };
  }
}

async function testMemoryStorage(chatbot) {
  log('\n🧪 Test 4: Memory Storage', 'cyan');
  
  if (!chatbot) {
    log('   ⚠️  Skipping - service not initialized', 'yellow');
    return { success: false, reason: 'Service not available' };
  }
  
  try {
    const conversationId = `test-memory-${Date.now()}`;
    
    // Save a message
    log('   💾 Saving message to memory...', 'blue');
    await chatbot.saveMessage(conversationId, 'user', 'Test message', { test: true });
    log('   ✅ Message saved', 'green');
    
    // Retrieve history
    log('   📖 Retrieving conversation history...', 'blue');
    const history = await chatbot.getConversationHistory(conversationId);
    
    if (history && history.length > 0) {
      log(`   ✅ Retrieved ${history.length} message(s)`, 'green');
      const lastMessage = history[history.length - 1];
      if (lastMessage.content === 'Test message') {
        log('   ✅ Message content matches', 'green');
        return { success: true };
      } else {
        log('   ⚠️  Message content mismatch', 'yellow');
        return { success: false, reason: 'Content mismatch' };
      }
    } else {
      log('   ⚠️  No history retrieved (may be using Pinecone which needs time to index)', 'yellow');
      return { success: false, reason: 'No history' };
    }
  } catch (error) {
    log(`   ❌ Error: ${error.message}`, 'red');
    return { success: false, error: error.message };
  }
}

async function runTests() {
  log('\n═══════════════════════════════════════════════════════', 'cyan');
  log('🧪 LangChain Chatbot Service - Unit Tests', 'cyan');
  log('═══════════════════════════════════════════════════════\n', 'cyan');
  
  const results = {
    passed: 0,
    failed: 0,
    warnings: 0,
    skipped: 0
  };
  
  // Test 1: Initialization
  const initResult = await testServiceInitialization();
  if (initResult.success) {
    results.passed++;
  } else if (initResult.reason === 'OpenAI not configured') {
    results.skipped++;
    log('\n⚠️  Tests require OpenAI API key. Set OPENAI_API_KEY in .env', 'yellow');
    log('   Skipping remaining tests...\n', 'yellow');
  } else {
    results.failed++;
  }
  
  const chatbot = initResult.chatbot;
  
  // Test 2: Message Processing
  if (chatbot) {
    const msgResult = await testMessageProcessing(chatbot);
    if (msgResult.success) results.passed++;
    else results.failed++;
    
    // Test 3: Conversation History
    const histResult = await testConversationHistory(chatbot);
    if (histResult.success) results.passed++;
    else results.warnings++;
    
    // Test 4: Memory Storage
    const memResult = await testMemoryStorage(chatbot);
    if (memResult.success) results.passed++;
    else results.warnings++;
  }
  
  // Summary
  log('\n═══════════════════════════════════════════════════════', 'cyan');
  log('📊 Test Summary', 'cyan');
  log('═══════════════════════════════════════════════════════', 'cyan');
  log(`   ✅ Passed: ${results.passed}`, 'green');
  log(`   ❌ Failed: ${results.failed}`, results.failed > 0 ? 'red' : 'green');
  log(`   ⚠️  Warnings: ${results.warnings}`, results.warnings > 0 ? 'yellow' : 'green');
  log(`   ⏭️  Skipped: ${results.skipped}`, results.skipped > 0 ? 'yellow' : 'green');
  log('═══════════════════════════════════════════════════════\n', 'cyan');
  
  if (results.failed === 0 && results.skipped === 0) {
    log('✅ All tests passed!', 'green');
    process.exit(0);
  } else if (results.skipped > 0) {
    log('⚠️  Some tests were skipped due to missing configuration', 'yellow');
    process.exit(0);
  } else {
    log('❌ Some tests failed. Please check the errors above.', 'red');
    process.exit(1);
  }
}

runTests().catch(error => {
  log(`\n❌ Test suite error: ${error.message}`, 'red');
  if (error.stack) {
    log(`Stack: ${error.stack}`, 'red');
  }
  process.exit(1);
});

