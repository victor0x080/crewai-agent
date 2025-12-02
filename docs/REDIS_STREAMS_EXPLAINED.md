# Redis Streams: Input/Output Relationship Explained

## Overview

Redis Streams are like a **message queue** where:
- **INPUT (Write)**: Producers use `XADD` to write messages
- **OUTPUT (Read)**: Consumers use `XREAD`, `XREADGROUP`, or `XRANGE` to read messages

---

## Basic Concepts

### 1. Writing to Streams (INPUT) - `XADD`

**Syntax:**
```redis
XADD stream_name * field1 value1 field2 value2 ...
```

**What it does:**
- Adds a new message to the stream
- `*` = Auto-generate message ID (timestamp-sequence)
- Returns the message ID (e.g., `1764084108851-0`)

**Example from TranscriptMonitor.js:**
```javascript
// INPUT: Writing an issue to the stream
await redis.xadd(
  'stream:contact_center:issues',  // Stream name
  '*',                              // Auto-generate ID
  'event_id', issue.issue_id,       // Field-value pairs
  'type', cloudEvent.type,
  'subject', cloudEvent.subject,
  'rep_id', issue.rep_id,
  'call_id', issue.call_id,
  'issue_type', issue.issue_type,
  'severity', issue.severity
);

// Returns: "1764084108851-0" (message ID)
```

**What happens:**
```
┌─────────────────────────────────────────┐
│ TranscriptMonitor (Producer)            │
│ Detects: no_empathy issue                │
└───────────────┬─────────────────────────┘
                │ XADD
                ↓
┌─────────────────────────────────────────┐
│ stream:contact_center:issues            │
│ Message ID: 1764084108851-0              │
│ Fields:                                   │
│   event_id: "issue_abc123"               │
│   type: "contact_center.issue.detected"  │
│   issue_type: "no_empathy"                │
│   severity: "medium"                      │
└─────────────────────────────────────────┘
```

---

### 2. Reading from Streams (OUTPUT) - Three Methods

#### Method 1: `XRANGE` - Read Historical Messages

**Syntax:**
```redis
XRANGE stream_name start_id end_id [COUNT limit]
```

**What it does:**
- Reads messages within a range
- `-` = Start from beginning
- `+` = End at latest
- Returns all messages in range

**Example from contact-center-routes.js:**
```javascript
// OUTPUT: Reading coaching messages (historical)
const messages = await redis.xrange(
  'stream:coaching:messages',  // Stream name
  '-',                          // Start from beginning
  '+',                          // End at latest
  'COUNT',                      // Limit
  100                           // Max 100 messages
);

// Returns: [
//   ["1764084108851-0", ["event_id", "coaching_123", "type", "coaching.message.created", ...]],
//   ["1764084108852-0", ["event_id", "coaching_124", "type", "coaching.message.created", ...]]
// ]
```

**Use Case:** API endpoints reading historical data

---

#### Method 2: `XREAD` - Read New Messages (Simple Consumer)

**Syntax:**
```redis
XREAD [COUNT count] [BLOCK milliseconds] STREAMS stream_name start_id
```

**What it does:**
- Reads new messages from a position
- `$` = Only new messages (after current position)
- `BLOCK` = Wait for new messages (blocking)
- Returns messages as they arrive

**Example:**
```python
# OUTPUT: Reading new issues (simple consumer)
messages = redis_client.xread(
    {'stream:contact_center:issues': '$'},  # Stream and start position
    count=10,                                # Max messages
    block=5000                               # Block 5 seconds if no messages
)

# Returns: [
#   ('stream:contact_center:issues', [
#     ('1764084108851-0', {'event_id': 'issue_123', 'type': '...', ...})
#   ])
# ]
```

**Use Case:** Simple consumers that don't need consumer groups

---

#### Method 3: `XREADGROUP` - Consumer Groups (Advanced)

**Syntax:**
```redis
XREADGROUP GROUP group_name consumer_name [COUNT count] [BLOCK milliseconds] STREAMS stream_name position
```

