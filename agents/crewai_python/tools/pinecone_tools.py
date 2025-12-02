"""
Pinecone Integration Tools for CrewAI Agents
============================================

Provides tools for CrewAI agents to interact with Pinecone vector database:
- Store agent execution results and insights
- Retrieve similar past executions for context
- Search knowledge base for relevant information
- Maintain conversation memory across agent runs

Uses Pinecone REST API (no SDK required).
"""

import os
import json
from typing import Dict, List, Any, Optional
from crewai.tools import tool
from datetime import datetime
import hashlib
import logging
import requests

# Pinecone configuration from environment
PINECONE_API_KEY = os.getenv('PINECONE_API_KEY')
PINECONE_HOST = os.getenv('PINECONE_HOST')  # e.g., https://agent-am60zjk.svc.aped-4627-b74a.pinecone.io
PINECONE_INDEX_NAME = os.getenv('PINECONE_INDEX_NAME')
PINECONE_NAMESPACE = os.getenv('PINECONE_NAMESPACE', 'crewai-agents')
PINECONE_DIMENSION = int(os.getenv('PINECONE_DIMENSION', '1024'))
EMBEDDING_MODEL = os.getenv('PINECONE_EMBEDDING_MODEL', 'text-embedding-3-large')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

_logger = logging.getLogger("PineconeTools")
if not _logger.handlers:
    logging.basicConfig(level=logging.INFO)

def _get_pinecone_base_url() -> Optional[str]:
    """Get Pinecone base URL from host or index name."""
    if PINECONE_HOST:
        # Ensure it has https:// prefix
        host = PINECONE_HOST
        if not host.startswith('http'):
            host = f'https://{host}'
        return host.rstrip('/')
    
    if PINECONE_INDEX_NAME:
        # Construct host from index name (serverless format)
        # This is a fallback - ideally use PINECONE_HOST
        _logger.warning("Using PINECONE_INDEX_NAME to construct URL. Consider using PINECONE_HOST instead.")
        return f'https://{PINECONE_INDEX_NAME}.svc.pinecone.io'
    
    return None


