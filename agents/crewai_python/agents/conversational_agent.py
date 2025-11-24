"""
Conversational CrewAI Agent with Pinecone Memory and OpenAI Function Calling
============================================================================

A conversational AI agent that uses Pinecone for persistent memory.
Uses OpenAI function calling for structured responses (Cursor/Windsurf style).
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from openai import OpenAI

sys.path.insert(0, str(Path(__file__).parent.parent))
from tools.pinecone_tools import (
    retrieve_conversation_history,
    store_conversation_context,
    search_agent_knowledge,
    get_conversation_history,
    save_conversation_context
)


class ConversationalAgentWithFunctionCalling:
    """
    Conversational agent that uses OpenAI function calling for structured responses.
    Returns responses in Cursor/Windsurf style with function calls.
    """
    
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4-turbo-preview')
        
        # Define available functions for OpenAI function calling
        self.functions = [
            {
                "type": "function",
                "function": {
                    "name": "retrieve_conversation_history",
                    "description": "Retrieve conversation history from Pinecone for context. Use this to remember previous messages in the conversation.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "conversation_id": {
                                "type": "string",
                                "description": "Unique conversation identifier"
                            },
                            "query": {
                                "type": "string",
                                "description": "Optional query to find relevant messages (if None, returns all for conversation)"
                            },
                            "top_k": {
                                "type": "integer",
                                "description": "Number of results to return (default: 10)",
                                "default": 10
                            }
                        },
                        "required": ["conversation_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "store_conversation_context",
                    "description": "Store conversation context in Pinecone for memory across agent runs. Use this to save the current conversation turn.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "conversation_id": {
                                "type": "string",
                                "description": "Unique conversation identifier"
                            },
                            "agent_id": {
                                "type": "string",
                                "description": "Identifier of the agent (e.g., 'conversational_agent')"
                            },
                            "user_query": {
                                "type": "string",
                                "description": "User's query/question"
                            },
                            "agent_response": {
                                "type": "string",
                                "description": "Agent's response"
                            },
                            "context": {
                                "type": "object",
                                "description": "Optional additional context"
                            }
                        },
                        "required": ["conversation_id", "agent_id", "user_query", "agent_response"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_agent_knowledge",
                    "description": "Search for similar past conversations or agent executions in Pinecone. Use this to find relevant past solutions or similar queries.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Natural language query describing what you're looking for"
                            },
                            "agent_id": {
                                "type": "string",
                                "description": "Optional filter by specific agent"
                            },
                            "top_k": {
                                "type": "integer",
                                "description": "Number of results to return (default: 5)",
                                "default": 5
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
        ]
    
    def _execute_function(self, function_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a function call and return the result."""
        import logging
        logger = logging.getLogger("ConversationalAgent")
        
        try:
            # Auto-correct conversation_id if agent provided wrong one
            if hasattr(self, '_current_conversation_id') and self._current_conversation_id:
                if 'conversation_id' in arguments:
                    # If agent provided a conversation_id, check if it's reasonable
                    provided_id = arguments.get("conversation_id", "")
                    # If it's a generic ID like "1", "conversation", etc., replace with actual ID
                    if provided_id in ["1", "conversation", "conv", ""] or len(provided_id) < 5:
                        logger.info(f"🔧 Auto-correcting conversation_id from '{provided_id}' to '{self._current_conversation_id}'")
                        arguments["conversation_id"] = self._current_conversation_id
                    # Otherwise, trust the agent's provided ID (might be for a different conversation)
                else:
                    # If no conversation_id provided, use the current one
                    logger.info(f"🔧 Adding missing conversation_id: '{self._current_conversation_id}'")
                    arguments["conversation_id"] = self._current_conversation_id
            
            if function_name == "retrieve_conversation_history":
                conv_id = arguments.get("conversation_id")
                query = arguments.get("query")
                top_k = arguments.get("top_k", 10)
                logger.info(f"🔍 Executing retrieve_conversation_history: conversation_id={conv_id}, top_k={top_k}")
                
                # Call the underlying function directly (not the tool wrapper)
                from tools.pinecone_tools import get_conversation_history
                result = get_conversation_history(
                    conversation_id=conv_id,
                    query=query,
                    top_k=top_k
                )
                
                logger.info(f"✅ Retrieved {result.get('count', 0)} messages for conversation_id={conv_id}")
                return result
            elif function_name == "store_conversation_context":
                # Also auto-correct conversation_id for store function
                if hasattr(self, '_current_conversation_id') and self._current_conversation_id:
                    if 'conversation_id' not in arguments or arguments.get("conversation_id") in ["1", "conversation", "conv", ""]:
                        arguments["conversation_id"] = self._current_conversation_id
                
                return store_conversation_context(
                    conversation_id=arguments.get("conversation_id"),
                    agent_id=arguments.get("agent_id", "conversational_agent"),
                    user_query=arguments.get("user_query"),
                    agent_response=arguments.get("agent_response"),
                    context=arguments.get("context")
                )
            elif function_name == "search_agent_knowledge":
                return search_agent_knowledge(
                    query=arguments.get("query"),
                    agent_id=arguments.get("agent_id"),
                    top_k=arguments.get("top_k", 5)
                )
            else:
                return {"error": f"Unknown function: {function_name}"}
        except Exception as e:
            return {"error": str(e)}
    
    def generate_response(
        self,
        user_query: str,
        conversation_id: str,
        conversation_history: Optional[List[Dict]] = None,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Generate a conversational response using OpenAI function calling.
        Returns structured response with function calls (Cursor/Windsurf style).
        
        Args:
            user_query: User's query
            conversation_id: Conversation identifier (will be used for all function calls)
            conversation_history: Previous conversation messages
            context: Additional context
            
        Returns:
            Dict with 'response', 'function_calls', and 'metadata'
        """
        # Store conversation_id for function execution
        self._current_conversation_id = conversation_id
        """
        Generate a conversational response using OpenAI function calling.
        Returns structured response with function calls (Cursor/Windsurf style).
        
        Args:
            user_query: User's query
            conversation_id: Conversation identifier
            conversation_history: Previous conversation messages
            context: Additional context
            
        Returns:
            Dict with 'response', 'function_calls', and 'metadata'
        """
        # Build system message with conversation_id
        system_message = f"""You are a friendly and knowledgeable AI assistant powered by OpenAI function calling.
You excel at:
- Understanding user queries in natural language
- Providing clear, concise, and helpful responses
- Remembering previous conversations using Pinecone memory
- Referencing past interactions when relevant
- Maintaining context across multiple conversation turns

IMPORTANT: The current conversation ID is: {conversation_id}
When calling functions that require conversation_id, you MUST use this exact ID: "{conversation_id}"

Your workflow:
1. Use retrieve_conversation_history to get context from previous messages (use conversation_id: "{conversation_id}")
2. Use search_agent_knowledge if you need to find similar past conversations
3. Generate a natural, conversational response
4. Use store_conversation_context to save the conversation for future reference (use conversation_id: "{conversation_id}")

Always be helpful, accurate, and maintain a friendly professional tone.
When you need to retrieve or store information, use the available functions with the correct conversation_id."""

        # Build messages
        messages = [{"role": "system", "content": system_message}]
        
        # Add conversation history
        if conversation_history:
            for msg in conversation_history:
                if msg.get('user_query'):
                    messages.append({"role": "user", "content": msg['user_query']})
                if msg.get('agent_response'):
                    messages.append({"role": "assistant", "content": msg['agent_response']})
        
        # Add current user query
        messages.append({"role": "user", "content": user_query})
        
        # Call OpenAI with function calling
        response = self.openai_client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=self.functions,
            tool_choice="auto",  # Let the model decide when to use functions
            temperature=0.7,
            max_tokens=2000
        )
        
        message = response.choices[0].message
        function_calls = []
        final_response = ""
        
        # Handle function calls
        if message.tool_calls:
            # Execute function calls
            messages.append(message)  # Add assistant's message with tool calls
            
            for tool_call in message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                # Execute function
                function_result = self._execute_function(function_name, function_args)
                
                # Add function result to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": function_name,
                    "content": json.dumps(function_result)
                })
                
                function_calls.append({
                    "id": tool_call.id,
                    "name": function_name,
                    "arguments": function_args,
                    "result": function_result
                })
            
            # Get final response after function execution
            final_response_obj = self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.functions,
                tool_choice="auto",
                temperature=0.7,
                max_tokens=2000
            )
            
            final_message = final_response_obj.choices[0].message
            final_response = final_message.content or ""
            
            # Check if there are more function calls needed
            if final_message.tool_calls:
                # Recursively handle additional function calls (up to 3 iterations)
                for tool_call in final_message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    function_result = self._execute_function(function_name, function_args)
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": function_name,
                        "content": json.dumps(function_result)
                    })
                    
                    function_calls.append({
                        "id": tool_call.id,
                        "name": function_name,
                        "arguments": function_args,
                        "result": function_result
                    })
                
                # Get final response
                final_response_obj = self.openai_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=2000
                )
                final_response = final_response_obj.choices[0].message.content or ""
        else:
            # No function calls, just text response
            final_response = message.content or ""
        
        return {
            "response": final_response,
            "function_calls": function_calls,
            "metadata": {
                "conversation_id": conversation_id,
                "model": self.model,
                "has_function_calls": len(function_calls) > 0,
                "function_call_count": len(function_calls)
            }
        }


# Create singleton instance
_conversational_agent_instance = None

def get_conversational_agent():
    """Get or create the conversational agent instance."""
    global _conversational_agent_instance
    if _conversational_agent_instance is None:
        _conversational_agent_instance = ConversationalAgentWithFunctionCalling()
    return _conversational_agent_instance

# For backward compatibility, export as conversational_agent
conversational_agent = get_conversational_agent()

