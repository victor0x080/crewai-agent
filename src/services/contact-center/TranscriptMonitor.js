/**
 * Transcript Monitor Service
 * Watches streaming call transcripts in real-time and detects:
 * - No empathy (customer frustration not acknowledged)
 * - Missing verification (accessing accounts without security check)
 * - Policy violations (unauthorized actions)
 * - Missed upsells (good opportunities not taken)
 * - Script non-compliance (required steps skipped)
 * - Escalation risk (conversation getting heated)
 * 
 * Publishes detected issues to Redis Streams for coaching crew
 */

// EventBus is passed as constructor parameter, no direct import needed
import Redis from 'ioredis';
import { v4 as uuidv4 } from 'uuid';

const REDIS_URL = process.env.REDIS_URL || 'redis://localhost:6379';
const redis = new Redis(REDIS_URL);

// Phrase dictionaries for rule-based detection
const FRUSTRATION_PHRASES = [
  'this is ridiculous',
  "i'm upset",
  'this is frustrating',
  'unacceptable',
  'this ruined my',
  'terrible service',
  "i'm very disappointed",
  "i can't believe"
];

const EMPATHY_PHRASES = [
  "i'm sorry",
  'i apologize',
  'i totally understand',
  'i understand how frustrating',
  'i hear how',
  'that must be',
  'i can imagine'
];

const VERIFICATION_PHRASES = [
  'before i access',
  'for security',
  'can i verify',
  'to protect your account',
  'confirm your',
  'validate your identity'
];

const ACCOUNT_ACCESS_HINTS = [
  'i see your booking',
  'i pulled up your reservation',
  'i can see your flight',
  'looking at your account',
  'your order shows'
];

const POLICY_PHRASES = [
  'let me check our policy',
  'our policy allows',
  "i'm authorized to",
  'i need approval for',
  'let me see what i can do'
];

const UNAUTHORIZED_ACTIONS = [
  "i'll refund everything",
  "i'll comp your stay",
  'consider it done',
  "i'll waive all fees"
];

const UPSELL_OPPORTUNITIES = [
  'travel often',
  'next time',
  'future booking',
  'coming back',
  'business trip'
];

export class TranscriptMonitor {
  constructor(eventBus) {
    this.eventBus = eventBus;
    this.callTranscripts = new Map();
    this.callMetadata = new Map(); // Store call metadata (rep_id, customer_id)
    this.repProfiles = new Map();
    this.customerProfiles = new Map();
    this.detectedIssues = new Map(); // call_id -> Set of issue keys (for deduplication)
    this.setupEventHandlers();
  }

  setupEventHandlers() {
    // Listen for new transcript turns
    // this.eventBus.on('transcript.turn.received', (turn) => {
    //   this.processTurn(turn);
    // });
  }

  /**
   * Register rep profile
   */
  registerRep(profile) {
    this.repProfiles.set(profile.rep_id, profile);
    console.log(`[TranscriptMonitor] Registered rep: ${profile.name} (${profile.rep_id})`);
  }

  /**
   * Register customer profile
   */
  registerCustomer(profile) {
    this.customerProfiles.set(profile.customer_id, profile);
    console.log(`[TranscriptMonitor] Registered customer: ${profile.customer_id}`);
  }

