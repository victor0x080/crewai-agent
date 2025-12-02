#!/usr/bin/env python3
import sys, json, uuid
from pathlib import Path

# Ensure Python can import the crew module
sys.path.insert(0, str(Path(__file__).parent.parent / 'agents' / 'crewai_python'))

from crews.contact_center.ContactCenterCoachingCrew import build_crew

# Build crew
config, crew = build_crew()

# Construct a sample source_event that should route to Policy & Compliance Coach
issue_id = f"test_issue_{uuid.uuid4().hex[:6]}"
source_event = {
  "specversion": "1.0",
  "id": issue_id,
  "source": "transcript-monitor",
  "type": "contact_center.issue.detected",
  "subject": "rep_45",
  "dataschema": "ContactCenterIssueV1",
  "data": {
    "call_id": "test_call_123",
    "rep_id": "rep_45",
    "issue_type": "missing_verification",
    "severity": "medium",
    "detected_at_turn": 3,
    "rep_profile": {
      "name": "Test Rep",
      "tenure_months": 12,
      "skill_level": "intermediate",
      "vertical_specialty": "hotel",
      "avg_csat": 4.2,
      "compliance_score": 85.0,
      "upsell_rate": 0.15,
      "top_training_needs": ["policy_adherence"]
    },
    "customer_profile": {
      "segment": "business",
      "sentiment_tendency": "impatient"
    },
    "transcript_snippet": [
      {"turn_index": 2, "speaker": "customer", "text": "I need to change my reservation"},
      {"turn_index": 3, "speaker": "rep", "text": "Sure, can you share your booking ref?", "error": "missing_verification"}
    ]
  }
}

inputs = {
  'source_event': source_event,
  'target_schema_uri': 'CoachingMessageV1',
  'target_stream': 'stream:coaching:messages',
  'route_msg_id': 'test_msg_id',
  'route_stream': config.route_stream,
}

print("Running crew for delegation test...\n")
result = crew.kickoff(inputs=inputs)
raw = getattr(result, 'raw', result)
print("Raw result:\n", raw)

text = str(raw)
if "Policy & Compliance Coach" in text:
  print("\n✅ Delegation SUCCESS: Specialist agent executed (Policy & Compliance Coach)")
elif "Real-Time Coaching Coordinator" in text:
  print("\n❌ Delegation FAILED: Manager executed instead of specialist")
else:
  print("\n⚠️  Could not determine agent from output. Preview:")
  print(text[:400])
