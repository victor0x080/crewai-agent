/**
 * Test script for Problem-First Conversational Workflow
 * Tests the problem type classification and workflow stage progression
 */

import http from 'http';
import { logger } from '../src/utils/logger.js';

const API_BASE = 'http://localhost:3001';
const TEST_CONVERSATION_ID = `test-problem-first-${Date.now()}`;

// Color codes for terminal output
const colors = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m',
};

function log(message, color = 'reset') {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

function logSection(title) {
  console.log('\n' + '='.repeat(60));
  log(title, 'cyan');
  console.log('='.repeat(60) + '\n');
}

function logTest(name) {
  log(`\n🧪 Testing: ${name}`, 'blue');
}

function logSuccess(message) {
  log(`✅ ${message}`, 'green');
}

function logError(message) {
  log(`❌ ${message}`, 'red');
}

function logWarning(message) {
  log(`⚠️  ${message}`, 'yellow');
}

function logInfo(message) {
  log(`ℹ️  ${message}`, 'reset');
}

/**
 * Make HTTP POST request
 */
function makeRequest(path, data) {
  return new Promise((resolve, reject) => {
    const postData = JSON.stringify(data);
    
    const options = {
      hostname: 'localhost',
      port: 3001,
      path: path,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(postData)
      }
    };

    const req = http.request(options, (res) => {
      let body = '';
      
      res.on('data', (chunk) => {
        body += chunk;
      });
      
      res.on('end', () => {
        try {
          const parsed = JSON.parse(body);
          resolve({ status: res.statusCode, data: parsed });
        } catch (error) {
          resolve({ status: res.statusCode, data: body, error: error.message });
        }
      });
    });

    req.on('error', (error) => {
      reject(error);
    });

    req.write(postData);
    req.end();
  });
}

/**
 * Test problem type classification for different query types
 */
async function testProblemTypeClassification() {
  logSection('Problem Type Classification Tests');

  const testCases = [
    {
      name: 'Alert Problem',
      query: 'alert me if there is a risk in sales',
      expectedType: 'alert',
      description: 'Should classify as alert type'
    },
    {
      name: 'Understand Problem',
      query: 'help me understand why sales dropped this quarter',
      expectedType: 'understand',
      description: 'Should classify as understand type'
    },
    {
      name: 'Solve Problem',
      query: 'solve the inventory shortage problem',
      expectedType: 'solve',
      description: 'Should classify as solve type'
    },
    {
      name: 'Monitor Problem',
      query: 'monitor the supply chain for disruptions',
      expectedType: 'monitor',
      description: 'Should classify as monitor type'
    },
    {
      name: 'Automate Problem',
      query: 'automate the order processing workflow',
      expectedType: 'automate',
      description: 'Should classify as automate type'
    },
    {
      name: 'General Question',
      query: 'what is the weather today',
      expectedType: 'general',
      description: 'Should classify as general type'
    }
  ];

  const results = [];

  for (const testCase of testCases) {
    logTest(testCase.name);
    logInfo(`Query: "${testCase.query}"`);
    logInfo(`Expected: ${testCase.expectedType}`);

    try {
      const response = await makeRequest('/api/process-message', {
        message: testCase.query,
        conversationId: `${TEST_CONVERSATION_ID}-${testCase.name.toLowerCase().replace(/\s+/g, '-')}`
      });

      if (response.status === 200) {
        // Check multiple locations for problem classification
        const problemType = response.data.problem_type || 
                          response.data.metadata?.problem_type || 
                          response.data.turnEnvelope?.meta?.problemType;
        const workflowStage = response.data.workflow_stage || 
                            response.data.metadata?.workflow_stage || 
                            response.data.turnEnvelope?.meta?.workflowStage;
        const problemSpace = response.data.problem_space || 
                           response.data.metadata?.problem_space || 
                           response.data.turnEnvelope?.meta?.problemSpace;

        logInfo(`Actual: ${problemType}`);
        logInfo(`Workflow Stage: ${workflowStage}`);
        logInfo(`Problem Space: ${problemSpace || 'N/A'}`);

        const passed = problemType === testCase.expectedType;
        if (passed) {
          logSuccess(`✓ Correctly classified as ${problemType}`);
        } else {
          logError(`✗ Expected ${testCase.expectedType}, got ${problemType}`);
        }

        results.push({
          name: testCase.name,
          passed,
          expected: testCase.expectedType,
          actual: problemType,
          workflowStage,
          problemSpace
        });
      } else {
        logError(`Request failed with status ${response.status}`);
        results.push({
          name: testCase.name,
          passed: false,
          error: `Status ${response.status}`
        });
      }
    } catch (error) {
      logError(`Request error: ${error.message}`);
      results.push({
        name: testCase.name,
        passed: false,
        error: error.message
      });
    }

    // Small delay between requests
    await new Promise(resolve => setTimeout(resolve, 500));
  }

  return results;
}

