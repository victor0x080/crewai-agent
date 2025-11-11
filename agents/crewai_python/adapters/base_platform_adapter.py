"""
Base Platform Adapter - Python Translation from TypeScript
Abstract base for platform-specific adapters (SA360, DV360, Amazon, TikTok)
Follows CrewAI + Redis Streams + CloudEvents pattern
"""
import asyncio
import time
import uuid
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, Any, Set, Optional
import sys
sys.path.append('..')
from tools.redis_streams_tools import RedisStreamsClient, publish_cloudevent, fetch_cloudevent

logger = logging.getLogger(__name__)


class ActionOutcome:
    """Action outcome structure"""
    def __init__(
        self,
        action_id: str,
        status: str,  # 'success', 'failure', 'partial'
        platform_id: Optional[str] = None,
        error_message: Optional[str] = None,
        retry_count: int = 0,
        api_latency_ms: Optional[int] = None
    ):
        self.action_id = action_id
        self.status = status
        self.platform_id = platform_id
        self.error_message = error_message
        self.retry_count = retry_count
        self.api_latency_ms = api_latency_ms

    def to_dict(self) -> Dict[str, Any]:
        return {
            'action_id': self.action_id,
            'status': self.status,
            'platform_id': self.platform_id,
            'error_message': self.error_message,
            'retry_count': self.retry_count,
            'api_latency_ms': self.api_latency_ms
        }


