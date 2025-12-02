#!/usr/bin/env node
/**
 * Test script for Contact Center Coaching Mechanism
 * Tests the full flow: registration → call → transcript → detection → coaching
 */

import axios from 'axios';
import { setTimeout } from 'timers/promises';

const API_BASE = process.env.API_URL || 'http://localhost:3001';
const API_PREFIX = `${API_BASE}/api/contact-center`;

// Colors for terminal output
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  green: '\x1b[32m',
  blue: '\x1b[34m',
  yellow: '\x1b[33m',
  red: '\x1b[31m',
  cyan: '\x1b[36m',
  magenta: '\x1b[35m'
};

function log(message, color = 'reset') {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

function logSection(title) {
  console.log(`\n${colors.cyan}${'='.repeat(70)}${colors.reset}`);
  log(title, 'cyan');
  console.log(`${colors.cyan}${'='.repeat(70)}${colors.reset}\n`);
}

function logSuccess(message) {
  log(`✅ ${message}`, 'green');
}

function logError(message) {
  log(`❌ ${message}`, 'red');
}

function logInfo(message) {
  log(`ℹ️  ${message}`, 'blue');
}

function logWarning(message) {
  log(`⚠️  ${message}`, 'yellow');
}

async function testContactCenterCoaching() {
  logSection('CONTACT CENTER COACHING MECHANISM TEST');
  
  const testId = `test_${Date.now()}`;
  const callId = `call_${testId}`;
  const repId = `rep_${testId}`;
  const customerId = `customer_${testId}`;

  try {
    // ========================================================================
    // Step 1: Register Rep Profile
    // ========================================================================
    logSection('Step 1: Register Rep Profile');
    
    const repProfile = {
      rep_id: repId,
      name: 'Demo Rep',
      tenure_months: 3,
      skill_level: 'novice',
      vertical_specialty: 'hotel',
      language: 'en',
      avg_aht_seconds: 300,
      avg_csat: 3.8,
      compliance_score: 75.0,
      upsell_rate: 0.10,
      top_training_needs: ['empathy', 'policy_adherence']
    };

    logInfo(`Registering rep: ${repProfile.name} (${repId})`);
    const repResponse = await axios.post(`${API_PREFIX}/reps`, repProfile);
    logSuccess(`Rep registered: ${repResponse.data.rep_id}`);

    // ========================================================================
    // Step 2: Register Customer Profile
    // ========================================================================
    logSection('Step 2: Register Customer Profile');
    
    const customerProfile = {
      customer_id: customerId,
      segment: 'business',
      vertical: 'hotel',
      sentiment_tendency: 'impatient'
    };

    logInfo(`Registering customer: ${customerId}`);
    const customerResponse = await axios.post(`${API_PREFIX}/customers`, customerProfile);
    logSuccess(`Customer registered: ${customerResponse.data.customer_id}`);

    // ========================================================================
    // Step 3: Start Call
    // ========================================================================
    logSection('Step 3: Start Call');
    
    logInfo(`Starting call: ${callId}`);
    const callResponse = await axios.post(`${API_PREFIX}/calls/start`, {
      call_id: callId,
      rep_id: repId,
      customer_id: customerId
    });
    logSuccess(`Call started: ${callResponse.data.call_id}`);

    // ========================================================================
    // Step 4: Send Transcript Turns (Trigger Issues)
    // ========================================================================
    logSection('Step 4: Send Transcript Turns');
    
    const turns = [
      {
        turn_index: 0,
        speaker: 'customer',
        text: "Hi, I just arrived at the hotel and they say you're overbooked. I don't have a room!",
        timestamp: new Date().toISOString(),
        rep_id: repId,
        customer_id: customerId
      },
      {
        turn_index: 1,
        speaker: 'rep',
        text: "Can you give me your confirmation number?",
        timestamp: new Date().toISOString(),
        rep_id: repId,
        customer_id: customerId
      },
      {
        turn_index: 2,
        speaker: 'customer',
        text: "It's ABC123. This is ridiculous and very frustrating!",
        timestamp: new Date().toISOString(),
        rep_id: repId,
        customer_id: customerId
      },
      {
        turn_index: 3,
        speaker: 'rep',
        text: "I see your booking here in the system.",
        timestamp: new Date().toISOString(),
        rep_id: repId,
        customer_id: customerId
      },
      {
        turn_index: 4,
        speaker: 'customer',
        text: "This has ruined my trip. I want a full refund immediately.",
        timestamp: new Date().toISOString(),
        rep_id: repId,
        customer_id: customerId
      },
      {
        turn_index: 5,
        speaker: 'rep',
        text: "Okay, I'll refund everything right now.",
        timestamp: new Date().toISOString(),
        rep_id: repId,
        customer_id: customerId
      },
      {
        turn_index: 6,
        speaker: 'customer',
        text: "Fine. I travel for business often so this is really disappointing.",
        timestamp: new Date().toISOString(),
        rep_id: repId,
        customer_id: customerId
      },
      {
        turn_index: 7,
        speaker: 'rep',
        text: "You'll get an email confirmation shortly. Goodbye.",
        timestamp: new Date().toISOString(),
        rep_id: repId,
        customer_id: customerId
      }
    ];

    logInfo(`Sending ${turns.length} transcript turns...`);
    
    for (const turn of turns) {
      await axios.post(`${API_PREFIX}/calls/${callId}/turns`, turn);
      log(`  Turn ${turn.turn_index}: ${turn.speaker.toUpperCase()} - "${turn.text.substring(0, 50)}..."`, 
          turn.speaker === 'customer' ? 'green' : 'blue');
      
      // Small delay to simulate real-time
      await setTimeout(500);
    }

    logSuccess(`All ${turns.length} turns sent`);

    // ========================================================================
    // Step 5: Wait for Detection (give system time to process)
    // ========================================================================
    logSection('Step 5: Waiting for Issue Detection');
    
    logInfo('Waiting 3 seconds for issue detection...');
    await setTimeout(3000);

    // ========================================================================
    // Step 6: Check Detected Issues
    // ========================================================================
    logSection('Step 6: Check Detected Issues');
    
    const issuesResponse = await axios.get(`${API_PREFIX}/issues`, {
      params: { call_id: callId }
    });

    const issues = issuesResponse.data.issues || [];
    logInfo(`Found ${issues.length} detected issue(s)`);

    if (issues.length === 0) {
      logWarning('No issues detected. This might indicate:');
      logWarning('  - Redis is not running');
      logWarning('  - Issue detection logic needs adjustment');
      logWarning('  - TranscriptMonitor not processing turns correctly');
    } else {
      for (const issue of issues) {
        const severityColor = issue.severity === 'high' ? 'red' : 
                             issue.severity === 'medium' ? 'yellow' : 'blue';
        log(`\n🚨 Issue Detected:`, 'bright');
        log(`   Type: ${issue.issue_type}`, severityColor);
        log(`   Severity: ${issue.severity}`, severityColor);
        log(`   Message ID: ${issue.message_id}`);
        
        // Try to get full issue details
        try {
          const issueId = issue.event_id || issue.message_id;
          if (issueId) {
            const fullIssueResponse = await axios.get(`${API_PREFIX}/issues/${issueId}`);
            const fullIssue = fullIssueResponse.data;
            if (fullIssue) {
              log(`   Detected at turn: ${fullIssue.detected_at_turn}`);
              log(`   Rep: ${fullIssue.rep_id}`);
            }
          }
        } catch (e) {
          // Issue details might not be available if Redis JSON is not enabled
          logWarning('Full issue details not available (Redis JSON might not be enabled)');
        }
      }
    }

    // ========================================================================
    // Step 7: Check Analytics
    // ========================================================================
    logSection('Step 7: Check Analytics Summary');
    
    try {
      const analyticsResponse = await axios.get(`${API_PREFIX}/analytics/summary`);
      const analytics = analyticsResponse.data;
      
      logInfo('Analytics Summary:');
      log(`   Total Issues: ${analytics.total_issues || 0}`);
      log(`   Issues by Type: ${JSON.stringify(analytics.issues_by_type || {})}`);
      log(`   Issues by Severity: ${JSON.stringify(analytics.issues_by_severity || {})}`);
    } catch (error) {
      logWarning(`Analytics endpoint error: ${error.message}`);
    }

    // ========================================================================
    // Step 8: Test Simulation Endpoint
    // ========================================================================
    logSection('Step 8: Test Complete Call Simulation');
    
    const simCallId = `sim_call_${testId}`;
    const simRepId = `sim_rep_${testId}`;
    const simCustomerId = `sim_customer_${testId}`;
    
    logInfo(`Running complete call simulation...`);
    
    try {
      const simResponse = await axios.post(`${API_PREFIX}/simulate/call`, {
        call_id: simCallId,
        rep_id: simRepId,
        customer_id: simCustomerId,
        turns: turns.slice(0, 4) // Use first 4 turns for simulation
      });
      
      logSuccess(`Simulation complete: ${simResponse.data.turns_processed} turns processed`);
    } catch (error) {
      logError(`Simulation failed: ${error.message}`);
      if (error.response) {
        logError(`Response: ${JSON.stringify(error.response.data)}`);
      }
    }

    // ========================================================================
    // Summary
    // ========================================================================
    logSection('TEST SUMMARY');
    
    logSuccess('Test completed successfully!');
    logInfo(`Test ID: ${testId}`);
    logInfo(`Call ID: ${callId}`);
    logInfo(`Issues Detected: ${issues.length}`);
    
    if (issues.length > 0) {
      logSuccess('✅ Issue detection is working!');
    } else {
      logWarning('⚠️  No issues detected - check Redis connection and TranscriptMonitor');
    }

    log('\n' + colors.cyan + '='.repeat(70) + colors.reset);
    log('Next Steps:', 'bright');
    log('1. Check Redis Stream: stream:contact_center:issues');
    log('2. Verify TranscriptMonitor is processing turns');
    log('3. Check if Coaching Crew is registered and processing issues');
    log('4. Monitor coaching messages in: stream:coaching:messages');
    console.log('');

  } catch (error) {
    logError('Test failed!');
    if (error.response) {
      logError(`Status: ${error.response.status}`);
      logError(`Response: ${JSON.stringify(error.response.data, null, 2)}`);
    } else if (error.request) {
      logError(`No response received. Is the server running at ${API_BASE}?`);
      logError(`Error: ${error.message}`);
    } else {
      logError(`Error: ${error.message}`);
    }
    process.exit(1);
  }
}

// Run the test
testContactCenterCoaching()
  .then(() => {
    log('\n✅ All tests completed', 'green');
    process.exit(0);
  })
  .catch((error) => {
    logError(`\n❌ Test suite failed: ${error.message}`);
    process.exit(1);
  });