  /**
   * Process a single turn and run all detectors
   * Only checks the NEW turn and recent context, not the entire transcript
   */
  async processTurn(turn) {
    // Store turn
    if (!this.callTranscripts.has(turn.call_id)) {
      this.callTranscripts.set(turn.call_id, []);
    }
    if (!this.detectedIssues.has(turn.call_id)) {
      this.detectedIssues.set(turn.call_id, new Set());
    }
    this.callTranscripts.get(turn.call_id).push(turn);

    const transcript = this.callTranscripts.get(turn.call_id);
    let detectedSet = this.detectedIssues.get(turn.call_id);
    
    // Safety check: ensure detectedSet is initialized
    if (!detectedSet) {
      this.detectedIssues.set(turn.call_id, new Set());
      detectedSet = this.detectedIssues.get(turn.call_id);
    }

    // Get the current turn index (0-based)
    const currentTurnIndex = transcript.length - 1;
    const currentTurn = transcript[currentTurnIndex];

    // Only run detectors when:
    // 1. Current turn is a rep turn (rep is responding)
    // 2. There was a previous customer turn (customer spoke before)
    if (currentTurn.speaker !== 'rep') {
      // Skip detection if current turn is not from rep
      return;
    }

    // Find the most recent customer turn before the current rep turn
    let mostRecentCustomerIndex = -1;
    for (let i = currentTurnIndex - 1; i >= 0; i--) {
      if (transcript[i].speaker === 'customer') {
        mostRecentCustomerIndex = i;
        break;
      }
    }
    
    if (mostRecentCustomerIndex === -1) {
      // Skip detection if no customer turn found before current rep turn
      return;
    }

    // Only check from the most recent customer turn to the current rep turn
    // This ensures we only evaluate the rep's response to the most recent customer statement
    const recentContext = transcript.slice(mostRecentCustomerIndex, currentTurnIndex + 1);
    const recentContextStartIndex = mostRecentCustomerIndex;

    // Check if turn has an 'error' or 'intent' field indicating which issue type to detect
    const expectedIssueType = currentTurn.error || currentTurn.intent;
    
    // Run detectors but only keep ONE issue per turn (first detected or highest priority)
    const allDetectedIssues = [];
    
    if (expectedIssueType) {
      // Only run the detector that matches the expected issue type
      switch (expectedIssueType) {
        case 'no_empathy':
          allDetectedIssues.push(...this.detectNoEmpathy(recentContext, 2, recentContextStartIndex));
          break;
        case 'missing_verification':
          allDetectedIssues.push(...this.detectMissingVerification(recentContext, recentContextStartIndex));
          break;
        case 'policy_violation':
          allDetectedIssues.push(...this.detectPolicyViolation(recentContext, recentContextStartIndex));
          break;
        case 'missed_upsell':
          allDetectedIssues.push(...this.detectMissedUpsell(recentContext, recentContextStartIndex));
          break;
        case 'escalation_risk':
          allDetectedIssues.push(...this.detectEscalationRisk(recentContext, recentContextStartIndex));
          break;
        default:
          // Unknown issue type, run all detectors as fallback
          console.warn(`[TranscriptMonitor] Unknown issue type: ${expectedIssueType}, running all detectors`);
          allDetectedIssues.push(...this.detectNoEmpathy(recentContext, 2, recentContextStartIndex));
          allDetectedIssues.push(...this.detectMissingVerification(recentContext, recentContextStartIndex));
          allDetectedIssues.push(...this.detectPolicyViolation(recentContext, recentContextStartIndex));
          allDetectedIssues.push(...this.detectMissedUpsell(recentContext, recentContextStartIndex));
          allDetectedIssues.push(...this.detectEscalationRisk(recentContext, recentContextStartIndex));
      }
    } else {
      // No expected issue type specified, run all detectors
      allDetectedIssues.push(...this.detectNoEmpathy(recentContext, 2, recentContextStartIndex));
      allDetectedIssues.push(...this.detectMissingVerification(recentContext, recentContextStartIndex));
      allDetectedIssues.push(...this.detectPolicyViolation(recentContext, recentContextStartIndex));
      allDetectedIssues.push(...this.detectMissedUpsell(recentContext, recentContextStartIndex));
      allDetectedIssues.push(...this.detectEscalationRisk(recentContext, recentContextStartIndex));
    }
    
    // Only keep ONE issue per turn
    // Priority: primaryCoach from scenario > severity > first detected
    const issues = [];
    if (allDetectedIssues.length > 0) {
      // Get primaryCoach from call metadata
      const callMeta = this.callMetadata?.get(currentTurn.call_id);
      const primaryCoach = callMeta?.primary_coach || null;
      
      // Map coach names to issue types
      const coachToIssueType = {
        'EmpathyCoach': 'no_empathy',
        'PolicyCoach': ['missing_verification', 'policy_violation'],
        'UpsellCoach': 'missed_upsell',
        'DeEscalationCoach': 'escalation_risk',
        'NewHireCoach': 'script_noncompliance'
      };
      
      // Extract primary coaches (can be comma-separated like "EmpathyCoach, PolicyCoach")
      const primaryCoaches = primaryCoach 
        ? primaryCoach.split(',').map(c => c.trim())
        : [];
      
      // Priority function: primaryCoach issues first, then by severity
      const severityOrder = { 'high': 3, 'medium': 2, 'low': 1 };
      allDetectedIssues.sort((a, b) => {
        // Check if issue matches primaryCoach
        const aIsPrimary = primaryCoaches.some(coach => {
          const issueTypes = coachToIssueType[coach];
          if (Array.isArray(issueTypes)) {
            return issueTypes.includes(a.issue_type);
          }
          return issueTypes === a.issue_type;
        });
        const bIsPrimary = primaryCoaches.some(coach => {
          const issueTypes = coachToIssueType[coach];
          if (Array.isArray(issueTypes)) {
            return issueTypes.includes(b.issue_type);
          }
          return issueTypes === b.issue_type;
        });
        
        // Primary coach issues come first
        if (aIsPrimary && !bIsPrimary) return -1;
        if (!aIsPrimary && bIsPrimary) return 1;
        
        // If both or neither are primary, sort by severity
        const aSeverity = severityOrder[a.severity] || 0;
        const bSeverity = severityOrder[b.severity] || 0;
        if (bSeverity !== aSeverity) {
          return bSeverity - aSeverity; // Higher severity first
        }
        
        // If same severity, keep original order (first detected)
        return 0;
      });
      
      issues.push(allDetectedIssues[0]); // Only keep the first (highest priority) issue
    }

    // Deduplicate: Only publish issues we haven't seen before
    // Use issue_type + detected_at_turn as the key
    for (const issue of issues) {
      const issueKey = `${issue.issue_type}_${issue.detected_at_turn}`;
      
      if (!detectedSet.has(issueKey)) {
        detectedSet.add(issueKey);
      await this.publishIssue(issue);
        console.log(
          `😍😍😍😍😍😍 published issue in turn ${turn.text}`
        );
      } else {
        console.log(
          `[TranscriptMonitor] ⏭️  Skipping duplicate issue: ${issue.issue_type} ` +
          `at turn ${issue.detected_at_turn} for call ${issue.call_id}`
        );
      }
    }

    
  }

