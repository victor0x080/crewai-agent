/**
 * Contact Center API Routes
 * REST endpoints for contact center coaching demo
 * Integrates with TranscriptMonitor, CoachingCrew, and WebSocket server
 */

import express from 'express';
import { eventBus } from '../../services/events/EventBus.js';
import TranscriptMonitor from '../../services/contact-center/TranscriptMonitor.js';
import Redis from 'ioredis';
import OpenAI from 'openai';
import config from '../../config/index.js';

const router = express.Router();
const transcriptMonitor = new TranscriptMonitor(eventBus);

const REDIS_URL = process.env.REDIS_URL || 'redis://localhost:6379';
const redis = new Redis(REDIS_URL);

// Initialize OpenAI client if available
let openaiClient = null;
if (config.openai.enabled && config.openai.apiKey) {
  openaiClient = new OpenAI({ apiKey: config.openai.apiKey });
}

// ============================================================================
// REP PROFILE ENDPOINTS
// ============================================================================

/**
 * GET /api/contact-center/reps/:repId
 * Get rep profile
 */
router.get('/reps/:repId', async (req, res) => {
  try {
    const { repId } = req.params;
    
    // In production, fetch from database
    // For demo, we'll return from Redis or mock data
    const profile = await redis.get(`rep:${repId}`);
    
    if (profile) {
      res.json(JSON.parse(profile));
    } else {
      // Mock profile for demo
      res.json({
        rep_id: repId,
        name: `Rep ${repId}`,
        skill_level: 'intermediate',
        avg_csat: 4.1,
        compliance_score: 82.5,
        upsell_rate: 0.15,
        top_training_needs: ['empathy', 'policy_adherence']
      });
    }
  } catch (error) {
    console.error('[ContactCenterAPI] Error fetching rep:', error);
    res.status(500).json({ error: 'Failed to fetch rep profile' });
  }
});

/**
 * POST /api/contact-center/reps
 * Register rep profile
 */
router.post('/reps', async (req, res) => {
  try {
    const profile = req.body;
    
    // Register with transcript monitor
    transcriptMonitor.registerRep(profile);
    
    // Store in Redis
    await redis.set(`rep:${profile.rep_id}`, JSON.stringify(profile));
    
    res.json({ success: true, rep_id: profile.rep_id });
  } catch (error) {
    console.error('[ContactCenterAPI] Error registering rep:', error);
    res.status(500).json({ error: 'Failed to register rep' });
  }
});

// ============================================================================
// CUSTOMER PROFILE ENDPOINTS
// ============================================================================

/**
 * POST /api/contact-center/customers
 * Register customer profile
 */
router.post('/customers', async (req, res) => {
  try {
    const profile = req.body;
    
    // Register with transcript monitor
    transcriptMonitor.registerCustomer(profile);
    
    // Store in Redis
    await redis.set(`customer:${profile.customer_id}`, JSON.stringify(profile));
    
    res.json({ success: true, customer_id: profile.customer_id });
  } catch (error) {
    console.error('[ContactCenterAPI] Error registering customer:', error);
    res.status(500).json({ error: 'Failed to register customer' });
  }
});

// ============================================================================
// CALL ENDPOINTS
// ============================================================================

/**
 * POST /api/contact-center/calls/start
 * Start a new call
 */
router.post('/calls/start', async (req, res) => {
  try {
    const { call_id, rep_id, customer_id, primary_coach } = req.body;
    
    if (!call_id || !rep_id || !customer_id) {
      return res.status(400).json({ error: 'Missing required fields' });
    }
    
    // Start monitoring this call
    transcriptMonitor.startCall(call_id, rep_id, customer_id, primary_coach);
    
    // Store call metadata in Redis
    await redis.set(`call:${call_id}`, JSON.stringify({
      call_id,
      rep_id,
      customer_id,
      primary_coach: primary_coach || null,
      started_at: new Date().toISOString(),
      status: 'active'
    }));
    
    res.json({ success: true, call_id });
  } catch (error) {
    console.error('[ContactCenterAPI] Error starting call:', error);
    res.status(500).json({ error: 'Failed to start call' });
  }
});

/**
 * POST /api/contact-center/calls/:callId/turns
 * Ingest a transcript turn (simulates ASR output)
 */