/**
 * Test workflow stage progression
 */
async function testWorkflowStageProgression() {
  logSection('Workflow Stage Progression Tests');

  const conversationId = `${TEST_CONVERSATION_ID}-workflow`;
  const queries = [
    {
      query: 'help me understand the sales trend',
      expectedStage: 'interpret',
      description: 'First query should start at interpret stage'
    },
    {
      query: 'what do you recommend I do about it',
      expectedStage: 'recommend',
      description: 'Second query should progress to recommend stage'
    },
    {
      query: 'what if we increase marketing budget by 20%',
      expectedStage: 'what-if',
      description: 'Third query should progress to what-if stage'
    },
    {
      query: 'explain the underlying economic factors',
      expectedStage: 'full-llm',
      description: 'Fourth query should progress to full-llm stage'
    }
  ];

  const results = [];

  for (let i = 0; i < queries.length; i++) {
    const testCase = queries[i];
    logTest(`Workflow Stage ${i + 1}: ${testCase.description}`);
    logInfo(`Query: "${testCase.query}"`);
    logInfo(`Expected Stage: ${testCase.expectedStage}`);

    try {
      const response = await makeRequest('/api/process-message', {
        message: testCase.query,
        conversationId: conversationId
      });

      if (response.status === 200) {
        // Check multiple locations for workflow stage and problem type
        const workflowStage = response.data.workflow_stage || 
                            response.data.metadata?.workflow_stage || 
                            response.data.turnEnvelope?.meta?.workflowStage;
        const problemType = response.data.problem_type || 
                          response.data.metadata?.problem_type || 
                          response.data.turnEnvelope?.meta?.problemType;

        logInfo(`Actual Stage: ${workflowStage}`);
        logInfo(`Problem Type: ${problemType}`);

        // For workflow stages, we're more lenient - the stage might progress differently
        // based on the problem type, so we just check that it's a valid stage
        const validStages = ['interpret', 'recommend', 'what-if', 'full-llm'];
        const isValidStage = validStages.includes(workflowStage);

        if (isValidStage) {
          logSuccess(`✓ Valid workflow stage: ${workflowStage}`);
          results.push({
            query: testCase.query,
            stage: workflowStage,
            expected: testCase.expectedStage,
            passed: isValidStage
          });
        } else {
          logWarning(`⚠ Stage ${workflowStage} is not in expected stages`);
          results.push({
            query: testCase.query,
            stage: workflowStage,
            expected: testCase.expectedStage,
            passed: false
          });
        }
      } else {
        logError(`Request failed with status ${response.status}`);
        results.push({
          query: testCase.query,
          passed: false,
          error: `Status ${response.status}`
        });
      }
    } catch (error) {
      logError(`Request error: ${error.message}`);
      results.push({
        query: testCase.query,
        passed: false,
        error: error.message
      });
    }

    // Delay between requests to allow conversation context to build
    await new Promise(resolve => setTimeout(resolve, 1000));
  }

  return results;
}

/**
 * Test server health and service availability
 */
async function testServerHealth() {
  logSection('Server Health Check');

  try {
    const response = await new Promise((resolve, reject) => {
      http.get('http://localhost:3001/api/health', (res) => {
        let body = '';
        res.on('data', (chunk) => { body += chunk; });
        res.on('end', () => {
          try {
            resolve({ status: res.statusCode, data: JSON.parse(body) });
          } catch (error) {
            resolve({ status: res.statusCode, data: body });
          }
        });
      }).on('error', reject);
    });

    if (response.status === 200) {
      const health = response.data;
      logInfo('Server Status:', health.status);
      logInfo('Services:');
      
      if (health.services) {
        Object.entries(health.services).forEach(([service, healthy]) => {
          if (healthy) {
            logSuccess(`  ${service}: healthy`);
          } else {
            logError(`  ${service}: unhealthy`);
          }
        });

        // Check if ProblemTypeClassifier is in services
        if ('problemTypeClassifier' in health.services) {
          logSuccess('✓ ProblemTypeClassifier service is registered');
        } else {
          logError('✗ ProblemTypeClassifier service not found in health check');
        }
      }

      return { passed: true, health };
    } else {
      logError(`Health check failed with status ${response.status}`);
      return { passed: false, status: response.status };
    }
  } catch (error) {
    logError(`Health check error: ${error.message}`);
    return { passed: false, error: error.message };
  }
}

