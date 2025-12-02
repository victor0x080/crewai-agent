/**
 * Test script for WorkflowRequirementTracker
 * Tests requirement tracking, completion detection, and decision recording
 */

import http from 'http';

const API_BASE = 'http://localhost:3001';
const TEST_CONVERSATION_ID = `test-req-tracking-${Date.now()}`;

// Color codes
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

function logInfo(message) {
  log(`ℹ️  ${message}`, 'reset');
}

/**
 * Make HTTP request
 */
function makeRequest(method, path, data = null) {
  return new Promise((resolve, reject) => {
    const postData = data ? JSON.stringify(data) : null;
    
    const options = {
      hostname: 'localhost',
      port: 3001,
      path: path,
      method: method,
      headers: {
        'Content-Type': 'application/json'
      }
    };

    if (postData) {
      options.headers['Content-Length'] = Buffer.byteLength(postData);
    }

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
          resolve({ status: res.statusCode, data: body });
        }
      });
    });

    req.on('error', (error) => {
      reject(error);
    });

    if (postData) {
      req.write(postData);
    }
    req.end();
  });
}

/**
 * Test 1: Send a query and check requirement tracking is included
 */
async function testRequirementTrackingInResponse() {
  logSection('Test 1: Requirement Tracking in API Response');

  logTest('Sending query with interpret stage');
  logInfo(`Query: "help me understand this sales data: Q1=$2M, Q2=$1.5M, Q3=$1.8M"`);
  logInfo(`Conversation ID: ${TEST_CONVERSATION_ID}`);

  try {
    const response = await makeRequest('POST', '/api/process-message', {
      message: 'help me understand this sales data: Q1 revenue was $2M, Q2 was $1.5M, Q3 was $1.8M. What does this trend mean?',
      conversationId: TEST_CONVERSATION_ID
    });

    if (response.status === 200) {
      const reqTracking = response.data.requirementTracking;
      
      if (reqTracking) {
        logSuccess('Requirement tracking found in response');
        logInfo(`Workflow Stage: ${reqTracking.workflowStage}`);
        logInfo(`Is Complete: ${reqTracking.isComplete}`);
        logInfo(`Progress: ${reqTracking.progress.met}/${reqTracking.progress.total} (${reqTracking.progress.percentage}%)`);
        
        if (reqTracking.requirements && reqTracking.requirements.length > 0) {
          logInfo(`\nRequirements:`);
          reqTracking.requirements.forEach(req => {
            const status = req.met ? '✅' : '❌';
            logInfo(`  ${status} ${req.requirement}: ${req.description}`);
            if (req.met && req.evidence) {
              logInfo(`     Evidence: ${req.evidence}`);
            }
          });
        }

        if (reqTracking.decisions && reqTracking.decisions.length > 0) {
          logInfo(`\nDecisions Recorded: ${reqTracking.decisions.length}`);
          reqTracking.decisions.forEach((decision, idx) => {
            logInfo(`  ${idx + 1}. ${decision.decision}`);
            logInfo(`     Rationale: ${decision.rationale.substring(0, 100)}...`);
          });
        }

        // Check if requirements were detected
        const metCount = reqTracking.requirements.filter(r => r.met).length;
        if (metCount > 0) {
          logSuccess(`${metCount} requirements automatically detected as met`);
        } else {
          logError('No requirements detected as met (may need better detection)');
        }

        return { passed: true, tracking: reqTracking };
      } else {
        logError('Requirement tracking not found in response');
        return { passed: false, error: 'No requirementTracking in response' };
      }
    } else {
      logError(`Request failed with status ${response.status}`);
      return { passed: false, error: `Status ${response.status}` };
    }
  } catch (error) {
    logError(`Request error: ${error.message}`);
    return { passed: false, error: error.message };
  }
}

/**
 * Test 2: Check requirement tracking endpoint
 */
async function testRequirementTrackingEndpoint() {
  logSection('Test 2: Requirement Tracking API Endpoint');

  // First, send a query to create tracking
  logTest('Creating tracking by sending a query');
  await makeRequest('POST', '/api/process-message', {
    message: 'help me understand this inventory data: current stock is 500 units, reorder point is 1000',
    conversationId: TEST_CONVERSATION_ID
  });

  await new Promise(resolve => setTimeout(resolve, 1000));

  logTest('Fetching requirement tracking status');
  try {
    const response = await makeRequest('GET', `/api/requirement-tracking/${TEST_CONVERSATION_ID}/interpret`);

    if (response.status === 200) {
      const tracking = response.data;
      
      logSuccess('Requirement tracking endpoint works');
      logInfo(`Workflow Stage: ${tracking.workflowStage}`);
      logInfo(`Is Complete: ${tracking.isComplete}`);
      logInfo(`Progress: ${tracking.progress.met}/${tracking.progress.total} (${tracking.progress.percentage}%)`);
      logInfo(`Started At: ${tracking.startedAt}`);
      if (tracking.completedAt) {
        logInfo(`Completed At: ${tracking.completedAt}`);
      }

      if (tracking.requirements) {
        logInfo(`\nRequirements Status:`);
        tracking.requirements.forEach(req => {
          const status = req.met ? '✅' : '❌';
          logInfo(`  ${status} ${req.requirement}`);
        });
      }

      return { passed: true, tracking };
    } else if (response.status === 404) {
      logError('Tracking not found (may need to wait or check conversationId)');
      return { passed: false, error: 'Tracking not found' };
    } else {
      logError(`Request failed with status ${response.status}`);
      return { passed: false, error: `Status ${response.status}` };
    }
  } catch (error) {
    logError(`Request error: ${error.message}`);
    return { passed: false, error: error.message };
  }
}