  /**
   * Detect: Customer frustration not acknowledged
   * @param {Array} transcript - Recent transcript context (last few turns)
   * @param {number} window - Number of turns to look ahead for empathy
   * @param {number} offset - Turn index offset to adjust for absolute turn numbers
   */
  detectNoEmpathy(transcript, window = 2, offset = 0) {
    const issues = [];

    // Only check the LAST customer turn in the recent context (the new turn)
    // This ensures we only detect issues on the current turn, not re-check old ones
    for (let i = transcript.length - 1; i >= 0; i--) {
      const turn = transcript[i];
      
      if (turn.speaker === 'customer') {
        const hasFrustration = FRUSTRATION_PHRASES.some(phrase => 
          turn.text.toLowerCase().includes(phrase)
        );

        if (hasFrustration) {
          // Look ahead at next N rep turns (within the recent context)
          const repTurns = transcript.slice(i + 1, i + 1 + window)
            .filter(t => t.speaker === 'rep');

          if (repTurns.length > 0) {
            const hasEmpathy = repTurns.some(rt => 
              EMPATHY_PHRASES.some(phrase => rt.text.toLowerCase().includes(phrase))
            );

            if (!hasEmpathy) {
              const repId = this.getRepForCall(turn.call_id);
              const customerId = this.getCustomerForCall(turn.call_id);
              
              if (repId && customerId) {
                const repProfile = this.repProfiles.get(repId);
                const customerProfile = this.customerProfiles.get(customerId);
                
                if (repProfile && customerProfile) {
                  // Use absolute turn index (offset + relative index)
                  const absoluteTurnIndex = offset + i;
                  issues.push({
                    issue_id: `issue_${uuidv4()}`,
                    call_id: turn.call_id,
                    rep_id: repId,
                    issue_type: 'no_empathy',
                    severity: 'medium',
                    detected_at_turn: absoluteTurnIndex,
                    rep_profile: repProfile,
                    customer_profile: customerProfile,
                    transcript_snippet: transcript.slice(Math.max(0, i - 1), i + window + 1)
                  });
                }
              }
            }
          }
        }
        // Only check the most recent customer turn to avoid duplicates
        break;
      }
    }

    return issues;
  }

