"""
CrewAI Manager Service
Wraps CrewAI hierarchical crews for the quest-agent-forge infrastructure
Consumes from manager-specific route streams, delegates to crew, publishes results
"""

from __future__ import annotations
import os
import json
import time
import traceback
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
import redis
from crewai import Agent, Task, Crew, Process
from crewai.tools import tool

# Redis connection
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
redis_client = redis.from_url(REDIS_URL, decode_responses=True)


@dataclass
class ManagerConfig:
    """Manager configuration"""
    manager_id: str
    crew_id: str
    route_stream: str
    consumer_group: str = "translator"
    consumer_name: str = "translator-1"
    block_ms: int = 2000
    count: int = 8


class CrewAIManagerService:
    """
    Manages a CrewAI hierarchical crew
    - Reads from dedicated route stream
    - Delegates to crew (manager + workers)
    - Publishes validated results to target streams
    """

    def __init__(
        self,
        config: ManagerConfig,
        manager: Agent,
        crew: Crew,
        heartbeat_interval: int = 30
    ):
        self.config = config
        self.manager = manager
        self.crew = crew
        self.heartbeat_interval = heartbeat_interval
        self.last_heartbeat = 0
        self.running = False
        self.processed_events = set()  # Track processed event_ids to prevent duplicates
        self.max_processed_events = 1000  # Limit size to prevent memory issues

    def start(self) -> None:
        """Start consuming from route stream"""
        print(f"[{self.config.manager_id}] Starting manager service...")
        
        # Register specialist agents if available
        if hasattr(self.config, 'specialists'):
            self._register_specialists()
        
        # Create consumer group
        try:
            redis_client.xgroup_create(
                self.config.route_stream,
                self.config.consumer_group,
                id='$',
                mkstream=True
            )
            print(f"[{self.config.manager_id}] Created consumer group: {self.config.consumer_group}")
        except redis.exceptions.ResponseError as e:
            if 'BUSYGROUP' in str(e):
                print(f"[{self.config.manager_id}] Consumer group already exists")
            else:
                raise

        self.running = True
        print(f"[{self.config.manager_id}] Listening on {self.config.route_stream}...")
        
        # Clean up any pending messages from previous runs (acknowledge them to prevent reprocessing)
        self._cleanup_pending_messages()

        while self.running:
            # Heartbeat
            if time.time() - self.last_heartbeat > self.heartbeat_interval:
                self._send_heartbeat()

            # Read messages (only new messages, not pending ones)
            messages = redis_client.xreadgroup(
                self.config.consumer_group,
                self.config.consumer_name,
                {self.config.route_stream: '>'},
                count=self.config.count,
                block=self.config.block_ms
            )

            print(f"[{self.config.manager_id}] 🧹 Messages: {messages}")
            if not messages:
                continue

            for stream, entries in messages:
                for message_id, fields in entries:
                    # Check if we've already processed this event
                    event_id = fields.get('event_id', message_id)
                    if event_id in self.processed_events:
                        print(f"[{self.config.manager_id}] ⚠️ Skipping duplicate event {event_id} (already processed)")
                        # Acknowledge to prevent reprocessing
                        redis_client.xack(self.config.route_stream, self.config.consumer_group, message_id)
                        continue
                    
                    self._process_route_decision(message_id, fields)

    def stop(self) -> None:
        """Stop the service"""
        self.running = False
        print(f"[{self.config.manager_id}] Stopped")
    
    def _cleanup_pending_messages(self) -> None:
        """Clean up pending messages from previous runs to prevent reprocessing"""
        try:
            # Get pending messages for this consumer
            pending = redis_client.xpending_range(
                self.config.route_stream,
                self.config.consumer_group,
                min='-',
                max='+',
                count=100
            )
            
            if pending:
                print(f"[{self.config.manager_id}] 🧹 Found {len(pending)} pending messages, cleaning up...")
                for msg in pending:
                    # Claim and acknowledge pending messages to prevent reprocessing
                    try:
                        claimed = redis_client.xclaim(
                            self.config.route_stream,
                            self.config.consumer_group,
                            self.config.consumer_name,
                            min_idle_time=0,
                            message_ids=[msg['message_id']]
                        )
                        if claimed:
                            # Acknowledge claimed messages
                            redis_client.xack(
                                self.config.route_stream,
                                self.config.consumer_group,
                                msg['message_id']
                            )
                            print(f"[{self.config.manager_id}] ✅ Cleaned up pending message {msg['message_id']}")
                    except Exception as e:
                        print(f"[{self.config.manager_id}] ⚠️ Could not clean up {msg['message_id']}: {e}")
        except Exception as e:
            print(f"[{self.config.manager_id}] ⚠️ Could not check pending messages: {e}")

    def _process_route_decision(self, message_id: str, fields: Dict[str, str]) -> None:
        """Process a single route decision"""
        start_time = time.time()
        
        try:
            event_id = fields['event_id']
            # When consuming directly from 'stream:contact_center:issues', routing fields may be missing.
            # Provide sensible defaults so the crew can run without the CoachingRouter.
            source_stream = fields.get('source_stream', 'stream:contact_center:issues')
            target_stream = fields.get('target_stream', 'stream:coaching:messages')
            target_schema = fields.get('target_schema', 'CoachingMessageV1')
            confidence = float(fields.get('confidence', '0.0'))

            print(f"[{self.config.manager_id}] Processing {event_id} → {target_stream}")

            # Mark as processing to prevent duplicates
            self.processed_events.add(event_id)
            
            # Clean up old entries if set gets too large
            if len(self.processed_events) > self.max_processed_events:
                # Remove oldest 100 entries (simple cleanup)
                to_remove = list(self.processed_events)[:100]
                for eid in to_remove:
                    self.processed_events.discard(eid)

            # 1. Fetch source event from RedisJSON
            source_event = self._fetch_event(event_id)
            if not source_event:
                # Attempt fallback: build source_event from TranscriptMonitor payload + stream fields
                try:
                    transcript_key = f"transcript:{event_id}"
                    transcript_payload: Optional[Dict[str, Any]] = None
                    try:
                        # Try RedisJSON first
                        transcript_json = redis_client.execute_command('JSON.GET', transcript_key)
                        if transcript_json:
                            transcript_payload = json.loads(transcript_json)
                    except Exception:
                        # Fallback to regular GET
                        try:
                            transcript_json = redis_client.get(transcript_key)
                            if transcript_json:
                                transcript_payload = json.loads(transcript_json)
                        except Exception:
                            transcript_payload = None

                    # Synthesize a minimal CloudEvent-like source_event
                    # Use fields from route decision + transcript payload
                    source_event = {
                        'specversion': '1.0',
                        'id': event_id,
                        'source': fields.get('source_stream', 'stream:contact_center:issues'),
                        'type': fields.get('type', 'contact_center.issue.detected'),
                        'subject': fields.get('subject', f"rep_{fields.get('rep_id', 'unknown')}"),
                        'dataschema': 'ContactCenterIssueV1',
                        'data': {
                            'rep_id': fields.get('rep_id', 'unknown'),
                            'call_id': fields.get('call_id', 'unknown'),
                            'issue_type': fields.get('issue_type', 'unknown'),
                            'severity': fields.get('severity', 'medium'),
                            # Include transcript details if available
                            'detected_at_turn': (transcript_payload or {}).get('detected_at_turn'),
                            'transcript_snippet': (transcript_payload or {}).get('transcript_snippet'),
                            'rep_profile': (transcript_payload or {}).get('rep_profile'),
                            'customer_profile': (transcript_payload or {}).get('customer_profile'),
                        }
                    }
                    print(f"[{self.config.manager_id}] ⚠️ Event {event_id} not found under event:, used transcript fallback")
                except Exception as e:
                    print(f"[{self.config.manager_id}] Event {event_id} not found and transcript fallback failed: {e}")
                    redis_client.xack(self.config.route_stream, self.config.consumer_group, message_id)
                    return


            # 2. Build specialist crew based on issue_type
            issue_type = (source_event.get('data') or {}).get('issue_type') or fields.get('issue_type', 'no_empathy')
            
            if hasattr(self.config, 'specialists'):
                # Import locally to avoid circular dependencies
                import sys
                import os
                sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'crews', 'contact-center'))
                from ContactCenterCoachingCrew import get_specialist_for_issue_type
                from crewai import Crew, Process
                
                coaches = self.config.specialists['coaches']
                tasks = self.config.specialists['tasks']
                specialist_agent, specialist_task = get_specialist_for_issue_type(issue_type, coaches, tasks)
                
                # Build crew with only the relevant specialist
                specialist_crew = Crew(
                    agents=[specialist_agent],
                    tasks=[specialist_task],
                    process=Process.sequential,
                    verbose=True
                )
                
                print(f"[{self.config.manager_id}] Running specialist: {specialist_agent.role} for issue_type: {issue_type}")
                crew_to_run = specialist_crew
            else:
                crew_to_run = self.crew
            
            # 3. Run crew with inputs
            result = crew_to_run.kickoff(inputs={
                'source_event': source_event,
                'target_schema_uri': target_schema,
                'target_stream': target_stream,
                'route_msg_id': message_id,
                'route_stream': self.config.route_stream,
                'actual_issue_type': issue_type
            })

            latency_ms = (time.time() - start_time) * 1000
            print(f"[{self.config.manager_id}] ✅ Crew completed for {event_id} ({latency_ms:.0f}ms)")

            # 3. Extract coaching message from result and publish
            self._publish_coaching_message(result, source_event, target_stream, event_id)

            # 4. Record success metric
            self._record_metric(True, latency_ms, None)

            # 5. Ack the route decision (must be done to prevent reprocessing)
            ack_count = redis_client.xack(self.config.route_stream, self.config.consumer_group, message_id)
            if ack_count > 0:
                print(f"[{self.config.manager_id}] ✅ Acknowledged message {message_id}")
            else:
                print(f"[{self.config.manager_id}] ⚠️ Message {message_id} was already acknowledged")

        except ValueError as e:
            # Validation errors - send to DLQ without retry
            latency_ms = (time.time() - start_time) * 1000
            error_msg = str(e)
            print(f"[{self.config.manager_id}] Validation error for {message_id}: {error_msg}")
            
            self._send_to_dlq(
                message_id, fields, 'validation', error_msg, None, 0, 0
            )
            self._record_metric(False, latency_ms, 'validation')
            redis_client.xack(self.config.route_stream, self.config.consumer_group, message_id)

        except Exception as e:
            # Other errors - send to DLQ with retry
            latency_ms = (time.time() - start_time) * 1000
            error_msg = str(e)
            error_stack = traceback.format_exc() if hasattr(traceback, 'format_exc') else None
            
            print(f"[{self.config.manager_id}] Error processing {message_id}: {error_msg}")
            
            self._send_to_dlq(
                message_id, fields, 'translation', error_msg, error_stack, 0, 3
            )
            self._record_metric(False, latency_ms, 'translation')
            redis_client.xack(self.config.route_stream, self.config.consumer_group, message_id)

    def _publish_coaching_message(
        self,
        crew_result: Any,
        source_event: Dict[str, Any],
        target_stream: str,
        source_event_id: str
    ) -> None:
        """Extract coaching message from crew result and publish as CloudEvent"""
        try:
            import uuid
            from datetime import datetime
            
            # Extract coaching data from crew result
            # Crew result might be a string, dict, or CrewAI result object
            coaching_data = {}
            
            # Handle CrewAI result object (has .raw attribute)
            if hasattr(crew_result, 'raw'):
                crew_result = crew_result.raw
            
            # Handle string results
            if isinstance(crew_result, str):
                # Try to parse JSON from string (might be double-encoded)
                try:
                    # First try direct JSON parse
                    coaching_data = json.loads(crew_result)
                except:
                    try:
                        # If that fails, look for JSON in the string
                        import re
                        json_match = re.search(r'\{.*\}', crew_result, re.DOTALL)
                        if json_match:
                            parsed = json.loads(json_match.group())
                            # If parsed is still a string, parse again
                            if isinstance(parsed, str):
                                coaching_data = json.loads(parsed)
                            else:
                                coaching_data = parsed
                        else:
                            # Fallback: create basic structure from text
                            coaching_data = {
                                'agent_name': 'CoachingCoordinator',
                                'title': 'Coaching guidance',
                                'message': crew_result[:400],
                                'suggested_responses': []
                            }
                    except:
                        coaching_data = {
                            'agent_name': 'CoachingCoordinator',
                            'title': 'Coaching guidance',
                            'message': crew_result[:400],
                            'suggested_responses': []
                        }
            elif isinstance(crew_result, dict):
                coaching_data = crew_result
            else:
                # Convert to string and try to extract
                result_str = str(crew_result)
                try:
                    # Try parsing as JSON first
                    coaching_data = json.loads(result_str)
                except:
                    coaching_data = {
                        'agent_name': 'CoachingCoordinator',
                        'title': 'Coaching guidance',
                        'message': result_str[:400],
                        'suggested_responses': []
                    }
            
            # Get source event data
            source_data = source_event.get('data', {})
            rep_id = source_data.get('rep_id', 'unknown')
            call_id = source_data.get('call_id', 'unknown')
            issue_type = source_data.get('issue_type', 'unknown')
            severity = source_data.get('severity', 'medium')
            detected_at_turn = source_data.get('detected_at_turn', None)  # Include turn index
            
            # Build CloudEvent
            coaching_event = {
                'specversion': '1.0',
                'id': f"coaching_{uuid.uuid4()}",
                'source': 'coaching-crew',
                'type': 'coaching.message.created',
                'subject': f"rep_{rep_id}",
                'dataschema': 'CoachingMessageV1',
                'time': datetime.utcnow().isoformat() + 'Z',
                'data': {
                    '@context': {
                        '@vocab': 'https://schema.org/',
                        'ex': 'https://example.com/ontology#'
                    },
                    'session_id': str(uuid.uuid4()),
                    'call_id': call_id,
                    'rep_id': rep_id,
                    'issue_id': source_event_id,
                    'issue_type': issue_type,  # Include issue type
                    'detected_at_turn': detected_at_turn,  # Include turn index for frontend matching
                    'agent_name': coaching_data.get('agent_name', 'CoachingCoordinator'),
                    'title': coaching_data.get('title', 'Coaching guidance'),
                    'message': coaching_data.get('message', ''),
                    'suggested_responses': coaching_data.get('suggested_responses', []),
                    'micro_exercise': coaching_data.get('micro_exercise', ''),
                    'severity': severity
                }
            }
            
            # Publish to Redis Stream
            message_id = redis_client.xadd(
                target_stream,
                {
                    'event_id': coaching_event['id'],
                    'type': coaching_event['type'],
                    'subject': coaching_event['subject'],
                    'data': json.dumps(coaching_event['data'])
                }
            )
            
            # Also store full event in Redis for later retrieval
            try:
                redis_client.set(f"event:{coaching_event['id']}", json.dumps(coaching_event))
            except:
                pass  # Non-critical
            
            print(f"[{self.config.manager_id}] ✅ Published coaching message {coaching_event['id']} to {target_stream}")
            
        except Exception as e:
            print(f"[{self.config.manager_id}] ⚠️ Error publishing coaching message: {e}")
            # Don't fail the whole process if publishing fails
            import traceback
            traceback.print_exc()

    def _fetch_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Fetch CloudEvent from Redis (tries JSON.GET first, falls back to regular GET)"""
        try:
            # Try JSON.GET first (if Redis JSON module is enabled)
            try:
                event_json = redis_client.execute_command('JSON.GET', f'event:{event_id}')
                if event_json:
                    return json.loads(event_json)
            except (redis.exceptions.ResponseError, redis.exceptions.DataError, Exception) as json_error:
                # JSON.GET not available or failed, try regular GET
                # Check if error is about unknown command
                error_str = str(json_error).lower()
                if 'unknown command' in error_str or 'json.get' in error_str:
                    # Redis JSON module not available, use regular GET
                    try:
                        event_json = redis_client.get(f'event:{event_id}')
                        if event_json:
                            return json.loads(event_json)
                    except Exception as get_error:
                        print(f"[{self.config.manager_id}] Error with regular GET for {event_id}: {get_error}")
                        return None
                else:
                    # Some other error with JSON.GET, try regular GET anyway
                    try:
                        event_json = redis_client.get(f'event:{event_id}')
                        if event_json:
                            return json.loads(event_json)
                    except Exception:
                        pass
            return None
        except Exception as e:
            print(f"[{self.config.manager_id}] Error fetching event {event_id}: {e}")
            return None

    def _register_specialists(self) -> None:
        """Register all specialist agents with heartbeats"""
        if not hasattr(self.config, 'specialists'):
            return
        
        try:
            import requests
            api_url = os.getenv('API_URL', 'http://localhost:3001')
            coaches = self.config.specialists.get('coaches', [])
            
            for coach in coaches:
                # Create agent ID from role
                agent_id = coach.role.lower().replace(' ', '-').replace('&', '').replace('/', '-')
                try:
                    requests.post(
                        f"{api_url}/api/managers/{agent_id}/heartbeat",
                        json={'manager_id': agent_id},
                        timeout=2
                    )
                    print(f"[{self.config.manager_id}] ✅ Registered specialist: {coach.role}")
                except:
                    pass  # Silently ignore registration failures
        except Exception:
            pass  # Non-critical

    def _send_heartbeat(self) -> None:
        """Send heartbeat to registry (non-critical, failures are ignored)"""
        try:
            import requests
            # Try port 3001 first (current server), fallback to 3000
            api_url = os.getenv('API_URL', 'http://localhost:3001')
            
            # Send heartbeat for manager
            try:
                response = requests.post(
                    f"{api_url}/api/managers/{self.config.manager_id}/heartbeat",
                    json={'manager_id': self.config.manager_id},
                    timeout=2
                )
                response.raise_for_status()  # Raise exception for bad status codes
                self.last_heartbeat = time.time()
                print(f"[{self.config.manager_id}] ❤️ Heartbeat")
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                # Try port 3000 as fallback
                api_url_fallback = api_url.replace(':3001', ':3000')
                try:
                    response = requests.post(
                        f"{api_url_fallback}/api/managers/{self.config.manager_id}/heartbeat",
                        json={'manager_id': self.config.manager_id},
                        timeout=2
                    )
                    response.raise_for_status()
                    self.last_heartbeat = time.time()
                    print(f"[{self.config.manager_id}] ❤️ Heartbeat (fallback)")
                except:
                    pass
            except requests.exceptions.RequestException:
                pass
            
            # Also send heartbeats for all specialists
            if hasattr(self.config, 'specialists'):
                coaches = self.config.specialists.get('coaches', [])
                for coach in coaches:
                    agent_id = coach.role.lower().replace(' ', '-').replace('&', '').replace('/', '-')
                    try:
                        requests.post(
                            f"{api_url}/api/managers/{agent_id}/heartbeat",
                            json={'manager_id': agent_id},
                            timeout=2
                        )
                    except:
                        pass  # Silently ignore
        except Exception:
            # Any other exception - silently ignore (heartbeat is non-critical)
            pass

    def _send_to_dlq(
        self,
        message_id: str,
        fields: Dict[str, str],
        error_type: str,
        error_message: str,
        error_stack: Optional[str],
        retry_count: int,
        max_retries: int
    ) -> None:
        """Send failed message to DLQ"""
        try:
            import requests
            api_url = os.getenv('API_URL', 'http://localhost:3000')
            
            requests.post(
                f"{api_url}/api/managers/dlq",
                json={
                    'manager_id': self.config.manager_id,
                    'route_msg_id': message_id,
                    'route_stream': self.config.route_stream,
                    'event_id': fields.get('event_id'),
                    'source_stream': fields.get('source_stream'),
                    'target_stream': fields.get('target_stream'),
                    'target_schema': fields.get('target_schema'),
                    'error_type': error_type,
                    'error_message': error_message,
                    'error_stack': error_stack,
                    'retry_count': retry_count,
                    'max_retries': max_retries,
                    'original_message': fields
                },
                timeout=2
            )
            print(f"[{self.config.manager_id}] 💀 Sent to DLQ: {message_id}")
        except Exception as e:
            print(f"[{self.config.manager_id}] Failed to send to DLQ: {e}")

    def _record_metric(
        self,
        success: bool,
        latency_ms: float,
        error_type: Optional[str]
    ) -> None:
        """Record routing metric"""
        try:
            import requests
            api_url = os.getenv('API_URL', 'http://localhost:3001')
            
            requests.post(
                f"{api_url}/api/managers/metrics",
                json={
                    'manager_id': self.config.manager_id,
                    'success': success,
                    'latency_ms': latency_ms,
                    'error_type': error_type
                },
                timeout=2
            )
        except Exception:
            pass  # Metrics are best-effort


# --- Tools for Manager/Crew ---

@tool("redis_publish")
def redis_publish(stream: str, cloudevent: Dict[str, Any]) -> str:
    """Publish a CloudEvent to a Redis Stream"""
    event_id = cloudevent['id']
    
    # Store full event in RedisJSON
    redis_client.execute_command('JSON.SET', f'event:{event_id}', '$', json.dumps(cloudevent))
    
    # Add pointer to stream
    message_id = redis_client.xadd(stream, {
        'event_id': event_id,
        'type': cloudevent['type'],
        'subject': cloudevent.get('subject', ''),
        'dataschema': cloudevent.get('dataschema', ''),
        'source': cloudevent['source'],
        'time': cloudevent.get('time', '')
    })
    
    print(f"✅ [redis_publish] Published {event_id} to {stream} ({message_id})")
    return message_id


@tool("redis_ack")
def redis_ack(stream: str, group: str, msg_id: str) -> str:
    """Acknowledge a message in a Redis Stream consumer group"""
    redis_client.xack(stream, group, msg_id)
    return "acked"


@tool("fetch_schema")
def fetch_schema(uri: str) -> Dict[str, Any]:
    """Fetch JSON Schema by URI from registry"""
    import requests
    
    api_url = os.getenv('API_URL', 'http://localhost:3000')
    
    try:
        # Call SchemaRegistry API
        response = requests.get(f"{api_url}/api/schemas/by-uri", params={"uri": uri}, timeout=5)
        response.raise_for_status()
        
        result = response.json()
        if result.get('success') and result.get('schema'):
            print(f"✅ [fetch_schema] Retrieved schema: {uri}")
            return result['schema']['schema_definition']
        else:
            print(f"⚠️ [fetch_schema] Schema not found: {uri}")
            return {"type": "object", "properties": {}}
    except Exception as e:
        print(f"❌ [fetch_schema] Error fetching schema {uri}: {e}")
        return {"type": "object", "properties": {}}


@tool("validate_jsonschema")
def validate_jsonschema(uri: str, obj: Dict[str, Any]) -> str:
    """Validate object against JSON Schema"""
    import requests
    
    api_url = os.getenv('API_URL', 'http://localhost:3000')
    
    try:
        # Call SchemaRegistry validation API
        response = requests.post(
            f"{api_url}/api/schemas/validate",
            json={"schema_uri": uri, "payload": obj},
            timeout=5
        )
        response.raise_for_status()
        
        result = response.json()
        if result.get('valid'):
            print(f"✅ [validate_jsonschema] Validation passed for {uri}")
            return "valid"
        else:
            errors = result.get('errors', ['Unknown validation error'])
            error_msg = '; '.join(errors)
            print(f"❌ [validate_jsonschema] Validation failed: {error_msg}")
            raise ValueError(f"Schema validation failed: {error_msg}")
    except requests.exceptions.RequestException as e:
        print(f"❌ [validate_jsonschema] API error: {e}")
        raise ValueError(f"Schema validation API error: {e}")

