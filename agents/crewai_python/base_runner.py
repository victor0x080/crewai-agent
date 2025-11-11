"""Base Agent Runner - Consumes Redis Streams, executes CrewAI agents"""
import logging
import os
import time
import requests
from crewai import Agent, Task, Crew, Process
from tools.redis_streams_tools import consume_stream, ack_message, nack_to_dlq, publish_cloudevent_raw as publish_cloudevent
from tools.rate_limiter import get_rate_limiter

# Configure logging if not already configured
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        force=True
    )

class AgentRunner:
    def __init__(self, agent: Agent, input_stream: str, output_stream: str, group: str, name: str, output_type: str):
        self.agent = agent
        self.input_stream = input_stream
        self.output_stream = output_stream
        self.group = group
        self.name = name
        self.output_type = output_type
        self.logger = logging.getLogger(f"Runner.{group}")
        self.logger.info(f"🎯 Initialized {group} runner (input: {input_stream}, output: {output_stream})")
        self.last_heartbeat = 0
        self.heartbeat_interval = 10  # Send heartbeat every 30 seconds
        self.rate_limiter = get_rate_limiter()
        # Extract agent ID from group (e.g., "sda-semantic-data" -> "sda")
        # or use agent role if available
        if '-' in group:
            self.agent_id = group.split('-')[0]
        else:
            self.agent_id = getattr(agent, 'role', group).lower().replace(' ', '-').replace('&', '').replace('/', '-')
    
    def _send_heartbeat(self):
        """Send heartbeat to Node.js backend"""
        try:
            api_url = os.getenv('API_URL', 'http://localhost:3001')
            requests.post(
                f"{api_url}/api/managers/{self.agent_id}/heartbeat",
                timeout=2
            )
            self.last_heartbeat = time.time()
            self.logger.debug(f"💓 Heartbeat sent for {self.agent_id}")
        except Exception as e:
            self.logger.debug(f"Heartbeat failed: {e}")
    
    def run(self):
        self.logger.info(f"🚀 Starting {self.group} runner")
        self.logger.info(f"   Listening on: {self.input_stream}")
        self.logger.info(f"   Consumer group: {self.group}, name: {self.name}")
        
        while True:
            try:
                # Send heartbeat periodically
                if time.time() - self.last_heartbeat > self.heartbeat_interval:
                    self._send_heartbeat()
                
                msgs = consume_stream(self.input_stream, self.group, self.name, count=10, block=1000)
                if msgs:
                    self.logger.info(f"📨 Received {len(msgs)} message(s) from {self.input_stream}")
                for msg in msgs:
                    self.process(msg)
            except KeyboardInterrupt:
                self.logger.info(f"🛑 Stopping {self.group} runner")
                break
            except Exception as e:
                self.logger.error(f"❌ Error in {self.group} runner: {e}", exc_info=True)
                time.sleep(1)  # Brief pause before retrying
    
    def process(self, msg):
        mid, event = msg['message_id'], msg['event']
        self.logger.info(f"📥 Processing message {mid}")
        
        # Extract task_id IMMEDIATELY at the start to prevent closure/stale variable issues
        task_id = ''
        event_id = event.get('id', 'unknown')
        if isinstance(event.get('data'), dict):
            task_id = event['data'].get('task_id', '')
        if not task_id:
            # Try alternative paths
            if isinstance(event.get('data'), dict):
                task_id = event['data'].get('task_id', '')
            if not task_id:
                self.logger.warning(f"⚠️ No task_id found in event data! Event: {event_id}")
        
        self.logger.info(f"📋 Extracted task_id: {task_id} from event {event_id}")
        
        try:
            # Guard: process only explicit task requests from Node backend
            event_type = event.get('type', '')
            if event_type != 'crewai.task.request':
                # Not our task; acknowledge within this consumer group and skip
                try:
                    ack_message(self.input_stream, self.group, mid)
                except Exception:
                    pass
                return
            # Extract task description from CloudEvent structure
            # CloudEvent format: event['data']['task_description'] or event['data'] (legacy)
            if isinstance(event.get('data'), dict):
                task_description = event['data'].get('task_description', '')
                if not task_description:
                    # Fallback: use the query if available
                    inputs = event['data'].get('inputs', {})
                    if isinstance(inputs, dict):
                        task_description = inputs.get('query', str(event['data']))
                    else:
                        task_description = str(event['data'])
            else:
                # Legacy format: event['data'] is already a string
                task_description = str(event.get('data', ''))
            
            if not task_description:
                task_description = "Process task"
            
            self.logger.info(f"📋 Task description: {task_description[:100]}...")
            # Estimate tokens (approx. 1 token ≈ 4 chars) + response buffer
            estimated_tokens = max(len(task_description) // 4, 0) + 500
            self.logger.info(f"🚦 Checking rate limits (est. {estimated_tokens} tokens)...")
            if not self.rate_limiter.wait_for_slot(estimated_tokens=estimated_tokens, max_wait=120.0):
                self.logger.warning("⏸️ Rate limit wait timed out, will retry later")
                # Publish error response so backend knows what happened
                try:
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
                    self.logger.info(f"✅ Published rate limit timeout response with task_id: {task_id}")
                except Exception as pubError:
                    self.logger.error(f"❌ Failed to publish rate limit timeout response: {pubError}")
                return

            task = Task(description=task_description, expected_output="Result", agent=self.agent)
            crew = Crew(agents=[self.agent], tasks=[task], process=Process.sequential, verbose=False)
            
            self.logger.info(f"🚀 Starting CrewAI execution...")
            start_time = time.time()
            
            # Execute with timeout protection (25 seconds, less than backend's 30s)
            # Also suppress CrewAI's verbose output to prevent log flooding
            import threading
            import io
            import contextlib
            result = None
            exception_holder = [None]
            
            def execute_with_timeout():
                try:
                    # Suppress CrewAI's verbose output
                    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                        result = crew.kickoff()
                        # CrewAI might return a result even on errors - check for error indicators
                        result_str = str(result)
                        # Check if result indicates an error
                        if 'error' in result_str.lower() or 'failed' in result_str.lower() or '429' in result_str or 'quota' in result_str.lower():
                            # This might be an error result, treat it as exception
                            exception_holder[0] = RuntimeError(f"CrewAI returned error result: {result_str[:200]}")
                        else:
                            exception_holder[0] = result
                except Exception as e:
                    # Capture the exception for proper handling
                    exception_holder[0] = e
                except BaseException as e:
                    # Catch all exceptions including system exits
                    exception_holder[0] = e
            
            exec_thread = threading.Thread(target=execute_with_timeout)
            exec_thread.daemon = True
            exec_thread.start()
            exec_thread.join(timeout=90.0)  # Increased to 90 seconds to match backend timeout
            
            if exec_thread.is_alive():
                self.logger.error(f"⏱️ Agent execution timed out after 90 seconds")
                # Release execution lock so others can proceed
                try:
                    self.rate_limiter.release_execution_lock()
                except Exception:
                    pass
                # Still publish a timeout response so backend knows what happened
                # Use task_id extracted at the start of process()
                try:
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
                    self.logger.info(f"✅ Published timeout response with task_id: {task_id}")
                except Exception as pubError:
                    self.logger.error(f"❌ Failed to publish timeout response: {pubError}")
                raise TimeoutError("Agent execution timed out after 90 seconds")
            
            if isinstance(exception_holder[0], Exception):
                # Handle OpenAI API errors gracefully
                error = exception_holder[0]
                error_msg = str(error)
                
                # Check for OpenAI quota/rate limit errors
                if '429' in error_msg or 'quota' in error_msg.lower() or 'insufficient_quota' in error_msg.lower():
                    self.logger.error(f"⚠️ OpenAI API quota exceeded: {error_msg}")
                    # Record cooldown and release lock before publishing
                    try:
                        self.rate_limiter.record_quota_error()
                        self.rate_limiter.release_execution_lock()
                    except Exception:
                        pass
                    # Still publish an error response so backend knows what happened
                    # Use task_id extracted at the start of process()
                    try:
                        publish_cloudevent(
                            self.output_stream,
                            self.output_type,
                            f"urn:agent:{self.group}",
                            {
                                "result": "Error: OpenAI API quota exceeded. Please check your OpenAI billing and plan.",
                                "task_id": task_id,
                                "event_id": event_id,
                                "status": "error",
                                "error": error_msg[:500]  # Limit error message length
                            }
                        )
                        ack_message(self.input_stream, self.group, mid)
                        self.logger.info(f"✅ Published quota error response with task_id: {task_id}")
                        return  # Exit successfully after publishing error response
                    except Exception as pubError:
                        self.logger.error(f"❌ Failed to publish quota error response: {pubError}")
                        # Re-raise original error
                        raise error
                
                # For other exceptions, try to publish error response before re-raising
                try:
                    self.rate_limiter.release_execution_lock()
                except Exception:
                    pass
                # Use task_id extracted at the start of process()
                try:
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
                    self.logger.info(f"✅ Published error response with task_id: {task_id}")
                except Exception as pubError:
                    self.logger.error(f"❌ Failed to publish error response: {pubError}")
                
                # Re-raise other exceptions
                raise error
            
            result = exception_holder[0]
            
            # Check if result indicates an error (CrewAI might return error strings/objects)
            result_str = str(result)
            is_error_result = (
                'error' in result_str.lower() or 
                'failed' in result_str.lower() or 
                '429' in result_str or 
                'quota exceeded' in result_str.lower() or
                'insufficient_quota' in result_str.lower() or
                'LLM Call Failed' in result_str or
                'LLM Failed' in result_str
            )
            
            if is_error_result:
                self.logger.warning(f"⚠️ CrewAI returned error-like result: {result_str[:200]}")
                # Treat as error and publish error response
                try:
                    self.rate_limiter.record_quota_error()
                    self.rate_limiter.release_execution_lock()
                except Exception:
                    pass
                # Use task_id extracted at the start of process()
                try:
                    publish_cloudevent(
                        self.output_stream,
                        self.output_type,
                        f"urn:agent:{self.group}",
                        {
                            "result": f"Error: {result_str[:500]}",
                            "task_id": task_id,
                            "event_id": event_id,
                            "status": "error",
                            "error": result_str[:500]
                        }
                    )
                    ack_message(self.input_stream, self.group, mid)
                    self.logger.info(f"✅ Published error response for error-like result with task_id: {task_id}")
                    return
                except Exception as pubError:
                    self.logger.error(f"❌ Failed to publish error response: {pubError}")
                    raise RuntimeError(f"CrewAI returned error result and failed to publish: {result_str[:200]}")
            
            elapsed = time.time() - start_time
            self.logger.info(f"✅ CrewAI execution completed in {elapsed:.2f}s")
            # Release lock on success
            try:
                self.rate_limiter.release_execution_lock()
            except Exception:
                pass

            self.logger.info(f"📤 Publishing result to {self.output_stream}")
            # Use task_id extracted at the start of process() to ensure it matches the original request
            
            if not task_id:
                self.logger.error(f"❌ Cannot publish response without task_id! Event: {event_id}")
                raise ValueError(f"Missing task_id for event {event_id}")
            
            self.logger.info(f"📋 Publishing response with task_id: {task_id} to {self.output_stream}")
            
            publish_cloudevent(
                self.output_stream, 
                self.output_type, 
                f"urn:agent:{self.group}", 
                {
                    "result": str(result),
                    "task_id": task_id,
                    "event_id": event_id,
                    "status": "success"
                }
            )
            
            self.logger.info(f"✅ Published response with task_id: {task_id}, event_id: {event_id}")
            
        except Exception as e:
            self.logger.error(f"❌ Error processing message {mid}: {e}", exc_info=True)
            # Try to publish error response so backend knows what happened
            try:
                try:
                    self.rate_limiter.release_execution_lock()
                except Exception:
                    pass
                # Use task_id extracted at the start of process()
                publish_cloudevent(
                    self.output_stream,
                    self.output_type,
                    f"urn:agent:{self.group}",
                    {
                        "result": f"Error: {str(e)}",
                        "task_id": task_id,
                        "event_id": event_id,
                        "status": "error",
                        "error": str(e)
                    }
                )
                ack_message(self.input_stream, self.group, mid)
            except Exception as publishError:
                self.logger.error(f"❌ Failed to publish error response: {publishError}")
                nack_to_dlq(self.input_stream, self.group, mid, event_id, str(e))