  /**
   * Detect: Accessing account without verification
   * @param {Array} transcript - Recent transcript context
   * @param {number} offset - Turn index offset
   */
  detectMissingVerification(transcript, offset = 0) {
    const issues = [];

    // Only check the LAST rep turn (the new turn)
    for (let i = transcript.length - 1; i >= 0; i--) {
        const turn = transcript[i];
        
        if (turn.speaker === 'rep') {
        // Check if this rep turn accessed account
          const accessedAccount = ACCOUNT_ACCESS_HINTS.some(hint =>
            turn.text.toLowerCase().includes(hint)
          );

          if (accessedAccount) {
          // Check if rep verified in recent context (last 5 turns)
          const recentContext = transcript.slice(Math.max(0, i - 4), i + 1);
          const hasVerified = recentContext.some(t => 
            t.speaker === 'rep' && 
            VERIFICATION_PHRASES.some(phrase => t.text.toLowerCase().includes(phrase))
          );

          if (!hasVerified) {
            const repId = this.getRepForCall(turn.call_id);
            const customerId = this.getCustomerForCall(turn.call_id);
            
            if (repId && customerId) {
              const repProfile = this.repProfiles.get(repId);
              const customerProfile = this.customerProfiles.get(customerId);
              
              if (repProfile && customerProfile) {
                const absoluteTurnIndex = offset + i;
                issues.push({
                  issue_id: `issue_${uuidv4()}`,
                  call_id: turn.call_id,
                  rep_id: repId,
                  issue_type: 'missing_verification',
                  severity: 'high',
                  detected_at_turn: absoluteTurnIndex,
                  rep_profile: repProfile,
                  customer_profile: customerProfile,
                  transcript_snippet: transcript.slice(Math.max(0, i - 2), i + 2)
                });
              }
            }
          }
        }
        // Only check the most recent rep turn
        break;
      }
    }

    return issues;
  }

  /**
   * Detect: Policy violation (unauthorized actions)
   * @param {Array} transcript - Recent transcript context
   * @param {number} offset - Turn index offset
   */
  detectPolicyViolation(transcript, offset = 0) {
    const issues = [];

    // Only check the LAST rep turn (the new turn)
    for (let i = transcript.length - 1; i >= 0; i--) {
      const turn = transcript[i];
      
      if (turn.speaker === 'rep') {
        const hasUnauthorizedAction = UNAUTHORIZED_ACTIONS.some(action =>
          turn.text.toLowerCase().includes(action)
        );

        if (hasUnauthorizedAction) {
          // Check if rep mentioned checking policy in recent context
          const recentContext = transcript.slice(Math.max(0, i - 4), i);
          const mentionedPolicy = recentContext.some(t =>
            t.speaker === 'rep' && 
            POLICY_PHRASES.some(phrase => t.text.toLowerCase().includes(phrase))
          );

          if (!mentionedPolicy) {
            const repId = this.getRepForCall(turn.call_id);
            const customerId = this.getCustomerForCall(turn.call_id);
            
            if (repId && customerId) {
              const repProfile = this.repProfiles.get(repId);
              const customerProfile = this.customerProfiles.get(customerId);
              
              if (repProfile && customerProfile) {
                const absoluteTurnIndex = offset + i;
                issues.push({
                  issue_id: `issue_${uuidv4()}`,
                  call_id: turn.call_id,
                  rep_id: repId,
                  issue_type: 'policy_violation',
                  severity: 'high',
                  detected_at_turn: absoluteTurnIndex,
                  rep_profile: repProfile,
                  customer_profile: customerProfile,
                  transcript_snippet: transcript.slice(Math.max(0, i - 2), i + 2)
                });
              }
            }
          }
        }
        // Only check the most recent rep turn
        break;
      }
    }

    return issues;
  }

