# Contact Center Coaching Mechanism - Testing Guide

## Overview

This guide explains how to test the contact center coaching mechanism, which includes:
1. **TranscriptMonitor** - Detects issues in real-time call transcripts
2. **ContactCenterCoachingCrew** - Provides AI-powered coaching to reps
3. **API Routes** - REST endpoints for managing calls, reps, and customers

## Prerequisites

1. **Node.js server running**:
   ```bash
   cd NEW_CREWAI_AGENT
   npm start
   ```
   Server should be running on `http://localhost:3000`

2. **Redis running** (optional but recommended):
   ```bash
   redis-server
   ```
   Note: The system will work without Redis, but issue detection results won't be persisted.

3. **Python Coaching Crew** (optional):
   ```bash
   cd agents/crewai_python/crews/contact-center
   python ContactCenterCoachingCrew.py
   ```

## Test Methods

### Method 1: Automated Test Script

Run the comprehensive test script:

```bash
cd NEW_CREWAI_AGENT
node scripts/test-contact-center-coaching.js
```

This script will:
- Register a rep profile
- Register a customer profile
- Start a call
- Send transcript turns that trigger issues
- Check for detected issues
- Display analytics

### Method 2: Manual API Testing with cURL

#### Step 1: Register Rep Profile

```bash
curl -X POST http://localhost:3000/api/contact-center/reps \
  -H "Content-Type: application/json" \
  -d '{
    "rep_id": "rep_1",
    "name": "Demo Rep",
    "tenure_months": 3,
    "skill_level": "novice",
    "vertical_specialty": "hotel",
    "language": "en",
    "avg_aht_seconds": 300,
    "avg_csat": 3.8,
    "compliance_score": 75.0,
    "upsell_rate": 0.10,
    "top_training_needs": ["empathy", "policy_adherence"]
  }'
```

#### Step 2: Register Customer Profile

```bash
curl -X POST http://localhost:3000/api/contact-center/customers \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "customer_1",
    "segment": "business",
    "vertical": "hotel",
    "sentiment_tendency": "impatient"
  }'
```

#### Step 3: Start a Call

```bash
curl -X POST http://localhost:3000/api/contact-center/calls/start \
  -H "Content-Type: application/json" \
  -d '{
    "call_id": "call_1",
    "rep_id": "rep_1",
    "customer_id": "customer_1"
  }'
```

#### Step 4: Send Transcript Turns

**Turn 0 - Customer expresses frustration:**
```bash
curl -X POST http://localhost:3000/api/contact-center/calls/call_1/turns \
  -H "Content-Type: application/json" \
  -d '{
    "turn_index": 0,
    "speaker": "customer",
    "text": "Hi, I just arrived at the hotel and they say you are overbooked. I do not have a room!",
    "timestamp": "2024-01-01T10:00:00Z",
    "rep_id": "rep_1",
    "customer_id": "customer_1"
  }'
```

**Turn 1 - Rep fails to show empathy (triggers no_empathy issue):**
```bash
curl -X POST http://localhost:3000/api/contact-center/calls/call_1/turns \
  -H "Content-Type: application/json" \
  -d '{
    "turn_index": 1,
    "speaker": "rep",
    "text": "Can you give me your confirmation number?",
    "timestamp": "2024-01-01T10:00:05Z",
    "rep_id": "rep_1",
    "customer_id": "customer_1"
  }'
```

**Turn 2 - Customer provides info:**
```bash
curl -X POST http://localhost:3000/api/contact-center/calls/call_1/turns \
  -H "Content-Type: application/json" \
  -d '{
    "turn_index": 2,
    "speaker": "customer",
    "text": "It is ABC123. This is ridiculous and very frustrating!",
    "timestamp": "2024-01-01T10:00:10Z",
    "rep_id": "rep_1",
    "customer_id": "customer_1"
  }'
```

**Turn 3 - Rep accesses account without verification (triggers missing_verification issue):**
```bash
curl -X POST http://localhost:3000/api/contact-center/calls/call_1/turns \
  -H "Content-Type: application/json" \
  -d '{
    "turn_index": 3,
    "speaker": "rep",
    "text": "I see your booking here in the system.",
    "timestamp": "2024-01-01T10:00:15Z",
    "rep_id": "rep_1",
    "customer_id": "customer_1"
  }'
```

#### Step 5: Check Detected Issues

Wait a few seconds for processing, then:

```bash
curl http://localhost:3000/api/contact-center/issues?call_id=call_1
```

#### Step 6: Get Analytics

```bash
curl http://localhost:3000/api/contact-center/analytics/summary
```

### Method 3: Complete Call Simulation

