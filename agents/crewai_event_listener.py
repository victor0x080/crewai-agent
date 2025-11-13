"""
CrewAI Event Listener with Semantic Filtering
Captures CrewAI events, filters via semantic policies, publishes to Redis Streams.
"""

import redis
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
import threading
import queue
from openai import OpenAI

# CrewAI event imports
try:
    from crewai.events import (
        BaseEventListener,
        CrewAIEventsBus,
        AgentExecutionCompletedEvent,
        TaskCompletedEvent,
        ToolUsageFinishedEvent,
        CrewCompletedEvent,
        CrewStartedEvent,
    )
    CREWAI_AVAILABLE = True
except ImportError:
    print("[CrewAIEventListener] Warning: CrewAI events not available, using mock")
    CREWAI_AVAILABLE = False
    BaseEventListener = object
    CrewAIEventsBus = None

from semantic_policy_engine import (
    SemanticPolicyEngine,
    OpenAIEmbedder,
    LLMJudge
)

# Redis connection
redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

# OpenAI client for embeddings and LLM judge
openai_client = OpenAI()

class BusPublisher:
    """
    Non-blocking publisher for Redis Streams.
    Uses a background thread to avoid blocking CrewAI event handlers.
    """
    
    def __init__(self):
        self.queue = queue.Queue(maxsize=1000)
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()
        print("[BusPublisher] Started background publisher thread")
    
    def enqueue(self, topic: str, body: Dict[str, Any], meta: Dict[str, Any] = None):
        """Enqueue message for publishing"""
        try:
            self.queue.put_nowait({
                "topic": topic,
                "body": body,
                "meta": meta or {}
            })
        except queue.Full:
            print(f"[BusPublisher] Queue full, dropping message to {topic}")
    
    def _worker(self):
        """Background worker that publishes to Redis"""
        while True:
            try:
                msg = self.queue.get()
                self._publish(msg["topic"], msg["body"], msg["meta"])
                self.queue.task_done()
            except Exception as e:
                print(f"[BusPublisher] Error in worker: {e}")
    
    def _publish(self, topic: str, body: Dict[str, Any], meta: Dict[str, Any]):
        """Publish message to Redis Stream"""
        try:
            # Build CloudEvent
            event_id = str(uuid.uuid4())
            cloudevent = {
                "specversion": "1.0",
                "id": event_id,
                "source": "urn:crewai:event-listener",
                "type": f"com.acme.crewai.{body.get('type', 'unknown')}",
                "subject": body.get('agent', {}).get('name', 'unknown'),
                "time": datetime.utcnow().isoformat() + "Z",
                "datacontenttype": "application/json",
                "dataschema": "https://schemas.acme.com/crewai/event/1-0-0.json",
                "data": {
                    "@context": {
                        "@vocab": "https://vocab.acme.com/",
                        "crewai": "https://vocab.acme.com/crewai/"
                    },
                    **body
                },
                "meta": meta
            }
            
            # Store full event in RedisJSON
            redis_client.json().set(f"event:{event_id}", "$", cloudevent)
            
            # Add pointer to stream
            redis_client.xadd(topic, {
                "event_id": event_id,
                "type": cloudevent["type"],
                "subject": cloudevent["subject"],
                "dataschema": cloudevent["dataschema"],
                "policy": meta.get("policy", "unknown"),
                "similarity": meta.get("similarity", 0.0)
            })
            
            print(f"[BusPublisher] Published {cloudevent['type']} to {topic}")
            
        except Exception as e:
            print(f"[BusPublisher] Error publishing to {topic}: {e}")

class SemanticBusListener(BaseEventListener if CREWAI_AVAILABLE else object):
    """
    CrewAI event listener with semantic filtering.
    
    Listens to CrewAI events, normalizes them, runs through semantic policy engine,
    and publishes filtered events to Redis Streams.
    """
    
    def __init__(self, policies_path: str):
        if CREWAI_AVAILABLE:
            super().__init__()
        
        # Initialize components
        self.embedder = OpenAIEmbedder(openai_client)
        self.judge = LLMJudge(openai_client)
        self.policy_engine = SemanticPolicyEngine.from_yaml(
            policies_path,
            self.embedder,
            self.judge
        )
        self.publisher = BusPublisher()
        
        print("[SemanticBusListener] Initialized")
    
    def setup_listeners(self, bus: 'CrewAIEventsBus'):
        """
        Register event handlers with CrewAI event bus.
        Keep handlers light and non-blocking.
        """
        
        @bus.on(CrewStartedEvent)
        def on_crew_started(source, event):
            payload = normalize_crew_event("crew_started", source, event)
            self._try_publish(payload)
        
        @bus.on(CrewCompletedEvent)
        def on_crew_completed(source, event):
            payload = normalize_crew_event("crew_completed", source, event)
            self._try_publish(payload)
        
        @bus.on(AgentExecutionCompletedEvent)
        def on_agent_done(source, event):
            payload = normalize_agent_event("agent_execution_completed", source, event)
            self._try_publish(payload)
        
        @bus.on(TaskCompletedEvent)
        def on_task_done(source, event):
            payload = normalize_task_event("task_completed", source, event)
            self._try_publish(payload)
        
        @bus.on(ToolUsageFinishedEvent)
        def on_tool_done(source, event):
            payload = normalize_tool_event("tool_usage_finished", source, event)
            self._try_publish(payload)
        
        print("[SemanticBusListener] Event handlers registered")
    
    def _try_publish(self, payload: Dict[str, Any]):
        """
        Filter payload through policy engine and publish if it passes.
        Non-blocking: queues for background thread.
        """
        try:
            decision = self.policy_engine.should_broadcast(payload)
            
            if decision:
                # Publish to each topic
                for topic in decision["topics"]:
                    self.publisher.enqueue(
                        topic=topic,
                        body=decision["body"],
                        meta=decision["meta"]
                    )
        except Exception as e:
            print(f"[SemanticBusListener] Error in _try_publish: {e}")