  /**
   * Detect: Missed upsell opportunity
   * @param {Array} transcript - Recent transcript context
   * @param {number} offset - Turn index offset
   */
  detectMissedUpsell(transcript, offset = 0) {
    const issues = [];

    // Only check if the LAST customer turn mentioned future business (the new turn)
    const lastTurn = transcript[transcript.length - 1];
    if (lastTurn && lastTurn.speaker === 'customer') {
      const customerMentionedFuture = UPSELL_OPPORTUNITIES.some(opp => 
        lastTurn.text.toLowerCase().includes(opp)
    );

    if (customerMentionedFuture) {
        // Check if rep offered anything in recent context (last 3 turns)
        const recentContext = transcript.slice(Math.max(0, transcript.length - 3));
        const repOffered = recentContext.some(turn =>
        turn.speaker === 'rep' && (
          turn.text.toLowerCase().includes('would you like') ||
          turn.text.toLowerCase().includes('i can also') ||
          turn.text.toLowerCase().includes('you might benefit') ||
          turn.text.toLowerCase().includes('loyalty program') ||
          turn.text.toLowerCase().includes('upgrade')
        )
      );

      if (!repOffered) {
        const repId = this.getRepForCall(lastTurn.call_id);
        const customerId = this.getCustomerForCall(lastTurn.call_id);
        
        if (repId && customerId) {
          const repProfile = this.repProfiles.get(repId);
          const customerProfile = this.customerProfiles.get(customerId);
          
          if (repProfile && customerProfile) {
              const absoluteTurnIndex = offset + transcript.length - 1;
            issues.push({
              issue_id: `issue_${uuidv4()}`,
              call_id: lastTurn.call_id,
              rep_id: repId,
              issue_type: 'missed_upsell',
              severity: 'low',
                detected_at_turn: absoluteTurnIndex,
              rep_profile: repProfile,
              customer_profile: customerProfile,
              transcript_snippet: transcript.slice(Math.max(0, transcript.length - 5))
            });
            }
          }
        }
      }
    }

    return issues;
  }

  /**
   * Detect: Escalation risk (conversation heating up)
   * @param {Array} transcript - Recent transcript context
   * @param {number} offset - Turn index offset
   */
  detectEscalationRisk(transcript, offset = 0) {
    const issues = [];

    // Only check if the LAST turn is from customer with frustration
    const lastTurn = transcript[transcript.length - 1];
    if (lastTurn && lastTurn.speaker === 'customer') {
      const hasFrustration = FRUSTRATION_PHRASES.some(phrase => 
        lastTurn.text.toLowerCase().includes(phrase)
      );

      if (hasFrustration) {
        // Count customer frustration mentions in recent context (last 4 turns)
    const recentWindow = 4;
    const recentTurns = transcript.slice(-recentWindow);
    
    const frustrationCount = recentTurns.filter(turn =>
      turn.speaker === 'customer' &&
      FRUSTRATION_PHRASES.some(phrase => turn.text.toLowerCase().includes(phrase))
    ).length;

    // If 2+ frustration expressions in recent window = escalation risk
    if (frustrationCount >= 2) {
      const repId = this.getRepForCall(lastTurn.call_id);
      const customerId = this.getCustomerForCall(lastTurn.call_id);
      
      if (repId && customerId) {
        const repProfile = this.repProfiles.get(repId);
        const customerProfile = this.customerProfiles.get(customerId);
        
        if (repProfile && customerProfile) {
              const absoluteTurnIndex = offset + transcript.length - 1;
          issues.push({
            issue_id: `issue_${uuidv4()}`,
            call_id: lastTurn.call_id,
            rep_id: repId,
            issue_type: 'escalation_risk',
            severity: 'high',
                detected_at_turn: absoluteTurnIndex,
            rep_profile: repProfile,
            customer_profile: customerProfile,
            transcript_snippet: recentTurns
          });
            }
          }
        }
      }
    }

    return issues;
  }