Use the simulation endpoint to send all turns at once:

```bash
curl -X POST http://localhost:3000/api/contact-center/simulate/call \
  -H "Content-Type: application/json" \
  -d '{
    "call_id": "call_sim_1",
    "rep_id": "rep_1",
    "customer_id": "customer_1",
    "turns": [
      {
        "turn_index": 0,
        "speaker": "customer",
        "text": "Hi, I just arrived at the hotel and they say you are overbooked. I do not have a room!",
        "timestamp": "2024-01-01T10:00:00Z"
      },
      {
        "turn_index": 1,
        "speaker": "rep",
        "text": "Can you give me your confirmation number?",
        "timestamp": "2024-01-01T10:00:05Z"
      },
      {
        "turn_index": 2,
        "speaker": "customer",
        "text": "It is ABC123. This is ridiculous!",
        "timestamp": "2024-01-01T10:00:10Z"
      },
      {
        "turn_index": 3,
        "speaker": "rep",
        "text": "I see your booking here in the system.",
        "timestamp": "2024-01-01T10:00:15Z"
      }
    ]
  }'
```

## Expected Issues Detected

Based on the test transcript, you should see:

1. **no_empathy** (medium severity)
   - Triggered when: Customer expresses frustration, rep doesn't acknowledge
   - Turn: 1

2. **missing_verification** (high severity)
   - Triggered when: Rep accesses account without security verification
   - Turn: 3

3. **policy_violation** (high severity)
   - Triggered when: Rep offers refund without checking policy
   - Turn: 5 (if included)

4. **missed_upsell** (low severity)
   - Triggered when: Customer mentions future travel, rep doesn't offer loyalty program
   - Turn: 7 (if included)

## Verifying Detection

### Check Server Logs

The TranscriptMonitor will log detected issues:
```
[TranscriptMonitor] 🚨 Detected no_empathy (medium) on call call_1 at turn 1
[TranscriptMonitor] 🚨 Detected missing_verification (high) on call call_1 at turn 3
```

### Check Redis Streams (if Redis is running)

```bash
redis-cli XRANGE stream:contact_center:issues - + COUNT 10
```

### Check API Response

```bash
curl http://localhost:3000/api/contact-center/issues?call_id=call_1
```

Expected response:
```json
{
  "issues": [
    {
      "message_id": "...",
      "event_id": "issue_...",
      "type": "contact_center.issue.detected",
      "rep_id": "rep_1",
      "call_id": "call_1",
      "issue_type": "no_empathy",
      "severity": "medium"
    },
    ...
  ],
  "count": 2
}
```

## Troubleshooting

### No Issues Detected

1. **Check if Redis is running**:
   ```bash
   redis-cli ping
   ```
   Should return `PONG`

2. **Check server logs** for errors:
   ```bash
   tail -f /tmp/server.log
   ```

3. **Verify TranscriptMonitor is processing**:
   - Check server console for `[TranscriptMonitor]` logs
   - Verify rep and customer profiles are registered

4. **Check if turns include rep_id and customer_id**:
   - These are required for issue detection

### Server Not Starting

1. **Check if port 3000 is in use**:
   ```bash
   lsof -i :3000
   ```

2. **Check for missing dependencies**:
   ```bash
   npm install
   ```

3. **Check for Redis connection errors**:
   - Server will start even if Redis is not available
   - Issue detection will work, but results won't be persisted

### Issues Not Appearing in API

1. **Redis JSON module not enabled**:
   - The system will fall back to regular SET if JSON.SET is not available
   - Full issue details might not be retrievable

2. **Stream not being read correctly**:
   - Check Redis Stream: `redis-cli XRANGE stream:contact_center:issues - +`

## Next Steps

Once basic detection is working:

1. **Start the Coaching Crew** to generate coaching messages
2. **Monitor coaching stream**: `stream:coaching:messages`
3. **Check coaching sessions API**: `/api/contact-center/coaching/sessions`

## Test Scenarios

### Scenario 1: Empathy Issue
- Customer: "This is ridiculous!"
- Rep: "What's your booking number?" (no empathy)
- Expected: `no_empathy` detected

### Scenario 2: Verification Issue
- Rep: "I see your booking here" (without verification)
- Expected: `missing_verification` detected

### Scenario 3: Policy Violation
- Rep: "I'll refund everything right now" (without checking policy)
- Expected: `policy_violation` detected

### Scenario 4: Missed Upsell
- Customer: "I travel for business often"
- Rep: "Goodbye" (no upsell offer)
- Expected: `missed_upsell` detected

### Scenario 5: Escalation Risk
- Multiple customer frustration expressions in recent turns
- Expected: `escalation_risk` detected

