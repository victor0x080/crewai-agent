"""
Conversational Agent Runner
===========================

Runs the conversational CrewAI agent with Pinecone memory.
Receives tasks from Node.js backend via Redis Streams following the standard pattern.
"""

import os
import json
import sys
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import requests

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging FIRST (before using logger)
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        force=True
    )

logger = logging.getLogger("Runner.conversational")

# Load environment variables from .env file if it exists
try:
    # Try multiple possible locations for .env file
    possible_env_paths = [
        Path(__file__).parent.parent.parent / '.env',  # From project root
        Path(__file__).parent.parent.parent.parent / '.env',  # Alternative
        Path.cwd() / '.env',  # Current working directory
        Path.home() / '.env',  # Home directory (fallback)
    ]
    
    env_file = None
    for path in possible_env_paths:
        if path.exists():
            env_file = path
            break
    
    if env_file:
        logger.info(f"📋 Loading environment from: {env_file}")
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    value = value.split('#')[0].strip().strip('"').strip("'")
                    if key.strip() not in os.environ:  # Don't override existing env vars
                        os.environ[key.strip()] = value
        logger.info(f"✅ Loaded environment variables from .env")
    else:
        logger.warning("⚠️ No .env file found, using system environment variables only")
except Exception as e:
    logger.warning(f"⚠️ Failed to load .env file: {e}")

from agents.conversational_agent import get_conversational_agent
from tools.redis_streams_tools import consume_stream, ack_message, nack_to_dlq, publish_cloudevent_raw as publish_cloudevent
from tools.pinecone_tools import save_conversation_context
from base_runner import AgentRunner