  /**
   * Publish detected issue to Redis Streams
   */
  async publishIssue(issue) {
    try {
      // Store complete issue data in Redis for CrewAI manager
      const transcriptData = {
        issue_type: issue.issue_type,
        severity: issue.severity,
        call_id: issue.call_id,
        rep_id: issue.rep_id,
        detected_at_turn: issue.detected_at_turn,
        transcript_snippet: issue.transcript_snippet,
        rep_profile: issue.rep_profile,
        customer_profile: issue.customer_profile
      };

      // Store in Redis (fallback to regular SET if JSON.SET not available)
      try {
        await redis.call('JSON.SET', `transcript:${issue.issue_id}`, '$', JSON.stringify(transcriptData));
      } catch (e) {
        // Fallback to regular SET if JSON.SET not available
        await redis.set(`transcript:${issue.issue_id}`, JSON.stringify(transcriptData));
      }

      // Add pointer to stream
      await redis.xadd(
        'stream:contact_center:issues',
        '*',
        'event_id', issue.issue_id,
        'type', 'contact_center.issue.detected',
        'subject', `rep_${issue.rep_id}`,
        'rep_id', issue.rep_id,
        'call_id', issue.call_id,
        'issue_type', issue.issue_type,
        'severity', issue.severity
      );

      console.log(
        `😜😜😜😜😜😜 detected issue ${issue.issue_type} then added to redis`
      );

      // Also emit to EventBus for UI updates
      this.eventBus.emit('issue.detected', issue);

    } catch (error) {
      console.error('[TranscriptMonitor] Error publishing issue:', error);
    }
  }

  /**
   * Get rep ID for a call (would come from call metadata in real system)
   */
  getRepForCall(callId) {
    // First try call metadata
    if (this.callMetadata && this.callMetadata.has(callId)) {
      return this.callMetadata.get(callId).rep_id || null;
    }
    // Fallback: extract from stored turns
    const turns = this.callTranscripts.get(callId);
    if (turns && turns.length > 0) {
      return turns[0].rep_id || null;
    }
    return null;
  }

  /**
   * Get customer ID for a call
   */
  getCustomerForCall(callId) {
    // First try call metadata
    if (this.callMetadata && this.callMetadata.has(callId)) {
      return this.callMetadata.get(callId).customer_id || null;
    }
    // Fallback: extract from stored turns
    const turns = this.callTranscripts.get(callId);
    if (turns && turns.length > 0) {
      return turns[0].customer_id || null;
    }
    return null;
  }

  /**
   * Start a new call with rep and customer IDs
   */
  startCall(callId, repId, customerId, primaryCoach = null) {
    this.callTranscripts.set(callId, []);
    if (!this.callMetadata) {
      this.callMetadata = new Map();
    }
    this.callMetadata.set(callId, { 
      rep_id: repId, 
      customer_id: customerId,
      primary_coach: primaryCoach 
    });
    console.log(`[TranscriptMonitor] Started monitoring call ${callId} (rep: ${repId}, customer: ${customerId}, primaryCoach: ${primaryCoach || 'none'})`);
  }

  /**
   * Ingest a turn (from ASR or simulation)
   */
  async ingestTurn(turn) {
    // Store rep/customer IDs with turn for lookup
    // Ensure call_id is set
    if (!turn.call_id) {
      console.warn('[TranscriptMonitor] Turn missing call_id');
      return;
    }
    
    // Store rep_id and customer_id with the turn for later lookup
    if (turn.rep_id) {
      // Store in a metadata map for this call
      if (!this.callMetadata) {
        this.callMetadata = new Map();
      }
      if (!this.callMetadata.has(turn.call_id)) {
        this.callMetadata.set(turn.call_id, {});
      }
      this.callMetadata.get(turn.call_id).rep_id = turn.rep_id;
    }
    
    if (turn.customer_id) {
      if (!this.callMetadata) {
        this.callMetadata = new Map();
      }
      if (!this.callMetadata.has(turn.call_id)) {
        this.callMetadata.set(turn.call_id, {});
      }
      this.callMetadata.get(turn.call_id).customer_id = turn.customer_id;
    }
    
    await this.processTurn(turn);
  }
}

export default TranscriptMonitor;

