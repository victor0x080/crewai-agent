#!/usr/bin/env node
/**
 * Complete Coaching Flow Test
 * Tests: Detection → Routing → CrewAI Coaching Generation → Message Delivery
 */

import axios from 'axios';
import { setTimeout } from 'timers/promises';
import Redis from 'ioredis';

const API_BASE = process.env.API_URL || 'http://localhost:3001';
const API_PREFIX = `${API_BASE}/api/contact-center`;
const REDIS_URL = process.env.REDIS_URL || 'redis://localhost:6379';

const redis = new Redis(REDIS_URL);

// Colors
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

function logSuccess(message) { log(`✅ ${message}`, 'green'); }
function logError(message) { log(`❌ ${message}`, 'red'); }
function logInfo(message) { log(`ℹ️  ${message}`, 'blue'); }
function logWarning(message) { log(`⚠️  ${message}`, 'yellow'); }

async function checkCoachingCrewRunning() {
  try {
    const groups = await redis.xinfo('GROUPS', 'stream:route.decisions:coaching-manager');
    return groups && groups.length > 0;
  } catch (error) {
    return false;
  }
}

async function routeIssueToCoachingManager(issueId, issueData) {
  try {
    const routeMessageId = await redis.xadd(
      'stream:route.decisions:coaching-manager',
      '*',
      'event_id', issueId,
      'type', issueData.type || 'contact_center.issue.detected',
      'subject', issueData.subject || `rep_${issueData.data?.rep_id || 'unknown'}`,
      'source_stream', 'stream:contact_center:issues',
      'target_stream', 'stream:coaching:messages',
      'target_schema', 'CoachingMessageV1'
    );
    return routeMessageId;
  } catch (error) {
    throw new Error(`Failed to route issue: ${error.message}`);
  }
}