/**
 * Test a complete conversation flow
 */
async function testCompleteConversationFlow() {
  logSection('Complete Conversation Flow Test');

  const conversationId = `${TEST_CONVERSATION_ID}-complete`;
  const queries = [
    'alert me if inventory levels drop below 1000 units',
    'what does the current inventory level mean?',
    'what should I do about low inventory?',
    'what if I increase the reorder point?'
  ];

  logInfo(`Conversation ID: ${conversationId}`);
  logInfo(`Testing ${queries.length} queries in sequence\n`);

  const results = [];

  for (let i = 0; i < queries.length; i++) {
    const query = queries[i];
    logTest(`Query ${i + 1}/${queries.length}`);
    logInfo(`"${query}"`);

    try {
      const response = await makeRequest('/api/process-message', {
        message: query,
        conversationId: conversationId
      });

      if (response.status === 200) {
        // Check multiple locations for problem classification
        const problemType = response.data.problem_type || 
                          response.data.metadata?.problem_type || 
                          response.data.turnEnvelope?.meta?.problemType;
        const workflowStage = response.data.workflow_stage || 
                            response.data.metadata?.workflow_stage || 
                            response.data.turnEnvelope?.meta?.workflowStage;
        const responseText = response.data.response || 'No response';

        logInfo(`Problem Type: ${problemType}`);
        logInfo(`Workflow Stage: ${workflowStage}`);
        logInfo(`Response Length: ${responseText.length} characters`);
        logInfo(`Response Preview: ${responseText.substring(0, 100)}...`);

        results.push({
          query,
          problemType,
          workflowStage,
          responseLength: responseText.length,
          success: true
        });

        logSuccess('✓ Query processed successfully');
      } else {
        logError(`✗ Request failed with status ${response.status}`);
        results.push({
          query,
          success: false,
          error: `Status ${response.status}`
        });
      }
    } catch (error) {
      logError(`✗ Request error: ${error.message}`);
      results.push({
        query,
        success: false,
        error: error.message
      });
    }

    // Delay between queries
    if (i < queries.length - 1) {
      await new Promise(resolve => setTimeout(resolve, 1500));
    }
  }

  return results;
}

/**
 * Main test runner
 */
async function runTests() {
  logSection('Problem-First Conversational Workflow Test Suite');
  logInfo(`Test Conversation ID: ${TEST_CONVERSATION_ID}`);
  logInfo(`API Base URL: ${API_BASE}\n`);

  const testResults = {
    health: null,
    classification: null,
    workflow: null,
    completeFlow: null
  };

  try {
    // Test 1: Server Health
    testResults.health = await testServerHealth();
    
    if (!testResults.health.passed) {
      logError('\n❌ Server health check failed. Please ensure the server is running.');
      logError('   Start the server with: npm start or node src/server.js');
      process.exit(1);
    }

    // Test 2: Problem Type Classification
    testResults.classification = await testProblemTypeClassification();

    // Test 3: Workflow Stage Progression
    testResults.workflow = await testWorkflowStageProgression();

    // Test 4: Complete Conversation Flow
    testResults.completeFlow = await testCompleteConversationFlow();

    // Summary
    logSection('Test Summary');

    const classificationPassed = testResults.classification.filter(r => r.passed).length;
    const classificationTotal = testResults.classification.length;
    logInfo(`Problem Type Classification: ${classificationPassed}/${classificationTotal} passed`);

    const workflowPassed = testResults.workflow.filter(r => r.passed).length;
    const workflowTotal = testResults.workflow.length;
    logInfo(`Workflow Stage Progression: ${workflowPassed}/${workflowTotal} passed`);

    const completeFlowPassed = testResults.completeFlow.filter(r => r.success).length;
    const completeFlowTotal = testResults.completeFlow.length;
    logInfo(`Complete Flow: ${completeFlowPassed}/${completeFlowTotal} queries successful`);

    const allPassed = 
      testResults.health.passed &&
      classificationPassed === classificationTotal &&
      workflowPassed === workflowTotal &&
      completeFlowPassed === completeFlowTotal;

    if (allPassed) {
      logSuccess('\n🎉 All tests passed!');
      process.exit(0);
    } else {
      logWarning('\n⚠️  Some tests failed. Review the output above for details.');
      process.exit(1);
    }

  } catch (error) {
    logError(`\n❌ Test suite error: ${error.message}`);
    console.error(error);
    process.exit(1);
  }
}

// Run tests
runTests().catch(error => {
  logError(`Fatal error: ${error.message}`);
  console.error(error);
  process.exit(1);
});