**What it does:**
- Reads messages in a consumer group
- `>` = Read pending messages for this consumer
- Distributes messages across multiple consumers
- Tracks which messages are being processed

**Example from CrewAIManagerService.py:**
```python
# OUTPUT: Reading route decisions (consumer group)
messages = redis_client.xreadgroup(
    'coaching',                              # Consumer group name
    'coaching-1',                            # Consumer name
    {'stream:route.decisions:coaching-manager': '>'},  # Stream and position
    count=1,                                 # Max messages per read
    block=5000                               # Block 5 seconds
)

# Returns: [
#   ('stream:route.decisions:coaching-manager', [
#     ('1764084181238-0', {
#       'event_id': 'issue_abc123',
#       'target_stream': 'stream:coaching:messages',
#       'target_schema': 'CoachingMessageV1'
#     })
#   ])
# ]
```

**Use Case:** Multiple workers processing messages (load balancing)

---

## Complete Flow Example: Call Center Coaching

### Step 1: INPUT - Issue Detection

**Producer:** `TranscriptMonitor.js`

```javascript
// INPUT: Writing detected issue
const messageId = await redis.xadd(
  'stream:contact_center:issues',
  '*',
  'event_id', 'issue_abc123',
  'type', 'contact_center.issue.detected',
  'rep_id', 'rep_45',
  'call_id', 'call_789',
  'issue_type', 'no_empathy',
  'severity', 'medium'
);

console.log(`Published issue: ${messageId}`);
// Output: "Published issue: 1764084108851-0"
```

**Stream State:**
```
stream:contact_center:issues
├─ 1764084108851-0
│  ├─ event_id: "issue_abc123"
│  ├─ type: "contact_center.issue.detected"
│  ├─ rep_id: "rep_45"
│  ├─ call_id: "call_789"
│  ├─ issue_type: "no_empathy"
│  └─ severity: "medium"
```

---

### Step 2: OUTPUT - Reading Issues (API)

**Consumer:** API Endpoint

```javascript
// OUTPUT: Reading issues for API response
const messages = await redis.xrange(
  'stream:contact_center:issues',
  '-',
  '+',
  'COUNT',
  20
);

// Convert to objects
const issues = messages.map(([msgId, fields]) => {
  const obj = {};
  for (let i = 0; i < fields.length; i += 2) {
    obj[fields[i]] = fields[i + 1];
  }
  return {
    message_id: msgId,
    ...obj
  };
});

// Returns:
// [
//   {
//     message_id: "1764084108851-0",
//     event_id: "issue_abc123",
//     issue_type: "no_empathy",
//     severity: "medium",
//     ...
//   }
// ]
```

---

### Step 3: INPUT - Routing Decision

**Producer:** Routing Service / Test Script

```javascript
// INPUT: Writing route decision
const routeId = await redis.xadd(
  'stream:route.decisions:coaching-manager',
  '*',
  'event_id', 'issue_abc123',
  'source_stream', 'stream:contact_center:issues',
  'target_stream', 'stream:coaching:messages',
  'target_schema', 'CoachingMessageV1'
);

console.log(`Routed issue: ${routeId}`);
// Output: "Routed issue: 1764084181238-0"
```

**Stream State:**
```
stream:route.decisions:coaching-manager
├─ 1764084181238-0
│  ├─ event_id: "issue_abc123"
│  ├─ source_stream: "stream:contact_center:issues"
│  ├─ target_stream: "stream:coaching:messages"
│  └─ target_schema: "CoachingMessageV1"
```

---

### Step 4: OUTPUT - Consuming Route Decisions

**Consumer:** `CrewAIManagerService.py` (Consumer Group)

```python
# OUTPUT: Reading route decisions (consumer group)
messages = redis_client.xreadgroup(
    'coaching',                              # Group name
    'coaching-1',                           # Consumer name
    {'stream:route.decisions:coaching-manager': '>'},  # Read pending
    count=1,
    block=5000
)

# Process message
for stream, entries in messages:
    for message_id, fields in entries:
        event_id = fields['event_id']
        target_stream = fields['target_stream']
        
        # Process issue and generate coaching...
        
        # Acknowledge after processing
        redis_client.xack(
            'stream:route.decisions:coaching-manager',
            'coaching',
            message_id
        )
```