def _generate_embedding(text: str) -> List[float]:
    """Generate embedding using OpenAI API with specified dimensions."""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is required for embeddings")
    
    try:
        import requests
        response = requests.post(
            'https://api.openai.com/v1/embeddings',
            headers={
                'Authorization': f'Bearer {OPENAI_API_KEY}',
                'Content-Type': 'application/json'
            },
            json={
                'model': EMBEDDING_MODEL,
                'input': text,
                'dimensions': PINECONE_DIMENSION
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json()['data'][0]['embedding']
    except Exception as e:
        raise ValueError(f"Failed to generate embedding: {str(e)}")


def _upsert_to_pinecone(vectors: List[Dict]) -> bool:
    """Upsert vectors to Pinecone via REST API."""
    if not PINECONE_API_KEY:
        _logger.warning("Pinecone API key is not set")
        return False
    
    base_url = _get_pinecone_base_url()
    if not base_url:
        _logger.error("Pinecone host/index not configured. Set PINECONE_HOST or PINECONE_INDEX_NAME")
        return False
    
    try:
        url = f"{base_url}/vectors/upsert"
        headers = {
            'Api-Key': PINECONE_API_KEY,
            'Content-Type': 'application/json'
        }
        payload = {
            'vectors': vectors,
            'namespace': PINECONE_NAMESPACE
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        _logger.debug(f"✅ Pinecone upsert successful: {response.json()}")
        return True
    except Exception as e:
        _logger.error(f"⚠️ Pinecone upsert failed: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                _logger.error(f"   Error details: {error_detail}")
            except:
                _logger.error(f"   Response: {e.response.text[:200]}")
        return False


def _query_pinecone(query_vector: List[float], top_k: int = 5, filter_dict: Optional[Dict] = None) -> List[Dict]:
    """Query Pinecone via REST API."""
    if not PINECONE_API_KEY:
        _logger.warning("Pinecone API key is not set")
        return []
    
    base_url = _get_pinecone_base_url()
    if not base_url:
        _logger.error("Pinecone host/index not configured. Set PINECONE_HOST or PINECONE_INDEX_NAME")
        return []
    
    try:
        url = f"{base_url}/query"
        headers = {
            'Api-Key': PINECONE_API_KEY,
            'Content-Type': 'application/json'
        }
        payload = {
            'vector': query_vector,
            'topK': top_k,
            'includeMetadata': True,
            'namespace': PINECONE_NAMESPACE
        }
        
        if filter_dict:
            payload['filter'] = filter_dict
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        result = response.json()
        return result.get('matches', [])
    except Exception as e:
        _logger.error(f"⚠️ Pinecone query failed: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                _logger.error(f"   Error details: {error_detail}")
            except:
                _logger.error(f"   Response: {e.response.text[:200]}")
        return []


@tool("store_agent_result")
def store_agent_result(
    agent_id: str,
    task_description: str,
    result: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Store agent execution result in Pinecone for future retrieval.
    
    Use this to:
    - Save successful agent executions for reference
    - Build a knowledge base of past solutions
    - Enable agents to learn from previous runs
    
    Args:
        agent_id: Identifier of the agent (e.g., 'rmn_portfolio_optimizer')
        task_description: Description of the task executed
        result: The result/output from the agent execution
        metadata: Optional additional metadata (e.g., {'query': '...', 'confidence': 0.95})
    
    Returns:
        {
            'stored': bool,
            'vector_id': str,
            'message': str
        }
    
    Example:
        result = store_agent_result(
            agent_id='rmn_portfolio_optimizer',
            task_description='Optimize budget allocation across Amazon and Walmart RMNs',
            result='Recommended 60% to Amazon, 40% to Walmart based on ROAS analysis',
            metadata={'query': 'How should I allocate my RMN budget?', 'confidence': 0.92}
        )
    """
    if not PINECONE_API_KEY:
        return {
            'stored': False,
            'message': 'Pinecone API key not configured'
        }
    
    base_url = _get_pinecone_base_url()
    if not base_url:
        return {
            'stored': False,
            'message': 'Pinecone host/index not configured (set PINECONE_HOST or PINECONE_INDEX_NAME)'
        }
    
    try:
        # Combine task and result for embedding
        text_to_embed = f"{task_description}\n\nResult: {result}"
        embedding = _generate_embedding(text_to_embed)
        
        # Generate unique vector ID
        content_hash = hashlib.md5(text_to_embed.encode()).hexdigest()[:12]
        vector_id = f"agent:{agent_id}:{datetime.utcnow().strftime('%Y%m%d%H%M%S')}:{content_hash}"
        
        # Prepare metadata
        vector_metadata = {
            'agent_id': agent_id,
            'task_description': task_description,
            'result': result,
            'timestamp': datetime.utcnow().isoformat(),
            'type': 'agent_result'
        }
        if metadata:
            vector_metadata.update(metadata)
        
        # Store in Pinecone
        success = _upsert_to_pinecone([{
            'id': vector_id,
            'values': embedding,
            'metadata': vector_metadata
        }])
        
        if success:
            return {
                'stored': True,
                'vector_id': vector_id,
                'message': f'Agent result stored successfully (ID: {vector_id})'
            }
        else:
            return {
                'stored': False,
                'message': 'Failed to store in Pinecone'
            }
    except Exception as e:
        return {
            'stored': False,
            'message': f'Error storing result: {str(e)}'
        }


@tool("search_agent_knowledge")
def search_agent_knowledge(
    query: str,
    agent_id: Optional[str] = None,
    top_k: int = 5
) -> Dict[str, Any]:
    """
    Search for similar past agent executions in Pinecone.
    
    Use this to:
    - Find similar problems solved before
    - Retrieve relevant past solutions
    - Get context from previous agent runs
    - Learn from historical executions
    
    Args:
        query: Natural language query describing what you're looking for
        agent_id: Optional filter by specific agent (e.g., 'rmn_portfolio_optimizer')
        top_k: Number of results to return (default: 5)
    
    Returns:
        {
            'results': List[Dict],
            'count': int,
            'message': str
        }
    
    Example:
        # Find similar budget optimization tasks
        results = search_agent_knowledge(
            query='How to optimize RMN budget allocation?',
            agent_id='rmn_portfolio_optimizer',
            top_k=3
        )
        
        for result in results['results']:
            print(f"Task: {result['task_description']}")
            print(f"Result: {result['result']}")
    """
    if not PINECONE_API_KEY or not PINECONE_HOST:
        return {
            'results': [],
            'count': 0,
            'message': 'Pinecone not configured'
        }
    
    try:
        # Generate embedding for query
        query_embedding = _generate_embedding(query)
        
        # Build filter if agent_id specified
        filter_dict = None
        if agent_id:
            filter_dict = {
                'agent_id': {'$eq': agent_id},
                'type': {'$eq': 'agent_result'}
            }
        else:
            filter_dict = {'type': {'$eq': 'agent_result'}}
        
        # Query Pinecone
        matches = _query_pinecone(query_embedding, top_k=top_k, filter_dict=filter_dict)
        
        # Format results
        results = []
        for match in matches:
            metadata = match.get('metadata', {})
            results.append({
                'task_description': metadata.get('task_description', ''),
                'result': metadata.get('result', ''),
                'agent_id': metadata.get('agent_id', ''),
                'timestamp': metadata.get('timestamp', ''),
                'score': match.get('score', 0.0),
                'metadata': {k: v for k, v in metadata.items() 
                            if k not in ['task_description', 'result', 'agent_id', 'timestamp', 'type']}
            })
        
        return {
            'results': results,
            'count': len(results),
            'message': f'Found {len(results)} similar past executions'
        }
    except Exception as e:
        return {
            'results': [],
            'count': 0,
            'message': f'Error searching knowledge: {str(e)}'
        }


def search_agent_knowledge_direct(
    query: str,
    agent_id: Optional[str] = None,
    top_k: int = 5
) -> Dict[str, Any]:
    """
    Helper function (non-decorated) to search for similar past agent executions in Pinecone.
    Mirrors the logic of the @tool-decorated search_agent_knowledge but safe to call directly.
    """
    if not PINECONE_API_KEY or not PINECONE_HOST:
        return {
            'results': [],
            'count': 0,
            'message': 'Pinecone not configured'
        }
    
    try:
        # Generate embedding for query
        query_embedding = _generate_embedding(query)
        
        # Build filter if agent_id specified
        filter_dict = None
        if agent_id:
            filter_dict = {
                'agent_id': {'$eq': agent_id},
                'type': {'$eq': 'agent_result'}
            }
        else:
            filter_dict = {'type': {'$eq': 'agent_result'}}
        
        # Query Pinecone
        matches = _query_pinecone(query_embedding, top_k=top_k, filter_dict=filter_dict)
        
        # Format results
        results = []
        for match in matches:
            metadata = match.get('metadata', {})
            results.append({
                'task_description': metadata.get('task_description', ''),
                'result': metadata.get('result', ''),
                'agent_id': metadata.get('agent_id', ''),
                'timestamp': metadata.get('timestamp', ''),
                'score': match.get('score', 0.0),
                'metadata': {k: v for k, v in metadata.items() 
                            if k not in ['task_description', 'result', 'agent_id', 'timestamp', 'type']}
            })
        
        return {
            'results': results,
            'count': len(results),
            'message': f'Found {len(results)} similar past executions'
        }
    except Exception as e:
        return {
            'results': [],
            'count': 0,
            'message': f'Error searching knowledge: {str(e)}'
        }

@tool("store_conversation_context")
def store_conversation_context(
    conversation_id: str,
    agent_id: str,
    user_query: str,
    agent_response: str,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Store conversation context in Pinecone for memory across agent runs.
    
    Use this to:
    - Maintain conversation history
    - Enable agents to remember previous interactions
    - Build context for multi-turn conversations
    
    Args:
        conversation_id: Unique conversation identifier
        agent_id: Identifier of the agent
        user_query: User's query/question
        agent_response: Agent's response
        context: Optional additional context (e.g., {'intent': '...', 'entities': [...]})
    
    Returns:
        {
            'stored': bool,
            'vector_id': str,
            'message': str
        }
    
    Example:
        result = store_conversation_context(
            conversation_id='conv_123',
            agent_id='rmn_portfolio_optimizer',
            user_query='What is the optimal budget split?',
            agent_response='Based on ROAS analysis, recommend 60/40 split',
            context={'intent': 'budget_optimization', 'tenant_id': 'acme_corp'}
        )
    """
    # Delegate to helper function
    return save_conversation_context(conversation_id, agent_id, user_query, agent_response, context)


def save_conversation_context(
    conversation_id: str,
    agent_id: str,
    user_query: str,
    agent_response: str,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Helper function (non-decorated) to save conversation context to Pinecone.
    This can be called directly from Python code, not just as a CrewAI tool.
    """
    import logging
    logger = logging.getLogger("PineconeTools")
    logger.info(f"💾 save_conversation_context called: conversation_id={conversation_id}, agent_id={agent_id}, query_length={len(user_query)}, response_length={len(agent_response)}")
    
    if not PINECONE_API_KEY:
        logger.warning("⚠️ Pinecone not configured - API_KEY missing")
        return {
            'stored': False,
            'message': 'Pinecone API key not configured'
        }
    
    base_url = _get_pinecone_base_url()
    if not base_url:
        logger.warning("⚠️ Pinecone not configured - HOST or INDEX_NAME missing")
        return {
            'stored': False,
            'message': 'Pinecone host/index not configured'
        }
    
    try:
        # Combine query and response for embedding
        text_to_embed = f"Query: {user_query}\n\nResponse: {agent_response}"
        embedding = _generate_embedding(text_to_embed)
        
        # Generate unique vector ID
        vector_id = f"conv:{conversation_id}:{agent_id}:{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        # Prepare metadata
        vector_metadata = {
            'conversation_id': conversation_id,
            'agent_id': agent_id,
            'user_query': user_query,
            'agent_response': agent_response,
            'timestamp': datetime.utcnow().isoformat(),
            'type': 'conversation_context'
        }
        if context:
            vector_metadata.update(context)
        
        # Store in Pinecone
        success = _upsert_to_pinecone([{
            'id': vector_id,
            'values': embedding,
            'metadata': vector_metadata
        }])
        
        if success:
            logger.info(f"✅ Successfully saved conversation context in Pinecone: vector_id={vector_id}")
            return {
                'stored': True,
                'vector_id': vector_id,
                'message': f'Conversation context saved (ID: {vector_id})'
            }
        else:
            logger.error(f"❌ Failed to save in Pinecone: success=False")
            return {
                'stored': False,
                'message': 'Failed to save in Pinecone'
            }
    except Exception as e:
        logger.error(f"❌ Error saving context in Pinecone: {str(e)}", exc_info=True)
        return {
            'stored': False,
            'message': f'Error saving context: {str(e)}'
        }


def get_conversation_history(
    conversation_id: str,
    query: Optional[str] = None,
    top_k: int = 10
) -> Dict[str, Any]:
    """
    Helper function (non-decorated) to retrieve conversation history from Pinecone.
    This can be called directly from Python code, not just as a CrewAI tool.
    """
    import logging
    logger = logging.getLogger("PineconeTools")
    logger.info(f"🔍 get_conversation_history called: conversation_id={conversation_id}, top_k={top_k}")
    
    if not PINECONE_API_KEY:
        logger.warning("⚠️ Pinecone not configured - API_KEY missing")
        return {
            'messages': [],
            'count': 0,
            'message': 'Pinecone API key not configured'
        }
    
    base_url = _get_pinecone_base_url()
    if not base_url:
        logger.warning("⚠️ Pinecone not configured - HOST or INDEX_NAME missing")
        return {
            'messages': [],
            'count': 0,
            'message': 'Pinecone host/index not configured'
        }
    
    try:
        # If query provided, use semantic search
        if query:
            query_embedding = _generate_embedding(query)
            matches = _query_pinecone(
                query_embedding,
                top_k=top_k,
                filter_dict={
                    'conversation_id': {'$eq': conversation_id},
                    'type': {'$eq': 'conversation_context'}
                }
            )
        else:
            # Use zero vector to get all matches (filtered by conversation_id)
            zero_vector = [0.0] * PINECONE_DIMENSION
            matches = _query_pinecone(
                zero_vector,
                top_k=top_k * 2,  # Get more, then filter
                filter_dict={
                    'conversation_id': {'$eq': conversation_id},
                    'type': {'$eq': 'conversation_context'}
                }
            )
        
        # Format messages
        messages = []
        for match in matches:
            metadata = match.get('metadata', {})
            # Include core fields plus any additional metadata (e.g., user_role)
            extra_metadata = {
                k: v for k, v in metadata.items()
                if k not in ['user_query', 'agent_response', 'agent_id', 'timestamp', 'type']
            }
            messages.append({
                'user_query': metadata.get('user_query', ''),
                'agent_response': metadata.get('agent_response', ''),
                'agent_id': metadata.get('agent_id', ''),
                'timestamp': metadata.get('timestamp', ''),
                'score': match.get('score', 0.0) if query else None,
                'metadata': extra_metadata if extra_metadata else None
            })
        
        # Sort by timestamp if no query (chronological order)
        if not query:
            messages.sort(key=lambda x: x['timestamp'])
        
        result = {
            'messages': messages[:top_k],
            'count': len(messages),
            'message': f'Retrieved {len(messages)} conversation messages'
        }
        logger.info(f"✅ Retrieved {len(messages)} messages from Pinecone for conversation_id={conversation_id}")
        return result
    except Exception as e:
        logger.error(f"❌ Error retrieving history from Pinecone: {str(e)}", exc_info=True)
        return {
            'messages': [],
            'count': 0,
            'message': f'Error retrieving history: {str(e)}'
        }


@tool("retrieve_conversation_history")
def retrieve_conversation_history(
    conversation_id: str,
    query: Optional[str] = None,
    top_k: int = 10
) -> Dict[str, Any]:
    """
    Retrieve conversation history from Pinecone.
    
    Use this to:
    - Get previous messages in a conversation
    - Understand conversation context
    - Reference past interactions
    
    Args:
        conversation_id: Conversation identifier
        query: Optional query to find relevant messages (if None, returns all for conversation)
        top_k: Number of results to return
    
    Returns:
        {
            'messages': List[Dict],
            'count': int,
            'message': str
        }
    
    Example:
        history = retrieve_conversation_history(
            conversation_id='conv_123',
            top_k=5
        )
        
        for msg in history['messages']:
            print(f"Query: {msg['user_query']}")
            print(f"Response: {msg['agent_response']}")
    """
    # Delegate to helper function
    return get_conversation_history(conversation_id, query, top_k)


# Export all tools
PINECONE_TOOLS = [
    store_agent_result,
    search_agent_knowledge,
    store_conversation_context,
    retrieve_conversation_history
]