class BasePlatformAdapter(ABC):
    """
    Base Platform Adapter
    Consumes stream:mco:event:action, publishes stream:mco:event:outcome
    Implements idempotency, rate limiting, retry logic, anomaly publishing
    """
    
    def __init__(
        self,
        platform_name: str,
        input_stream: str = 'stream:mco:event:action',
        output_stream: str = 'stream:mco:event:outcome',
        consumer_group: Optional[str] = None,
        rate_limit_per_hour: int = 1000
    ):
        self.platform_name = platform_name
        self.input_stream = input_stream
        self.output_stream = output_stream
        self.consumer_group = consumer_group or f'adapter-{platform_name}'
        
        # Rate limiting
        self.rate_limit_per_hour = rate_limit_per_hour
        self.rate_limit_remaining = rate_limit_per_hour
        self.rate_limit_reset = datetime.now() + timedelta(hours=1)
        
        # Idempotency tracking
        self.processed_actions: Set[str] = set()
        
        # Redis client
        self.redis_client = RedisStreamsClient().get_client()
        
        # Running flag
        self.running = False
        
        logger.info(f"{platform_name} Platform Adapter initialized")

    async def start(self):
        """Start consuming from input stream"""
        self.running = True
        logger.info(f"{self.platform_name} Platform Adapter started")
        
        # Create consumer group if not exists
        try:
            self.redis_client.xgroup_create(
                self.input_stream,
                self.consumer_group,
                id='$',
                mkstream=True
            )
            logger.info(f"Created consumer group: {self.consumer_group}")
        except Exception as e:
            if 'BUSYGROUP' not in str(e):
                logger.error(f"Error creating consumer group: {e}")
        
        # Start consuming
        await self._consume_loop()

    async def _consume_loop(self):
        """Main consumption loop with XREADGROUP"""
        consumer_name = f"{self.platform_name}-{uuid.uuid4().hex[:8]}"
        
        while self.running:
            try:
                # XREADGROUP with blocking
                messages = self.redis_client.xreadgroup(
                    self.consumer_group,
                    consumer_name,
                    {self.input_stream: '>'},
                    count=10,
                    block=1000  # 1 second block
                )
                
                if not messages:
                    continue
                
                for stream, entries in messages:
                    for message_id, fields in entries:
                        await self._handle_message(
                            message_id.decode() if isinstance(message_id, bytes) else message_id,
                            fields
                        )
                        
            except Exception as e:
                logger.error(f"Error in consume loop: {e}")
                await asyncio.sleep(1)

    async def _handle_message(self, message_id: str, fields: Dict):
        """Handle individual message"""
        try:
            # Decode fields
            decoded_fields = {
                k.decode() if isinstance(k, bytes) else k: 
                v.decode() if isinstance(v, bytes) else v
                for k, v in fields.items()
            }
            
            event_id = decoded_fields.get('event_id')
            if not event_id:
                logger.error(f"No event_id in message {message_id}")
                self.redis_client.xack(self.input_stream, self.consumer_group, message_id)
                return
            
            # Fetch full CloudEvent from RedisJSON
            event = self.redis_client.json().get(f"event:{event_id}")
            if not event:
                logger.error(f"Event {event_id} not found in RedisJSON")
                self.redis_client.xack(self.input_stream, self.consumer_group, message_id)
                return
            
            action = event.get('data', {})
            action_id = action.get('target', {}).get('entityId', event_id)
            
            # Idempotency check
            if action_id in self.processed_actions:
                logger.info(f"Action {action_id} already processed (idempotent)")
                self.redis_client.xack(self.input_stream, self.consumer_group, message_id)
                return
            
            # Rate limit check
            await self._check_rate_limit()
            
            # Execute platform-specific action
            outcome = await self.execute_action(action)
            
            # Mark as processed
            self.processed_actions.add(action_id)
            
            # Publish outcome
            await self._publish_outcome(outcome)
            
            # If failure, publish anomaly
            if outcome.status == 'failure':
                await self._publish_anomaly(action, outcome)
            
            # ACK message
            self.redis_client.xack(self.input_stream, self.consumer_group, message_id)
            
            logger.info(f"Processed action {action_id}: {outcome.status}")
            
        except Exception as e:
            logger.error(f"Error handling message {message_id}: {e}")
            # Don't ACK on error - message will be retried

    async def _check_rate_limit(self):
        """Check and enforce rate limiting"""
        now = datetime.now()
        
        # Reset if window expired
        if now > self.rate_limit_reset:
            self.rate_limit_remaining = self.rate_limit_per_hour
            self.rate_limit_reset = now + timedelta(hours=1)
        
        # Wait if rate limit exceeded
        if self.rate_limit_remaining <= 0:
            wait_seconds = (self.rate_limit_reset - now).total_seconds()
            logger.warning(f"Rate limit exceeded, waiting {wait_seconds:.1f}s")
            await asyncio.sleep(wait_seconds)
            self.rate_limit_remaining = self.rate_limit_per_hour
            self.rate_limit_reset = datetime.now() + timedelta(hours=1)
        
        self.rate_limit_remaining -= 1

    @abstractmethod
    async def execute_action(self, action: Dict[str, Any]) -> ActionOutcome:
        """
        Execute platform-specific action
        Must be implemented by subclasses
        
        Args:
            action: Action payload from CloudEvent data
            
        Returns:
            ActionOutcome with status, platform_id, errors
        """
        pass

    async def retry_action(
        self,
        action: Dict[str, Any],
        max_retries: int = 3
    ) -> ActionOutcome:
        """
        Retry logic with exponential backoff
        
        Args:
            action: Action payload
            max_retries: Maximum retry attempts
            
        Returns:
            ActionOutcome
        """
        retry_count = 0
        last_error = None
        
        while retry_count < max_retries:
            try:
                outcome = await self.execute_action(action)
                if outcome.status == 'success':
                    outcome.retry_count = retry_count
                    return outcome
                last_error = outcome.error_message
            except Exception as e:
                last_error = str(e)
            
            retry_count += 1
            backoff_seconds = 2 ** retry_count  # Exponential backoff
            logger.warning(f"Retry {retry_count}/{max_retries} after {backoff_seconds}s")
            await asyncio.sleep(backoff_seconds)
        
        # Max retries exceeded
        action_id = action.get('target', {}).get('entityId', 'unknown')
        return ActionOutcome(
            action_id=action_id,
            status='failure',
            error_message=last_error or 'Max retries exceeded',
            retry_count=retry_count
        )

    async def _publish_outcome(self, outcome: ActionOutcome):
        """Publish outcome to stream:mco:event:outcome"""
        outcome_id = str(uuid.uuid4())
        
        # Build CloudEvent
        cloudevent = {
            'specversion': '1.0',
            'id': outcome_id,
            'source': f'urn:adapter:{self.platform_name}',
            'type': 'mco.event.outcome',
            'subject': outcome.action_id,
            'time': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
            'dataschema': 'https://schemas.mesh/adapters/OutcomeContract.json',
            'data': {
                '@context': {'mco': 'https://mesh.example.com/ontology#'},
                'outcome_id': outcome_id,
                'action_id': outcome.action_id,
                'platform': self.platform_name,
                'status': outcome.status,
                'platform_id': outcome.platform_id,
                'error_message': outcome.error_message,
                'retry_count': outcome.retry_count,
                'api_latency_ms': outcome.api_latency_ms,
                'timestamp': datetime.utcnow().isoformat()
            }
        }
        
        # Store in RedisJSON
        self.redis_client.json().set(f"event:{outcome_id}", '$', cloudevent)
        
        # Add pointer to stream
        self.redis_client.xadd(self.output_stream, {
            'event_id': outcome_id,
            'type': 'mco.event.outcome',
            'subject': outcome.action_id,
            'dataschema': cloudevent['dataschema']
        })
        
        logger.info(f"Published outcome {outcome_id} for action {outcome.action_id}")

    async def _publish_anomaly(self, action: Dict[str, Any], outcome: ActionOutcome):
        """Publish anomaly to stream:mco:event:anomaly"""
        anomaly_id = str(uuid.uuid4())
        
        cloudevent = {
            'specversion': '1.0',
            'id': anomaly_id,
            'source': f'urn:adapter:{self.platform_name}',
            'type': 'mco.event.anomaly',
            'subject': outcome.action_id,
            'time': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
            'dataschema': 'https://schemas.mesh/EventPayload.json#/$defs/Anomaly',
            'data': {
                '@context': {'mco': 'https://mesh.example.com/ontology#'},
                'anomaly_id': anomaly_id,
                'type': 'platform_api_failure',
                'severity': 'high',
                'provider': self.platform_name,
                'errors': [outcome.error_message or 'Unknown error'],
                'data_sample': action,
                'timestamp': datetime.utcnow().isoformat()
            }
        }
        
        # Store in RedisJSON
        self.redis_client.json().set(f"event:{anomaly_id}", '$', cloudevent)
        
        # Add pointer to stream
        self.redis_client.xadd('stream:mco:event:anomaly', {
            'event_id': anomaly_id,
            'type': 'mco.event.anomaly',
            'subject': outcome.action_id,
            'dataschema': cloudevent['dataschema']
        })
        
        logger.warning(f"Published anomaly {anomaly_id} for action {outcome.action_id}")

    async def stop(self):
        """Stop the adapter"""
        self.running = False
        logger.info(f"{self.platform_name} Platform Adapter stopped")
