"""
Conversational CrewAI Agent
===========================

A conversational AI agent that uses OpenAI for generating responses.
All Pinecone memory operations (retrieval and storage) are handled by MemoryService.js.
Conversation history is pre-loaded and passed to the agent.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from openai import OpenAI

sys.path.insert(0, str(Path(__file__).parent.parent))
# Pinecone operations are handled by MemoryService.js - no need to import Pinecone tools


class ConversationalAgentWithFunctionCalling:
    """
    Conversational agent that generates responses using OpenAI.
    All memory operations are handled by MemoryService.js - no function calling needed.
    Returns structured responses compatible with Cursor/Windsurf style.
    """
    
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4-turbo-preview')
        
        # Define available functions for OpenAI function calling
        # Note: All Pinecone operations (retrieval and storage) are handled by MemoryService.js
        # No Pinecone function calling needed - conversation history is pre-loaded and storage is handled server-side
        self.functions = []  # No function calling needed - all operations handled by MemoryService.js
    
    def _execute_function(self, function_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a function call and return the result."""
        # No function calling needed - all Pinecone operations handled by MemoryService.js
        return {"error": f"No functions available - all operations handled by MemoryService.js"}
    
    def generate_response(
        self,
        user_query: str,
        conversation_id: str,
        conversation_history: Optional[List[Dict]] = None,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Generate a conversational response using OpenAI.
        All memory operations are handled by MemoryService.js.
        
        Args:
            user_query: User's query
            conversation_id: Conversation identifier
            conversation_history: Previous conversation messages (pre-loaded by MemoryService.js)
            context: Additional context (problem type, workflow stage, etc.)
            
        Returns:
            Dict with 'response', 'function_calls' (empty), and 'metadata'
        """
        # Store conversation_id (for potential future use)
        self._current_conversation_id = conversation_id
        
        # Extract problem context from context if available
        problem_type = context.get('problem_type', 'general')
        problem_space = context.get('problem_space', '')
        workflow_stage = context.get('workflow_stage', 'interpret')
        datasource = context.get('datasource', None)
        
        # Build system message with conversation_id and problem-first approach
        system_message = f"""You are a business intelligence assistant for executives, operating on a problem-first approach.

CORE PRINCIPLES:
1. The system always starts with a narrowly defined problem space - executives don't ask "anything", they start with specific problems
2. Problem types: alert (risks/alerts), understand (analysis/insights), solve (solutions), monitor (tracking), automate (workflows)
3. Workflow progression: interpret outputs → ask for recommendation → ask "what if" (simulator) → then full LLM questions
4. You help interpret outputs, provide recommendations, run simulations, and answer questions within the problem context

CURRENT CONTEXT:
- Conversation ID: {conversation_id}
- Problem Type: {problem_type}
- Problem Space: {problem_space if problem_space else 'Not yet defined'}
- Workflow Stage: {workflow_stage}
- Datasource Available: {'Yes' if datasource else 'No'}

WORKFLOW STAGES:
1. **interpret** - First stage: Interpret datasource
   - ONLY use this when there is a datasource from datacube
   - Explain what the datasource means, what it represents
   - Identify key insights, patterns, and trends in the datasource
   - If there is NO datasource, SKIP to "full-llm" stage instead
   - Example: "Here's what the datasource shows: [interpreting the datasource]"
   - NOT: "I need more information" (that's full-llm, not interpret)

2. **recommend** - Second stage: Provide recommendations based on interpreted outputs
   - Suggest actions or decisions based on the interpreted data
   - Provide actionable insights derived from the interpretation
   - Consider business implications of the interpreted results

3. **what-if** - Third stage: Run simulations or "what if" scenarios
   - Explore alternative scenarios based on interpreted data
   - Model different outcomes using the interpreted insights
   - Help with decision-making through simulation

4. **full-llm** - Final stage: Full LLM capabilities for complex questions
   - Use when there are NO outputs/data to interpret (setup tasks, configuration)
   - Answer complex questions requiring deep knowledge
   - Help set up systems, define criteria, explain concepts
   - Provide comprehensive analysis when data interpretation isn't applicable
   - Example: "To set up alerts, you need to define: [explaining setup requirements]"

YOUR ROLE:
- You operate within the defined problem space - stay focused on the executive's problem
- Guide the conversation through workflow stages naturally
- Remember: This is NOT "ask me anything" - it's problem-focused with narrow scope
- You can still answer general questions, but always relate them back to the problem context when possible
- All conversation memory is handled automatically by MemoryService.js - just focus on providing helpful responses

CRITICAL: Workflow Stage Selection
- If the user query asks to SET UP, CONFIGURE, or DEFINE something (like "alert me if...", "monitor...", "automate...") and there is NO datasource, you should respond as if in "full-llm" stage, not "interpret" stage
- "interpret" stage is ONLY for when there is a datasource from datacube
- For setup/configuration queries without a datasource, use "full-llm" behavior even if workflow_stage says "interpret"

IMPORTANT:
1. Conversation history is pre-loaded for you by MemoryService.js - use the conversation_history provided in the context.
2. All conversation storage is handled automatically by MemoryService.js - you don't need to call any functions to save conversations.
3. Focus on providing helpful responses within the problem space - all memory operations are handled server-side.

Your goal is to provide the best answer within the problem space, guide through workflow stages, and use tools when they add value."""

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
        
        # Call OpenAI (no function calling - all operations handled by MemoryService.js)
        response = self.openai_client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.7,
            max_tokens=2000
        )
        
        message = response.choices[0].message
        function_calls = []  # Empty - no function calling needed
        
        # Simple text response - no function calling
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