router.post('/calls/:callId/turns', async (req, res) => {
  try {
    const { callId } = req.params;
    const turn = req.body;
    
    if (!turn.speaker || !turn.text) {
      return res.status(400).json({ error: 'Missing required turn fields' });
    }
    
    // Set call_id from param
    turn.call_id = callId;
    
    eventBus.emit('transcript.turn.received', turn);
    console.log("😂😂😂😂😂😂Broadcasted to WebSocket clients", turn.text);
    
    // Ingest turn - this will trigger detection
    await transcriptMonitor.ingestTurn(turn);
    
    // Broadcast to WebSocket clients
    
   
    res.json({ success: true, call_id: callId, turn_index: turn.turn_index });
  } catch (error) {
    console.error('[ContactCenterAPI] Error ingesting turn:', error);
    res.status(500).json({ error: 'Failed to ingest turn' });
  }
});

/**
 * GET /api/contact-center/calls/:callId/transcript
 * Get full transcript for a call
 */
router.get('/calls/:callId/transcript', async (req, res) => {
  try {
    const { callId } = req.params;
    
    // Fetch from Redis Stream or database
    const turns = await redis.lrange(`call:${callId}:turns`, 0, -1);
    const transcript = turns.map(t => JSON.parse(t));
    
    res.json({ call_id: callId, turns: transcript });
  } catch (error) {
    console.error('[ContactCenterAPI] Error fetching transcript:', error);
    res.status(500).json({ error: 'Failed to fetch transcript' });
  }
});

// ============================================================================
// DETECTED ISSUES ENDPOINTS
// ============================================================================

/**
 * GET /api/contact-center/issues
 * Get all detected issues (with optional filters)
 */
router.get('/issues', async (req, res) => {
  try {
    const { rep_id, call_id, issue_type, severity } = req.query;
    
    // Read from Redis Stream
    const messages = await redis.xrange(
      'stream:contact_center:issues',
      '-',
      '+',
      'COUNT',
      100
    );
    
    let issues = messages.map(([id, fields]) => ({
      message_id: id,
      ...Object.fromEntries(
        Array.from({ length: fields.length / 2 }, (_, i) => [
          fields[i * 2],
          fields[i * 2 + 1]
        ])
      )
    }));
    
    // Apply filters
    if (rep_id) issues = issues.filter(i => i.rep_id === rep_id);
    if (call_id) issues = issues.filter(i => i.call_id === call_id);
    if (issue_type) issues = issues.filter(i => i.issue_type === issue_type);
    if (severity) issues = issues.filter(i => i.severity === severity);
    
    res.json({ issues, count: issues.length });
  } catch (error) {
    console.error('[ContactCenterAPI] Error fetching issues:', error);
    res.status(500).json({ error: 'Failed to fetch issues' });
  }
});

/**
 * GET /api/contact-center/issues/:issueId
 * Get specific issue with full details
 */
router.get('/issues/:issueId', async (req, res) => {
  try {
    const { issueId } = req.params;
    
    // Fetch CloudEvent from RedisJSON
    const eventJson = await redis.call('JSON.GET', `event:${issueId}`) || null;
    
    if (!eventJson) {
      return res.status(404).json({ error: 'Issue not found' });
    }
    
    const event = typeof eventJson === 'string' ? JSON.parse(eventJson) : eventJson;
    res.json(event.data);
  } catch (error) {
    console.error('[ContactCenterAPI] Error fetching issue:', error);
    res.status(500).json({ error: 'Failed to fetch issue' });
  }
});

// ============================================================================
// COACHING SESSIONS ENDPOINTS
// ============================================================================

/**
 * GET /api/contact-center/coaching/sessions
 * Get coaching sessions (with optional filters)
 */
router.get('/coaching/sessions', async (req, res) => {
  try {
    const { rep_id, call_id, agent_name } = req.query;
    
    // Read from Redis Stream
    const messages = await redis.xrange(
      'stream:coaching:messages',
      '-',
      '+',
      'COUNT',
      100
    );
    
    let sessions = messages.map(([id, fields]) => ({
      message_id: id,
      ...Object.fromEntries(
        Array.from({ length: fields.length / 2 }, (_, i) => [
          fields[i * 2],
          fields[i * 2 + 1]
        ])
      )
    }));
    
    // Apply filters
    if (rep_id) sessions = sessions.filter(s => s.subject === `rep_${rep_id}`);
    if (call_id) sessions = sessions.filter(s => s.call_id === call_id);
    
    // Fetch full CloudEvents for each session
    const fullSessions = await Promise.all(
      sessions.map(async (s) => {
        const eventJson = await redis.call('JSON.GET', `event:${s.event_id}`) || null;
        return eventJson ? (typeof eventJson === 'string' ? JSON.parse(eventJson) : eventJson).data : null;
      })
    );
    
    res.json({ 
      sessions: fullSessions.filter(Boolean),
      count: fullSessions.filter(Boolean).length
    });
  } catch (error) {
    console.error('[ContactCenterAPI] Error fetching sessions:', error);
    res.status(500).json({ error: 'Failed to fetch coaching sessions' });
  }
});