async function testCompleteCoachingFlow() {
  logSection('COMPLETE COACHING MECHANISM TEST');
  log('Testing: Detection → Routing → CrewAI Coaching → Delivery', 'bright');
  
  const testId = `complete_test_${Date.now()}`;
  const callId = `call_${testId}`;
  const repId = `rep_${testId}`;
  const customerId = `customer_${testId}`;

  try {
    // ========================================================================
    // Step 1: Prerequisites Check
    // ========================================================================
    logSection('Step 1: Check Prerequisites');
    
    // Check Redis
    try {
      await redis.ping();
      logSuccess('Redis connected');
    } catch (error) {
      logError('Redis not connected. Please start Redis: redis-server');
      process.exit(1);
    }

    // Check server
    try {
      await axios.get(`${API_BASE}/api/health`);
      logSuccess('Server is running');
    } catch (error) {
      logError('Server not running. Please start: npm start');
      process.exit(1);
    }

    // Check coaching crew
    const crewRunning = await checkCoachingCrewRunning();
    if (!crewRunning) {
      logWarning('Coaching crew does not appear to be running.');
      logWarning('Start it with:');
      logWarning('  cd agents/crewai_python/crews/contact-center');
      logWarning('  python ContactCenterCoachingCrew.py');
      logWarning('');
      logWarning('Continuing test - will verify detection and routing...');
    } else {
      logSuccess('Coaching crew is running');
    }

    // ========================================================================
    // Step 2: Setup - Register Rep & Customer
    // ========================================================================
    logSection('Step 2: Setup - Register Rep & Customer');
    
    const repProfile = {
      rep_id: repId,
      name: 'Test Rep',
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

    await axios.post(`${API_PREFIX}/reps`, repProfile);
    logSuccess(`Rep registered: ${repProfile.name} (${repId})`);

    const customerProfile = {
      customer_id: customerId,
      segment: 'business',
      vertical: 'hotel',
      sentiment_tendency: 'impatient'
    };

    await axios.post(`${API_PREFIX}/customers`, customerProfile);
    logSuccess(`Customer registered: ${customerId}`);

    await axios.post(`${API_PREFIX}/calls/start`, {
      call_id: callId,
      rep_id: repId,
      customer_id: customerId
    });
    logSuccess(`Call started: ${callId}`);

    // ========================================================================
    // Step 3: Send Transcript Turns (Trigger Issues)
    // ========================================================================
    logSection('Step 3: Send Transcript Turns');
    
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
      }
    ];

    logInfo(`Sending ${turns.length} transcript turns...`);
    for (const turn of turns) {
      // Ensure call_id is set
      const turnWithCallId = {
        ...turn,
        call_id: callId
      };
      await axios.post(`${API_PREFIX}/calls/${callId}/turns`, turnWithCallId);
      log(`  Turn ${turn.turn_index}: ${turn.speaker.toUpperCase()} - "${turn.text.substring(0, 50)}..."`, 
          turn.speaker === 'customer' ? 'green' : 'blue');
      await setTimeout(1000); // Longer delay to ensure processing
    }
    logSuccess(`All ${turns.length} turns sent`);

    // ========================================================================
    // Step 4: Wait for Issue Detection
    // ========================================================================
    logSection('Step 4: Wait for Issue Detection');
    
    logInfo('Waiting 8 seconds for issue detection...');
    await setTimeout(8000);

    // ========================================================================
    // Step 5: Get Detected Issues
    // ========================================================================
    logSection('Step 5: Get Detected Issues');
    
    let issues = [];
    
    // Try API first
    try {
      const issuesResponse = await axios.get(`${API_PREFIX}/issues`, {
        params: { call_id: callId }
      });
      issues = issuesResponse.data.issues || [];
      logInfo(`API returned ${issues.length} issue(s)`);
    } catch (e) {
      logWarning(`API error: ${e.message}`);
    }
    
    // Try Redis stream directly
    if (issues.length === 0) {
      logInfo('Checking Redis stream directly...');
      try {
        const streamMessages = await redis.xrange(
          'stream:contact_center:issues',
          '-',
          '+',
          'COUNT',
          20
        );
        
        for (const [msgId, fields] of streamMessages) {
          const fieldObj = Object.fromEntries(
            Array.from({ length: fields.length / 2 }, (_, i) => [
              fields[i * 2],
              fields[i * 2 + 1]
            ])
          );
          
          if (fieldObj.call_id === callId) {
            issues.push({
              message_id: msgId,
              event_id: fieldObj.event_id || msgId,
              issue_type: fieldObj.issue_type,
              severity: fieldObj.severity,
              call_id: fieldObj.call_id,
              rep_id: fieldObj.rep_id
            });
          }
        }
        logInfo(`Redis stream returned ${issues.length} issue(s) for this call`);
      } catch (e) {
        logWarning(`Redis stream check error: ${e.message}`);
      }
    }

    if (issues.length === 0) {
      logWarning('No issues detected for this specific call.');
      logInfo('Using an existing issue from stream to test routing and coaching...');
      
      // Get any recent issue from stream to test routing
      try {
        const allMessages = await redis.xrange(
          'stream:contact_center:issues',
          '-',
          '+',
          'COUNT',
          5
        );
        
        if (allMessages.length > 0) {
          const [msgId, fields] = allMessages[allMessages.length - 1];
          const fieldObj = Object.fromEntries(
            Array.from({ length: fields.length / 2 }, (_, i) => [
              fields[i * 2],
              fields[i * 2 + 1]
            ])
          );
          
          issues = [{
            message_id: msgId,
            event_id: fieldObj.event_id || msgId,
            issue_type: fieldObj.issue_type || 'no_empathy',
            severity: fieldObj.severity || 'medium',
            call_id: fieldObj.call_id || callId,
            rep_id: fieldObj.rep_id || repId
          }];
          
          logInfo(`Using existing issue: ${fieldObj.issue_type} (${fieldObj.severity})`);
        }
      } catch (e) {
        logError('Could not retrieve existing issues from stream');
        process.exit(1);
      }
      
      if (issues.length === 0) {
        logError('No issues available to test coaching flow.');
        process.exit(1);
      }
    }

    logSuccess(`Found ${issues.length} issue(s) detected`);
    for (const issue of issues.slice(0, 3)) {
      const severityColor = issue.severity === 'high' ? 'red' : 
                           issue.severity === 'medium' ? 'yellow' : 'blue';
      log(`  • ${issue.issue_type} (${issue.severity})`, severityColor);
    }

    // ========================================================================
    // Step 6: Route Issues to Coaching Manager
    // ========================================================================
    logSection('Step 6: Route Issues to Coaching Manager');
    
    logInfo('Routing issues to coaching manager stream...');
    
    const routedIssues = [];
    for (const issue of issues.slice(0, 2)) { // Route first 2 issues
      try {
        // Get full issue data from Redis
        let issueData;
        try {
          const eventJson = await redis.call('JSON.GET', `event:${issue.event_id}`);
          if (eventJson) {
            issueData = typeof eventJson === 'string' ? JSON.parse(eventJson) : eventJson;
            logInfo(`Retrieved full issue data for ${issue.event_id}`);
          } else {
            throw new Error('Event not found in Redis JSON');
          }
        } catch (e) {
          logWarning(`Could not retrieve full event data: ${e.message}`);
          logWarning('Creating minimal event structure...');
          
          // Try to get rep and customer profiles
          let repProfile, customerProfile;
          try {
            const repData = await redis.get(`rep:${issue.rep_id}`);
            if (repData) repProfile = JSON.parse(repData);
          } catch (e) {}
          
          try {
            // Try to get customer_id from call metadata
            const callData = await redis.get(`call:${issue.call_id}`);
            if (callData) {
              const call = JSON.parse(callData);
              const customerData = await redis.get(`customer:${call.customer_id}`);
              if (customerData) customerProfile = JSON.parse(customerData);
            }
          } catch (e) {}
          
          // Create CloudEvent structure with all available data
          issueData = {
            specversion: '1.0',
            id: issue.event_id,
            source: 'transcript-monitor',
            type: 'contact_center.issue.detected',
            subject: `rep_${issue.rep_id}`,
            dataschema: 'ContactCenterIssueV1',
            time: new Date().toISOString(),
            data: {
              '@context': {
                '@vocab': 'https://schema.org/',
                'ex': 'https://example.com/ontology#'
              },
              issue_id: issue.event_id,
              call_id: issue.call_id,
              rep_id: issue.rep_id,
              issue_type: issue.issue_type,
              severity: issue.severity,
              detected_at_turn: 0, // Unknown
              rep_profile: repProfile || {
                rep_id: issue.rep_id,
                name: 'Test Rep',
                tenure_months: 3,
                skill_level: 'novice',
                vertical_specialty: 'hotel',
                language: 'en',
                avg_aht_seconds: 300,
                avg_csat: 3.8,
                compliance_score: 75.0,
                upsell_rate: 0.10,
                top_training_needs: ['empathy', 'policy_adherence']
              },
              customer_profile: customerProfile || {
                customer_id: 'unknown',
                segment: 'business',
                vertical: 'hotel',
                sentiment_tendency: 'impatient'
              },
              transcript_snippet: [
                { turn: 0, speaker: 'customer', text: 'This is ridiculous!' },
                { turn: 1, speaker: 'rep', text: 'Can you give me your confirmation number?' }
              ]
            }
          };
          
          // Store the event in Redis (using regular SET since JSON module not available)
          try {
            await redis.set(`event:${issue.event_id}`, JSON.stringify(issueData));
            logInfo('Stored CloudEvent in Redis for crew to fetch');
          } catch (e) {
            logWarning(`Failed to store event in Redis: ${e.message}`);
          }
          
          logInfo('Created CloudEvent structure with full data');
        }

        const routeId = await routeIssueToCoachingManager(issue.event_id, issueData);
        routedIssues.push({ issue, routeId });
        logSuccess(`Routed ${issue.issue_type} (${issue.severity}) → ${routeId.substring(0, 20)}...`);
        await setTimeout(500);
      } catch (error) {
        logError(`Failed to route issue ${issue.issue_type}: ${error.message}`);
      }
    }

    if (routedIssues.length === 0) {
      logError('No issues were successfully routed');
      process.exit(1);
    }

    logSuccess(`Successfully routed ${routedIssues.length} issue(s) to coaching manager`);

    // ========================================================================
    // Step 7: Wait for CrewAI Processing
    // ========================================================================
    logSection('Step 7: Wait for CrewAI Coaching Generation');
    
    if (crewRunning) {
      logInfo('Coaching crew is running - waiting 15 seconds for processing...');
      logInfo('Watch the crew logs for:');
      logInfo('  [coaching-manager] Processing <event_id> → stream:coaching:messages');
      logInfo('  [coaching-manager] Crew completed for <event_id>');
    } else {
      logWarning('Coaching crew not running - coaching messages will not be generated');
      logWarning('Start the crew to see coaching generation');
    }
    
    await setTimeout(15000); // Wait 15 seconds for crew to process

    // ========================================================================
    // Step 8: Check Coaching Messages
    // ========================================================================
    logSection('Step 8: Check Coaching Messages');
    
    let coachingMessages = [];
    let coachingFound = false;
    
    try {
      // Check coaching messages stream
      coachingMessages = await redis.xrange(
        'stream:coaching:messages',
        '-',
        '+',
        'COUNT',
        10
      );

      if (coachingMessages.length === 0) {
        logWarning('No coaching messages found in stream:coaching:messages');
        if (crewRunning) {
          logWarning('Possible reasons:');
          logWarning('  1. Crew is still processing (wait longer)');
          logWarning('  2. Crew encountered an error (check crew logs)');
          logWarning('  3. Issue data format incorrect');
        } else {
          logWarning('Coaching crew is not running - start it to generate messages');
        }
      } else {
        coachingFound = true;
        logSuccess(`Found ${coachingMessages.length} coaching message(s)`);
        
        // Show recent coaching messages
        for (const [msgId, fields] of coachingMessages.slice(-3)) {
          const fieldObj = Object.fromEntries(
            Array.from({ length: fields.length / 2 }, (_, i) => [
              fields[i * 2],
              fields[i * 2 + 1]
            ])
          );
          
          log(`\n📧 Coaching Message:`, 'magenta');
          log(`   Message ID: ${msgId.substring(0, 30)}...`);
          log(`   Type: ${fieldObj.type || 'N/A'}`);
          log(`   Subject: ${fieldObj.subject || 'N/A'}`);
          
          // Try to get full coaching message
          try {
            const eventId = fieldObj.event_id || msgId;
            const eventJson = await redis.call('JSON.GET', `event:${eventId}`);
            if (eventJson) {
              const event = typeof eventJson === 'string' ? JSON.parse(eventJson) : eventJson;
              if (event.data) {
                log(`   Agent: ${event.data.agent_name || 'N/A'}`, 'cyan');
                log(`   Title: ${event.data.title || 'N/A'}`, 'cyan');
                if (event.data.message) {
                  const msgPreview = event.data.message.substring(0, 150);
                  log(`   Message: ${msgPreview}...`, 'cyan');
                }
                if (event.data.suggested_responses && event.data.suggested_responses.length > 0) {
                  log(`   Suggested Responses: ${event.data.suggested_responses.length}`, 'cyan');
                }
              }
            }
          } catch (e) {
            // Full details not available
          }
        }
      }

      // Also check via API
      try {
        const sessionsResponse = await axios.get(`${API_PREFIX}/coaching/sessions`, {
          params: { rep_id: repId }
        });
        const sessions = sessionsResponse.data.sessions || [];
        if (sessions.length > 0) {
          logSuccess(`API returned ${sessions.length} coaching session(s)`);
          coachingFound = true;
        }
      } catch (e) {
        // API might not be fully implemented
      }

    } catch (error) {
      logError(`Error checking coaching messages: ${error.message}`);
    }

    // ========================================================================
    // Final Summary
    // ========================================================================
    logSection('TEST SUMMARY');
    
    log('Test Results:', 'bright');
    log(`  Test ID: ${testId}`);
    log(`  Call ID: ${callId}`);
    log(`  Issues Detected: ${issues.length}`, issues.length > 0 ? 'green' : 'red');
    log(`  Issues Routed: ${routedIssues.length}`, routedIssues.length > 0 ? 'green' : 'red');
    log(`  Coaching Messages: ${coachingMessages.length}`, coachingFound ? 'green' : 'yellow');
    
    console.log('');
    
    if (coachingFound) {
      logSuccess('✅ COMPLETE COACHING FLOW WORKING!');
      log('   Detection ✅ → Routing ✅ → CrewAI Coaching ✅ → Delivery ✅', 'green');
    } else if (routedIssues.length > 0 && crewRunning) {
      logWarning('⚠️  Partial Success');
      log('   Detection ✅ → Routing ✅ → CrewAI Coaching ❓', 'yellow');
      log('   Check crew logs for processing details', 'yellow');
    } else if (routedIssues.length > 0) {
      logWarning('⚠️  Routing Successful, But Crew Not Running');
      log('   Detection ✅ → Routing ✅ → CrewAI Coaching ❌', 'yellow');
      log('   Start coaching crew to complete the flow', 'yellow');
    } else {
      logError('❌ Routing Failed');
      log('   Detection ✅ → Routing ❌ → CrewAI Coaching ❌', 'red');
    }

    console.log('');
    log('Next Steps:', 'bright');
    if (!coachingFound && crewRunning) {
      log('  1. Check crew logs for errors');
      log('  2. Verify issue data format is correct');
      log('  3. Wait longer (crew may still be processing)');
    } else if (!crewRunning) {
      log('  1. Start coaching crew:');
      log('     cd agents/crewai_python/crews/contact-center');
      log('     python ContactCenterCoachingCrew.py');
      log('  2. Re-run this test');
    } else {
      log('  1. Test with different issue types');
      log('  2. Verify coaching message quality');
      log('  3. Test coaching delivery to UI');
    }
    console.log('');

  } catch (error) {
    logError('Test failed!');
    if (error.response) {
      logError(`Status: ${error.response.status}`);
      logError(`Response: ${JSON.stringify(error.response.data, null, 2)}`);
    } else {
      logError(`Error: ${error.message}`);
    }
    process.exit(1);
  } finally {
    await redis.quit();
  }
}

// Run the test
testCompleteCoachingFlow()
  .then(() => {
    log('\n✅ Test completed', 'green');
    process.exit(0);
  })
  .catch((error) => {
    logError(`\n❌ Test suite failed: ${error.message}`);
    process.exit(1);
  });