/**
 * Test 3: Test different workflow stages
 */
async function testDifferentStages() {
  logSection('Test 3: Requirement Tracking Across Different Stages');

  const stages = [
    { stage: 'interpret', query: 'help me understand this sales trend: Q1=$2M, Q2=$1.5M, Q3=$1.8M' },
    { stage: 'recommend', query: 'what do you recommend I do about declining sales?' },
    { stage: 'what-if', query: 'what if we increase marketing budget by 20%?' },
    { stage: 'full-llm', query: 'alert me if there is a risk in sales' }
  ];

  const results = [];

  for (const test of stages) {
    logTest(`Testing ${test.stage} stage`);
    const convId = `${TEST_CONVERSATION_ID}-${test.stage}`;
    
    try {
      const response = await makeRequest('POST', '/api/process-message', {
        message: test.query,
        conversationId: convId
      });

      if (response.status === 200) {
        const reqTracking = response.data.requirementTracking;
        
        if (reqTracking) {
          const progress = reqTracking.progress;
          logSuccess(`${test.stage} stage: ${progress.met}/${progress.total} requirements met (${progress.percentage}%)`);
          
          results.push({
            stage: test.stage,
            passed: true,
            progress: progress
          });
        } else {
          logError(`${test.stage} stage: No requirement tracking found`);
          results.push({
            stage: test.stage,
            passed: false
          });
        }
      } else {
        logError(`${test.stage} stage: Request failed`);
        results.push({
          stage: test.stage,
          passed: false
        });
      }
    } catch (error) {
      logError(`${test.stage} stage: ${error.message}`);
      results.push({
        stage: test.stage,
        passed: false,
        error: error.message
      });
    }

    await new Promise(resolve => setTimeout(resolve, 1000));
  }

  return results;
}

/**
 * Test 4: Test summary endpoint
 */
async function testSummaryEndpoint() {
  logSection('Test 4: Requirement Tracking Summary');

  logTest('Fetching system-wide summary');
  
  try {
    const response = await makeRequest('GET', '/api/requirement-tracking/summary');

    if (response.status === 200) {
      const summary = response.data;
      
      logSuccess('Summary endpoint works');
      logInfo(`Total Tracked: ${summary.totalTracked}`);
      
      if (summary.byStage) {
        logInfo(`\nBy Stage:`);
        Object.entries(summary.byStage).forEach(([stage, stats]) => {
          logInfo(`  ${stage}:`);
          logInfo(`    Total: ${stats.total}`);
          logInfo(`    Complete: ${stats.complete}`);
          logInfo(`    Incomplete: ${stats.incomplete}`);
        });
      }

      if (summary.completionRates) {
        logInfo(`\nCompletion Rates:`);
        Object.entries(summary.completionRates).forEach(([stage, rate]) => {
          logInfo(`  ${stage}: ${rate}%`);
        });
      }

      return { passed: true, summary };
    } else {
      logError(`Request failed with status ${response.status}`);
      return { passed: false, error: `Status ${response.status}` };
    }
  } catch (error) {
    logError(`Request error: ${error.message}`);
    return { passed: false, error: error.message };
  }
}

/**
 * Main test runner
 */
async function runTests() {
  logSection('WorkflowRequirementTracker Test Suite');
  logInfo(`Test Conversation ID: ${TEST_CONVERSATION_ID}`);
  logInfo(`API Base URL: ${API_BASE}\n`);

  const results = {
    test1: null,
    test2: null,
    test3: null,
    test4: null
  };

  try {
    // Test 1: Requirement tracking in response
    results.test1 = await testRequirementTrackingInResponse();
    await new Promise(resolve => setTimeout(resolve, 1000));

    // Test 2: Requirement tracking endpoint
    results.test2 = await testRequirementTrackingEndpoint();
    await new Promise(resolve => setTimeout(resolve, 1000));

    // Test 3: Different stages
    results.test3 = await testDifferentStages();
    await new Promise(resolve => setTimeout(resolve, 1000));

    // Test 4: Summary endpoint
    results.test4 = await testSummaryEndpoint();

    // Summary
    logSection('Test Summary');

    const test1Passed = results.test1?.passed ? '✅' : '❌';
    const test2Passed = results.test2?.passed ? '✅' : '❌';
    const test3Passed = results.test3?.every(r => r.passed) ? '✅' : '❌';
    const test4Passed = results.test4?.passed ? '✅' : '❌';

    logInfo(`Test 1 (Tracking in Response): ${test1Passed}`);
    logInfo(`Test 2 (Tracking Endpoint): ${test2Passed}`);
    logInfo(`Test 3 (Different Stages): ${test3Passed}`);
    logInfo(`Test 4 (Summary Endpoint): ${test4Passed}`);

    const allPassed = results.test1?.passed && 
                     results.test2?.passed && 
                     results.test3?.every(r => r.passed) && 
                     results.test4?.passed;

    if (allPassed) {
      logSuccess('\n🎉 All tests passed!');
      process.exit(0);
    } else {
      logError('\n⚠️  Some tests failed. Review the output above for details.');
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

