# Contact Center Coaching Mechanism - Copy Summary

This document summarizes the call center coaching mechanism that was copied from `IMS-call-center` to `NEW_CREWAI_AGENT`.

## Files Copied

### 1. TranscriptMonitor Service
**Location**: `src/services/contact-center/TranscriptMonitor.ts`

Real-time transcript monitoring service that:
- Ingests streaming call transcript turns
- Detects 6 types of issues:
  - No empathy (customer frustration not acknowledged)
  - Missing verification (accessing accounts without security check)
  - Policy violations (unauthorized actions)
  - Missed upsells (good opportunities not taken)
  - Script non-compliance (required steps skipped)
  - Escalation risk (conversation getting heated)
- Publishes detected issues to Redis Streams

### 2. ContactCenterCoachingCrew
**Location**: `agents/crewai_python/crews/contact-center/ContactCenterCoachingCrew.py`

CrewAI hierarchical crew with:
- **Manager**: CoachingCoordinator (routes issues to specialists)
- **5 Specialist Coaches**:
  - EmpathyCoach
  - PolicyCoach
  - UpsellCoach
  - NewHireCoach
  - DeEscalationCoach

### 3. Contact Center API Routes
**Location**: `src/api/routes/contact-center-routes.js`

REST API endpoints for:
- Rep profile management
- Customer profile management
- Call management
- Transcript turn ingestion
- Issue detection queries
- Coaching session queries
- Analytics
- Call simulation (for demo)

### 4. CrewAIManagerService
**Location**: `agents/crewai_python/CrewAIManagerService.py`

Service that wraps CrewAI hierarchical crews:
- Consumes from manager-specific route streams
- Delegates to crew (manager + workers)
- Publishes validated results to target streams
- Handles DLQ, metrics, and heartbeats

### 5. EventBus Implementation
**Location**: `src/services/events/EventBus.ts`

In-memory event bus for local event communication:
- Supports both EventEmitter and InMemoryEventBus patterns
- Used for UI updates and local state sync

## Integration Points

### Server Integration
The contact-center routes are integrated into `src/server.js`:
- Express middleware added for `/api/contact-center/*` routes
- Routes are accessible at: `http://localhost:3000/api/contact-center/*`

### Dependencies Required

Make sure these packages are installed:
```bash
npm install express ioredis uuid
```

For Python agents:
```bash
pip install crewai redis requests
```

## Usage

### 1. Start the Coaching Crew

```bash
cd agents/crewai_python/crews/contact-center
python ContactCenterCoachingCrew.py
```

### 2. Register the Crew (Optional)

The crew can be registered via API:
```bash
curl -X POST http://localhost:3000/api/managers/register \
  -H "Content-Type: application/json" \
  -d '{
    "manager_id": "coaching-manager",
    "crew_id": "contact-center-coaching-crew",
    "route_stream": "stream:route.decisions:coaching-manager",
    "consumes_types": ["contact_center.issue.detected"],
    "produces_streams": ["stream:coaching:messages"],
    "produces_schemas": ["CoachingMessageV1"],
    "capabilities": [
      "real_time_coaching",
      "empathy_training",
      "policy_compliance",
      "upsell_guidance",
      "new_hire_support",
      "de_escalation"
    ]
  }'
```

### 3. Start a Call

```bash
curl -X POST http://localhost:3000/api/contact-center/calls/start \
  -H "Content-Type: application/json" \
  -d '{
    "call_id": "call_123",
    "rep_id": "rep_1",
    "customer_id": "customer_1"
  }'
```

### 4. Ingest Transcript Turns

```bash
curl -X POST http://localhost:3000/api/contact-center/calls/call_123/turns \
  -H "Content-Type: application/json" \
  -d '{
    "turn_index": 1,
    "speaker": "customer",
    "text": "This is ridiculous!",
    "timestamp": "2024-01-01T10:00:00Z"
  }'
```

### 5. Simulate a Complete Call

```bash
curl -X POST http://localhost:3000/api/contact-center/simulate/call \
  -H "Content-Type: application/json" \
  -d '{
    "call_id": "call_123",
    "rep_id": "rep_1",
    "customer_id": "customer_1",
    "turns": [
      {"turn_index": 1, "speaker": "customer", "text": "This is ridiculous!", "timestamp": "2024-01-01T10:00:00Z"},
      {"turn_index": 2, "speaker": "rep", "text": "What is your booking number?", "timestamp": "2024-01-01T10:00:05Z"}
    ]
  }'
```

## Architecture Flow

```
Live Call Transcript (ASR)
    ↓ (streams transcript turns)
POST /api/contact-center/calls/:callId/turns
    ↓
TranscriptMonitor.ts (detects issues)
    ↓ (publishes to Redis Stream)
stream:contact_center:issues
    ↓
ContactCenterCoachingCrew.py (processes issue)
    ↓ (publishes to Redis Stream)
stream:coaching:messages
    ↓
WebSocket/API (delivers to UI)
    ↓
Rep Console (displays coaching popup)
```

## Key Features

- **Real-Time Detection**: < 100ms to detect issues in streaming transcripts
- **5 Specialized Coaches**: Empathy, Policy, Upsell, NewHire, DeEscalation
- **Instant Feedback**: < 5 seconds from detection to coaching popup
- **Actionable Scripts**: Ready-to-use lines the rep can say RIGHT NOW
- **Context-Aware**: Tailored to rep profile (tenure, CSAT, compliance score)

## Configuration

### Environment Variables

```bash
REDIS_URL=redis://localhost:6379
API_URL=http://localhost:3000
```

### Redis Streams Used

- `stream:contact_center:issues` - Detected issues from TranscriptMonitor
- `stream:coaching:messages` - Coaching messages from CrewAI crew
- `stream:route.decisions:coaching-manager` - Route decisions for coaching manager

## Notes

- The system assumes ASR (Automatic Speech Recognition) is external and provides transcript turns
- TranscriptMonitor uses rule-based detection (can be enhanced with ML models)
- All coaching messages are validated against JSON schemas before publishing
- The system supports both real-time streaming and batch simulation

## Next Steps

1. Install dependencies: `npm install express ioredis uuid`
2. Start Redis: `redis-server`
3. Start the server: `npm start` or `node src/server.js`
4. Start the coaching crew: `python agents/crewai_python/crews/contact-center/ContactCenterCoachingCrew.py`
5. Test with the simulation endpoint