# Event normalization functions
def normalize_crew_event(event_type: str, source: Any, event: Any) -> Dict[str, Any]:
    """Normalize CrewCompletedEvent / CrewStartedEvent"""
    return {
        "type": event_type,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "crew_run_id": getattr(event, "crew_run_id", "unknown"),
        "crew_name": str(source),
        "metadata": {
            "duration_ms": getattr(event, "duration_ms", 0),
            "agents_count": getattr(event, "agents_count", 0)
        }
    }

def normalize_agent_event(event_type: str, source: Any, event: Any) -> Dict[str, Any]:
    """Normalize AgentExecutionCompletedEvent"""
    agent = getattr(event, "agent", None) or source
    
    return {
        "type": event_type,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "crew_run_id": getattr(event, "crew_run_id", "unknown"),
        "agent": {
            "name": getattr(agent, "role", str(agent)),
            "role": getattr(agent, "role", ""),
            "goal": getattr(agent, "goal", "")
        },
        "output": str(getattr(event, "output", "")),
        "success": not getattr(event, "error", None),
        "metadata": {
            "tokens": getattr(event, "tokens", 0),
            "cost": getattr(event, "cost", 0.0),
            "execution_time": getattr(event, "execution_time", 0),
            "error": str(getattr(event, "error", "")) if getattr(event, "error", None) else None,
            "error_type": type(getattr(event, "error", None)).__name__ if getattr(event, "error", None) else None
        }
    }

def normalize_task_event(event_type: str, source: Any, event: Any) -> Dict[str, Any]:
    """Normalize TaskCompletedEvent"""
    task = getattr(event, "task", None) or source
    agent = getattr(event, "agent", None)
    
    return {
        "type": event_type,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "crew_run_id": getattr(event, "crew_run_id", "unknown"),
        "task": {
            "id": str(id(task)),
            "name": getattr(task, "description", str(task))[:100],
            "description": getattr(task, "description", "")
        },
        "agent": {
            "name": getattr(agent, "role", str(agent)) if agent else "unknown",
            "role": getattr(agent, "role", "") if agent else ""
        },
        "output": str(getattr(event, "output", "")),
        "success": not getattr(event, "error", None),
        "metadata": {
            "tokens": getattr(event, "tokens", 0),
            "execution_time": getattr(event, "execution_time", 0),
            "error": str(getattr(event, "error", "")) if getattr(event, "error", None) else None,
            "reasoning_summary": getattr(event, "reasoning_summary", "")
        }
    }

def normalize_tool_event(event_type: str, source: Any, event: Any) -> Dict[str, Any]:
    """Normalize ToolUsageFinishedEvent"""
    tool = getattr(event, "tool", None) or source
    
    return {
        "type": event_type,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "crew_run_id": getattr(event, "crew_run_id", "unknown"),
        "tool": {
            "name": getattr(tool, "name", str(tool)),
            "description": getattr(tool, "description", "")
        },
        "agent": {
            "name": getattr(event, "agent_name", "unknown")
        },
        "inputs": getattr(event, "inputs", {}),
        "success": not getattr(event, "error", None),
        "metadata": {
            "execution_time": getattr(event, "execution_time", 0),
            "error": str(getattr(event, "error", "")) if getattr(event, "error", None) else None,
            "tool_result_summary": str(getattr(event, "result", ""))[:200] if getattr(event, "result", None) else ""
        }
    }

# Standalone test mode
if __name__ == "__main__":
    import sys
    
    if not CREWAI_AVAILABLE:
        print("CrewAI not installed. Install with: pip install crewai crewai-tools")
        sys.exit(1)
    
    # Test with a mock event
    listener = SemanticBusListener("crewai_policies.yaml")
    
    # Create mock event
    mock_event = {
        "type": "agent_execution_completed",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "crew_run_id": "test-123",
        "agent": {
            "name": "Strategic Plan Analyst",
            "role": "Strategic Plan Analyst",
            "goal": "Analyze strategic plan for Q4 revenue"
        },
        "output": "Q4 revenue target is $45M with 18% growth. Key initiatives include holiday campaign and product expansion.",
        "success": True,
        "metadata": {
            "tokens": 150,
            "cost": 0.002,
            "execution_time": 2500
        }
    }
    
    print("\n" + "="*80)
    print("TESTING SEMANTIC POLICY ENGINE")
    print("="*80 + "\n")
    
    # Test policy engine
    decision = listener.policy_engine.should_broadcast(mock_event)
    
    if decision:
        print(f"\n✅ Event PASSED filtering")
        print(f"   Topics: {decision['topics']}")
        print(f"   Policy: {decision['meta']['policy']}")
        print(f"   Similarity: {decision['meta']['similarity']}")
        
        # Test publishing
        for topic in decision["topics"]:
            listener.publisher.enqueue(topic, decision["body"], decision["meta"])
        
        # Wait for background thread
        import time
        time.sleep(2)
    else:
        print(f"\n❌ Event REJECTED by policy engine")
    
    print("\n" + "="*80)