**What happens:**
- Message is read by `coaching-1` consumer
- Message becomes "pending" in the consumer group
- After processing, message is acknowledged (`XACK`)
- If consumer crashes, message remains pending and can be claimed by another consumer

---

### Step 5: INPUT - Publishing Coaching Message

**Producer:** `CrewAIManagerService.py`

```python
# INPUT: Writing coaching message
message_id = redis_client.xadd(
    'stream:coaching:messages',  # Target stream
    {
        'event_id': 'coaching_xyz789',
        'type': 'coaching.message.created',
        'subject': 'rep_45',
        'data': json.dumps({
            'agent_name': 'EmpathyCoach',
            'title': 'Show Empathy to Defuse Frustration',
            'message': 'When a customer expresses frustration...',
            'suggested_responses': [
                "I understand this must be frustrating...",
                "I'm sorry you're experiencing this..."
            ]
        })
    }
)

print(f"Published coaching: {message_id}")
# Output: "Published coaching: 1764084200000-0"
```

**Stream State:**
```
stream:coaching:messages
├─ 1764084200000-0
│  ├─ event_id: "coaching_xyz789"
│  ├─ type: "coaching.message.created"
│  ├─ subject: "rep_45"
│  └─ data: "{'agent_name': 'EmpathyCoach', ...}"
```

---

### Step 6: OUTPUT - Reading Coaching Messages (API)

**Consumer:** API Endpoint

```javascript
// OUTPUT: Reading coaching messages for API
const messages = await redis.xrange(
  'stream:coaching:messages',
  '-',
  '+',
  'COUNT',
  100
);

// Filter by rep_id
const repCoaching = messages
  .map(([msgId, fields]) => {
    const obj = {};
    for (let i = 0; i < fields.length; i += 2) {
      obj[fields[i]] = fields[i + 1];
    }
    return { message_id: msgId, ...obj };
  })
  .filter(msg => msg.subject === `rep_${repId}`);

// Returns coaching messages for the rep
```

---

## Visual Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ PRODUCER: TranscriptMonitor.js                            │
│ INPUT: XADD                                                │
└───────────────────────┬───────────────────────────────────┘
                        │
                        │ XADD stream:contact_center:issues
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ stream:contact_center:issues                                │
│ Message: 1764084108851-0                                    │
└───────────────────────┬───────────────────────────────────┘
                        │
                        │ OUTPUT: XRANGE / XREAD
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ CONSUMER: API Endpoint / Routing Service                   │
│ Reads issues                                                │
└───────────────────────┬───────────────────────────────────┘
                        │
                        │ Routes to coaching
                        │ INPUT: XADD
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ stream:route.decisions:coaching-manager                    │
│ Message: 1764084181238-0                                    │
└───────────────────────┬───────────────────────────────────┘
                        │
                        │ OUTPUT: XREADGROUP
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ CONSUMER: CrewAIManagerService.py                          │
│ Consumer Group: coaching                                    │
│ Consumer: coaching-1                                        │
│ Reads route decisions                                       │
└───────────────────────┬───────────────────────────────────┘
                        │
                        │ Processes & generates coaching
                        │ INPUT: XADD
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ stream:coaching:messages                                    │
│ Message: 1764084200000-0                                    │
└───────────────────────┬───────────────────────────────────┘
                        │
                        │ OUTPUT: XRANGE
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ CONSUMER: API Endpoint / Frontend                           │
│ Reads coaching messages                                     │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Differences: XREAD vs XREADGROUP

### XREAD (Simple Consumer)
```python
# Simple: One consumer reads all messages
messages = redis.xread({'stream:issues': '$'}, count=10)
```
- **Use when:** Single consumer, simple use case
- **No tracking:** Doesn't track which messages were processed
- **No load balancing:** All messages go to one consumer