class ConversationalRunner(AgentRunner):
    """Runner for conversational CrewAI agent with Pinecone memory."""
    
    def __init__(self):
        # Initialize with standard AgentRunner pattern
        # Create a dummy agent object for base class compatibility
        class DummyAgent:
            role = "Conversational AI Assistant"
        dummy_agent = DummyAgent()
        super().__init__(
            agent=dummy_agent,  # Dummy agent for base class compatibility
            input_stream="stream:agent:conversational:in",
            output_stream="stream:agent:conversational:out",
            group="conversational",
            name="worker-1",
            output_type="conversation_response"
        )
        # Set the actual agent AFTER super().__init__() to avoid overwriting
        self.agent = get_conversational_agent()
    
    def process(self, msg):
        """
        Override base process method to handle conversational tasks.
        Extracts conversation context and enhances task with Pinecone memory instructions.
        """
        mid, event = msg['message_id'], msg['event']
        self.logger.info(f"📥 Processing conversational message {mid}")
        
        # Extract task_id (required for response)
        task_id = ''
        event_id = event.get('id', 'unknown')
        if isinstance(event.get('data'), dict):
            task_id = event['data'].get('task_id', '')
        
        if not task_id:
            self.logger.warning(f"⚠️ No task_id found in event data! Event: {event_id}")
            ack_message(self.input_stream, self.group, mid)
            return
        
        # Guard: process only explicit task requests
        event_type = event.get('type', '')
        if event_type != 'crewai.task.request':
            ack_message(self.input_stream, self.group, mid)
            return
        
        try:
            # Extract task description and inputs from CloudEvent
            inputs = {}
            task_description = ''
            if isinstance(event.get('data'), dict):
                task_description = event['data'].get('task_description', '')
                inputs = event['data'].get('inputs', {})
                if not task_description:
                    if isinstance(inputs, dict):
                        task_description = inputs.get('query', inputs.get('message', str(event['data'])))
                    else:
                        task_description = str(event['data'])
            else:
                task_description = str(event.get('data', ''))
            
            if not task_description:
                task_description = "Process conversation"
            
            # Extract conversation context from inputs
            conversation_id = inputs.get('conversation_id', f"conv_{int(time.time())}")
            user_query = inputs.get('query') or inputs.get('message') or task_description
            context = inputs.get('context', {})
            conversation_history = inputs.get('conversation_history', [])  # Pre-retrieved from MemoryService
            
            # Extract problem-first context
            problem_type = context.get('problem_type', 'general')
            problem_space = context.get('problem_space', '')
            workflow_stage = context.get('workflow_stage', 'interpret')
            problem_classification = context.get('problem_classification', {})
            datasource = context.get('datasource', None)
            
            self.logger.info(f"💬 Conversation ID: {conversation_id}, Query: {user_query[:50]}...")
            self.logger.info(f"🎯 Problem Type: {problem_type}, Workflow Stage: {workflow_stage}, Problem Space: {problem_space[:50] if problem_space else 'Not defined'}...")
            self.logger.info(f"📊 Datasource Available: {'Yes' if datasource else 'No'}")
            self.logger.info(f"📚 Conversation history: {len(conversation_history)} messages pre-loaded from MemoryService")
            
            # Note: Conversation history is pre-retrieved by MemoryService.js and passed here
            # No need for agent to call retrieve_conversation_history tool
            
            # Rate limiting check
            estimated_tokens = max(len(user_query) // 4, 0) + 1000  # Estimate tokens for function calling
            if not self.rate_limiter.wait_for_slot(estimated_tokens=estimated_tokens, max_wait=120.0):
                self.logger.warning("⏸️ Rate limit wait timed out")
                publish_cloudevent(
                    self.output_stream,
                    self.output_type,
                    f"urn:agent:{self.group}",
                    {
                        "result": "Error: Rate limit wait timed out after 120 seconds",
                        "task_id": task_id,
                        "event_id": event_id,
                        "status": "error",
                        "error": "Rate limit wait timed out"
                    }
                )
                ack_message(self.input_stream, self.group, mid)
                return
            
            # Conversation history is pre-loaded from MemoryService (handles Pinecone retrieval)
            # No need for agent to call retrieve_conversation_history tool
            
            self.logger.info(f"🚀 Starting OpenAI function calling conversational execution...")
            start_time = time.time()
            
            # Execute with timeout protection
            import threading
            exception_holder = [None]
            
            def execute_with_timeout():
                try:
                    # Build enhanced context with problem-first information
                    enhanced_context = {
                        **context,
                        'problem_type': problem_type,
                        'problem_space': problem_space,
                        'workflow_stage': workflow_stage,
                        'problem_classification': problem_classification,
                        'datasource': datasource  # Include datasource from datacube
                    }
                    
                    result = self.agent.generate_response(
                        user_query=user_query,
                        conversation_id=conversation_id,
                        conversation_history=conversation_history,  # Use pre-retrieved history from MemoryService
                        context=enhanced_context
                    )
                    exception_holder[0] = result
                except Exception as e:
                    exception_holder[0] = e
            
            exec_thread = threading.Thread(target=execute_with_timeout)
            exec_thread.daemon = True
            exec_thread.start()
            exec_thread.join(timeout=90.0)
            
            if exec_thread.is_alive():
                self.logger.error(f"⏱️ Agent execution timed out after 90 seconds")
                self.rate_limiter.release_execution_lock()
                publish_cloudevent(
                    self.output_stream,
                    self.output_type,
                    f"urn:agent:{self.group}",
                    {
                        "result": "Error: Agent execution timed out after 90 seconds",
                        "task_id": task_id,
                        "event_id": event_id,
                        "status": "error",
                        "error": "Timeout after 90 seconds"
                    }
                )
                ack_message(self.input_stream, self.group, mid)
                return
            
            # Handle result
            if isinstance(exception_holder[0], Exception):
                error = exception_holder[0]
                error_msg = str(error)
                self.logger.error(f"❌ Execution error: {error_msg}")
                self.rate_limiter.release_execution_lock()
                publish_cloudevent(
                    self.output_stream,
                    self.output_type,
                    f"urn:agent:{self.group}",
                    {
                        "result": f"Error: {error_msg[:500]}",
                        "task_id": task_id,
                        "event_id": event_id,
                        "status": "error",
                        "error": error_msg[:500]
                    }
                )
                ack_message(self.input_stream, self.group, mid)
                return
            
            # Success - extract result from function calling response
            agent_result = exception_holder[0]
            elapsed = time.time() - start_time
            self.logger.info(f"✅ Execution completed in {elapsed:.2f}s")
            
            # Extract response and function calls
            result = agent_result.get('response', '')
            function_calls = agent_result.get('function_calls', [])
            metadata = agent_result.get('metadata', {})
            
            # Log function calls if any
            if function_calls:
                self.logger.info(f"🔧 Executed {len(function_calls)} function calls:")
                for fc in function_calls:
                    self.logger.debug(f"  - {fc.get('name')}: {fc.get('arguments')}")
            
            # Final cleanup: ensure result is not empty
            if not result or len(result.strip()) == 0:
                result = "I apologize, but I could not generate a response."
            
            result = result.strip()
            self.logger.info(f"📝 Response length: {len(result)} chars")
            if len(result) > 200:
                self.logger.debug(f"📝 Response preview: {result[:200]}...")
            else:
                self.logger.debug(f"📝 Full response: {result}")
            
            # Note: Conversation history is pre-loaded from MemoryService.js (handles Pinecone retrieval)
            # All memory operations are handled server-side by MemoryService.js
            history_length = len(conversation_history) if conversation_history else 0
            
            # Publish success response (no function calls - all operations handled by MemoryService.js)
            publish_cloudevent(
                self.output_stream,
                self.output_type,
                f"urn:agent:{self.group}",
                {
                    "result": result,
                    "task_id": task_id,
                    "event_id": event_id,
                    "status": "success",
                    "conversation_id": conversation_id,
                    "processing_time": elapsed,
                    "history_length": history_length,  # Actual conversation history length from MemoryService
                    "function_calls": function_calls,  # Empty - no function calling needed
                    "metadata": {
                        **(metadata if metadata else {}),
                        "problem_type": problem_type,
                        "workflow_stage": workflow_stage,
                        "problem_space": problem_space
                    }  # Include metadata about the execution and problem context
                }
            )
            
            # Release rate limiter
            try:
                self.rate_limiter.release_execution_lock()
            except Exception:
                pass
            
            ack_message(self.input_stream, self.group, mid)
            self.logger.info(f"✅ Published response with task_id: {task_id}")
            
        except Exception as e:
            self.logger.error(f"❌ Error processing conversational task: {e}", exc_info=True)
            try:
                publish_cloudevent(
                    self.output_stream,
                    self.output_type,
                    f"urn:agent:{self.group}",
                    {
                        "result": f"Error processing conversation: {str(e)}",
                        "task_id": task_id,
                        "event_id": event_id,
                        "status": "error",
                        "error": str(e)
                    }
                )
                ack_message(self.input_stream, self.group, mid)
            except Exception as pubError:
                self.logger.error(f"❌ Failed to publish error response: {pubError}")


def main():
    """Main entry point for conversational agent runner."""
    runner = ConversationalRunner()
    runner.run()  # Use base class run() method which handles Redis Streams


if __name__ == "__main__":
    main()