/**
 * POST /api/contact-center/coaching/ask-question
 * Answer a question about coaching based on transcript snippet, selected response, and user question
 */
router.post('/coaching/ask-question', async (req, res) => {
  try {
    const { transcript_snippet, coach_recommendation, selected_response, user_question } = req.body;

    if (!transcript_snippet || !coach_recommendation || !user_question) {
      return res.status(400).json({ error: 'Missing required fields: transcript_snippet, coach_recommendation, user_question' });
    }

    if (!openaiClient) {
      return res.status(503).json({ error: 'OpenAI not configured' });
    }

    // Format transcript snippet as conversation
    let phoneConversation = '[Phone Conversation]\n';
    if (Array.isArray(transcript_snippet)) {
      phoneConversation += transcript_snippet
        .map(turn => `${turn.speaker}: ${turn.text}`)
        .join('\n');
    } else {
      phoneConversation += transcript_snippet;
    }

    // Format coach recommendation with selected response
    let coachMessage = `[Coach Recommendation]\n${coach_recommendation}`;
    if (selected_response) {
      coachMessage += `\n\nSelected Response: "${selected_response}"`;
    }

    // Build messages array as specified by user
    const messages = [
      {
        role: 'user',
        content: phoneConversation
      },
      {
        role: 'system',
        content: coachMessage
      },
      {
        role: 'user',
        content: user_question
      }
    ];

    // Call OpenAI
    const completion = await openaiClient.chat.completions.create({
      model: config.openai.model || 'gpt-4-turbo-preview',
      messages: messages,
      temperature: config.openai.temperature || 0.7,
      max_tokens: config.openai.maxTokens || 2000
    });

    const answer = completion.choices[0]?.message?.content || 'No answer generated';

    res.json({ answer });
  } catch (error) {
    console.error('[ContactCenterAPI] Error answering question:', error);
    res.status(500).json({ error: 'Failed to answer question', details: error.message });
  }
});

// ============================================================================
// ANALYTICS ENDPOINTS
// ============================================================================

/**
 * GET /api/contact-center/analytics/summary
 * Get summary analytics
 */
router.get('/analytics/summary', async (req, res) => {
  try {
    const { date_from, date_to } = req.query;
    
    // Fetch issue counts by type
    const messages = await redis.xrange(
      'stream:contact_center:issues',
      '-',
      '+',
      'COUNT',
      1000
    );
    
    const issueCounts = {};
    const severityCounts = {};
    
    for (const [, fields] of messages) {
      const fieldObj = Object.fromEntries(
        Array.from({ length: fields.length / 2 }, (_, i) => [
          fields[i * 2],
          fields[i * 2 + 1]
        ])
      );
      
      const issueType = fieldObj.issue_type;
      const severity = fieldObj.severity;
      
      issueCounts[issueType] = (issueCounts[issueType] || 0) + 1;
      severityCounts[severity] = (severityCounts[severity] || 0) + 1;
    }
    
    res.json({
      total_issues: messages.length,
      issues_by_type: issueCounts,
      issues_by_severity: severityCounts,
      period: { from: date_from, to: date_to }
    });
  } catch (error) {
    console.error('[ContactCenterAPI] Error fetching analytics:', error);
    res.status(500).json({ error: 'Failed to fetch analytics' });
  }
});

// ============================================================================
// SIMULATION ENDPOINTS (FOR DEMO)
// ============================================================================

/**
 * POST /api/contact-center/simulate/call
 * Simulate a complete call with transcript turns
 */
router.post('/simulate/call', async (req, res) => {
  try {
    const { call_id, rep_id, customer_id, turns } = req.body;
    
    if (!call_id || !rep_id || !customer_id || !turns) {
      return res.status(400).json({ error: 'Missing required fields' });
    }
    
    // Start call
    transcriptMonitor.startCall(call_id, rep_id, customer_id);
    
    // Send turns one by one with delays (simulates real-time streaming)
    for (const turn of turns) {
      await new Promise(resolve => setTimeout(resolve, 2000)); // 2 second delay
      
      await transcriptMonitor.ingestTurn({
        ...turn,
        call_id,
        rep_id,
        customer_id
      });
      
      eventBus.emit('transcript.turn.received', {
        ...turn,
        call_id
      });
    }
    
    res.json({ 
      success: true, 
      call_id,
      turns_processed: turns.length,
      message: 'Call simulation complete'
    });
  } catch (error) {
    console.error('[ContactCenterAPI] Error simulating call:', error);
    res.status(500).json({ error: 'Failed to simulate call' });
  }
});

// Export router and instances
export default router;
export { transcriptMonitor, eventBus };