### XREADGROUP (Consumer Groups)
```python
# Advanced: Multiple consumers share work
messages = redis.xreadgroup(
    'group1',                    # Group name
    'consumer-1',               # Consumer name
    {'stream:issues': '>'},      # Read pending
    count=10
)
```
- **Use when:** Multiple workers, need reliability
- **Tracks processing:** Messages marked as "pending"
- **Load balancing:** Messages distributed across consumers
- **Fault tolerance:** If consumer crashes, messages can be reclaimed

---

## Summary Table

| Operation | Command | Direction | Use Case |
|-----------|---------|-----------|----------|
| **Write** | `XADD` | INPUT | Producer adds message |
| **Read History** | `XRANGE` | OUTPUT | API reading past messages |
| **Read New** | `XREAD` | OUTPUT | Simple consumer waiting for new messages |
| **Read Group** | `XREADGROUP` | OUTPUT | Multiple workers processing messages |
| **Acknowledge** | `XACK` | - | Mark message as processed (consumer groups) |

---

## Real Example: Complete Flow

```javascript
// ============================================
// STEP 1: INPUT - Detect Issue
// ============================================
// Producer: TranscriptMonitor
const issueId = await redis.xadd(
  'stream:contact_center:issues',
  '*',
  'event_id', 'issue_123',
  'issue_type', 'no_empathy',
  'severity', 'medium'
);
// Returns: "1764084108851-0"

// ============================================
// STEP 2: OUTPUT - Read Issue (API)
// ============================================
// Consumer: API Endpoint
const issues = await redis.xrange(
  'stream:contact_center:issues',
  '-',
  '+',
  'COUNT',
  10
);
// Returns: [["1764084108851-0", ["event_id", "issue_123", ...]]]

// ============================================
// STEP 3: INPUT - Route Issue
// ============================================
// Producer: Routing Service
const routeId = await redis.xadd(
  'stream:route.decisions:coaching-manager',
  '*',
  'event_id', 'issue_123',
  'target_stream', 'stream:coaching:messages'
);
// Returns: "1764084181238-0"

// ============================================
// STEP 4: OUTPUT - Consume Route (Worker)
// ============================================
// Consumer: CrewAI Manager (Consumer Group)
const messages = await redis.xreadgroup(
  'coaching',
  'coaching-1',
  {'stream:route.decisions:coaching-manager': '>'},
  count=1,
  block=5000
);
// Returns: [('stream:route.decisions:coaching-manager', [('1764084181238-0', {...})])]

// Process message...
// Then acknowledge:
await redis.xack(
  'stream:route.decisions:coaching-manager',
  'coaching',
  '1764084181238-0'
);

// ============================================
// STEP 5: INPUT - Publish Coaching
// ============================================
// Producer: CrewAI Manager
const coachingId = await redis.xadd(
  'stream:coaching:messages',
  {
    'event_id': 'coaching_456',
    'type': 'coaching.message.created',
    'data': JSON.stringify({...})
  }
);
// Returns: "1764084200000-0"

// ============================================
// STEP 6: OUTPUT - Read Coaching (Frontend)
// ============================================
// Consumer: API / Frontend
const coaching = await redis.xrange(
  'stream:coaching:messages',
  '-',
  '+',
  'COUNT',
  100
);
// Returns: [["1764084200000-0", ["event_id", "coaching_456", ...]]]
```

---

## Important Notes

1. **Message IDs are Timestamps:**
   - Format: `timestamp-sequence` (e.g., `1764084108851-0`)
   - Auto-incrementing, can be used for ordering

2. **Consumer Groups Track Progress:**
   - Each consumer has a "pending" list
   - Messages are acknowledged with `XACK`
   - Failed messages can be reclaimed

3. **Streams are Append-Only:**
   - Messages are never deleted (by default)
   - Use `XTRIM` to limit size if needed
   - Perfect for event logs and audit trails

4. **Blocking Reads:**
   - `XREAD` and `XREADGROUP` can block waiting for new messages
   - Useful for real-time processing
   - Set timeout to avoid infinite blocking

