#!/usr/bin/env node
/**
 * Stream Transcript
 * Generates a realistic call transcript in real time and sends to the
 * TranscriptMonitor API endpoint. With the automatic router and coaching crew
 * running, coaching messages will flow to the frontend via WebSocket.
 *
 * Usage:
 *   node scripts/stream-transcript.js --rep demo_rep_1 --customer demo_customer_1 --call demo_call_1 [--delay=12000]
 *   API_URL=https://your-backend.example.com node scripts/stream-transcript.js
 * 
 * Note: Default delay is 12 seconds to allow coaching agent time to process each turn
 *       and generate coaching responses before the next turn arrives.
 */

import axios from 'axios';

const args = Object.fromEntries(
  process.argv.slice(2).map((a) => {
    const [k, v] = a.replace(/^--/, '').split('=');
    return [k, v || true];
  })
);

const API_BASE = process.env.API_URL || 'http://localhost:3001';
const API_PREFIX = `${API_BASE}/api/contact-center`;

const repId = args.rep || 'demo_rep_1';
const customerId = args.customer || 'demo_customer_1';
const callId = args.call || `call_demo_${Date.now()}`;
// Increased default delay to allow coaching agent time to process and respond
// Coaching agent needs time for: detection -> routing -> generation -> WebSocket delivery
const DELAY_MS = Number(args.delay || process.env.DELAY_MS || 12000); // 12 seconds default
const COACHING_PROCESSING_TIME = 8000; // Additional time for coaching agent to process

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

async function ensureProfiles() {
  try {
    await axios.post(`${API_PREFIX}/reps`, {
      rep_id: repId,
      name: 'Demo Rep',
      tenure_months: 4,
      skill_level: 'novice',
      vertical_specialty: 'hotel',
      language: 'en',
      avg_aht_seconds: 360,
      avg_csat: 3.7,
      compliance_score: 74.0,
      upsell_rate: 0.09,
      top_training_needs: ['empathy', 'policy_adherence']
    }).catch(() => {});
  } catch (_) {}

  try {
    await axios.post(`${API_PREFIX}/customers`, {
      customer_id: customerId,
      segment: 'business',
      vertical: 'hotel',
      sentiment_tendency: 'impatient'
    }).catch(() => {});
  } catch (_) {}
}

async function startCall() {
  await axios.post(`${API_PREFIX}/calls/start`, {
    call_id: callId,
    rep_id: repId,
    customer_id: customerId
  });
  // eslint-disable-next-line no-console
  console.log(`📞 Started call: ${callId} (rep: ${repId})`);
}

async function sendTurn(turn_index, speaker, text, timestamp) {
  await axios.post(`${API_PREFIX}/calls/${callId}/turns`, {
    turn_index,
    speaker,
    text,
    timestamp
  });
  // eslint-disable-next-line no-console
  console.log(`➡️  Sent turn ${turn_index} (${speaker}): ${text.slice(0, 80)}${text.length > 80 ? '...' : ''}`);
  
  // Wait for coaching agent to process this turn before sending next one
  // This ensures sequential processing and allows coaching responses to appear
  if (speaker === 'rep' || speaker === 'customer') {
    // eslint-disable-next-line no-console
    console.log(`⏳ Waiting ${COACHING_PROCESSING_TIME / 1000}s for coaching agent to process...`);
    await sleep(COACHING_PROCESSING_TIME);
  }
}

// Seed utterances to build longer conversations
const customerUtterances = [
  "Hi, I just arrived and the hotel says they're overbooked.",
  "This is ridiculous and very frustrating!",
  "I really need a room tonight — I'm here for a conference.",
  "I've been waiting for 20 minutes already.",
  "Why wasn't I notified earlier about this issue?",
  "It's ABC123, can you find my reservation?",
  "I want a full refund and a room at a nearby hotel.",
  "I expect some compensation for the inconvenience.",
  "Is there a supervisor I can speak to?",
  "Please confirm how long this will take."
];

const repUtterances = [
  "I completely understand how frustrating this is and I'm here to help.",
  "Could you please confirm your full name and email address?",
  "I see your booking. Let me check what happened.",
  "Thank you for your patience while I review your case.",
  "I'm coordinating with the front desk to prioritize your check-in.",
  "Let me check nearby partner hotels for availability.",
  "I'll escalate this to my supervisor and find a quick solution.",
  "I'll arrange transportation to the new hotel if needed.",
  "We can offer a refund and a one-night voucher for the inconvenience.",
  "I'll stay with you on the line until this is fully resolved."
];

function pick(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}

async function streamForever(startIndex = 0) {
  // Send turns sequentially with delays to allow coaching agent processing
  const scripted = [
    { s: 'customer', t: customerUtterances[0] },
    { s: 'rep',      t: repUtterances[0] },
    { s: 'customer', t: customerUtterances[1] },
    { s: 'rep',      t: repUtterances[2] },
    { s: 'customer', t: customerUtterances[2] },
    { s: 'rep',      t: repUtterances[1] },
    { s: 'customer', t: customerUtterances[3] },
    { s: 'rep',      t: repUtterances[3] },
    { s: 'customer', t: customerUtterances[4] },
    { s: 'rep',      t: repUtterances[5] }
  ];

  let idx = startIndex;
  const baseTime = Date.now();

  // Send initial scripted turns sequentially
  for (const turn of scripted) {
    await sendTurn(idx++, turn.s, turn.t, new Date(baseTime + idx * 1000).toISOString());
    // Additional delay between turns (beyond the processing time in sendTurn)
    const additionalDelay = Math.max(0, DELAY_MS - COACHING_PROCESSING_TIME);
    if (additionalDelay > 0) {
      await sleep(additionalDelay);
    }
  }

  // Then continue indefinitely with generated turns, sent sequentially
  // eslint-disable-next-line no-constant-condition
  while (true) {
    const speaker = Math.random() < 0.5 ? 'customer' : 'rep';
    const text = speaker === 'customer' ? pick(customerUtterances) : pick(repUtterances);
    await sendTurn(idx, speaker, text, new Date().toISOString());
    idx += 1;
    // Additional delay between turns (beyond the processing time in sendTurn)
    const additionalDelay = Math.max(0, DELAY_MS - COACHING_PROCESSING_TIME);
    if (additionalDelay > 0) {
      await sleep(additionalDelay);
    }
  }
}

async function run() {
  // eslint-disable-next-line no-console
  console.log('🚀 Streaming real-time transcript to TranscriptMonitor (continuous mode)...');
  await ensureProfiles();
  await startCall();

  // Stream without stopping; press Ctrl+C to exit
  await streamForever(0);
}

process.on('SIGINT', () => {
  // eslint-disable-next-line no-console
  console.log('\n🛑 Stopping transcript streaming.');
  process.exit(0);
});

run().catch((e) => {
  // eslint-disable-next-line no-console
  console.error('❌ Error streaming transcript:', e.message || e);
  process.exit(1);
});


