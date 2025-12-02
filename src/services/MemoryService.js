/**
 * Memory Service
 * Manages conversation history retrieval from Pinecone using semantic search
 */

import OpenAI from 'openai';
import axios from 'axios';
import config from '../config/index.js';
import { logger } from '../utils/logger.js';

export default class MemoryService {
  constructor() {
    this.healthy = false;
    this.workingMemory = new Map(); // In-process cache
    this.openaiClient = null; // OpenAI client for embeddings
    this.pineconeHost = null;
    this.pineconeNamespace = 'crewai-agents'; // Default namespace for CrewAI conversations
    this.embeddingDimension = 1024; // Default dimension
    this.embeddingModel = 'text-embedding-3-large'; // Default model
  }

  async initialize() {
    // Initialize Pinecone for semantic search if configured
    if (config.pinecone?.enabled && config.pinecone?.apiKey && (config.pinecone?.host || config.pinecone?.indexName)) {
      try {
        this.pineconeHost = (config.pinecone.host || '').replace(/\/$/, '');
        this.pineconeNamespace = config.pinecone.namespace || 'crewai-agents';
        this.embeddingDimension = config.pinecone.dimension || 1024;
        this.embeddingModel = config.pinecone.embeddingModel || 'text-embedding-3-large';

        if (!this.pineconeHost && config.pinecone.indexName && config.pinecone.environment) {
          // Construct host from index + environment if not provided
          this.pineconeHost = `https://${config.pinecone.indexName}.svc.${config.pinecone.environment}.pinecone.io`;
    }

        if (!this.pineconeHost) {
          logger.warn('⚠️ Pinecone host not configured');
        } else {
          // Initialize OpenAI client for embeddings
          if (config.openai?.enabled && config.openai?.apiKey) {
            this.openaiClient = new OpenAI({ apiKey: config.openai.apiKey });
            logger.info('✅ MemoryService Pinecone initialized', {
              host: this.pineconeHost,
              namespace: this.pineconeNamespace,
              dimension: this.embeddingDimension
            });
          } else {
            logger.warn('⚠️ OpenAI not configured, Pinecone semantic search will not work');
          }
        }
      } catch (error) {
        logger.error('❌ MemoryService Pinecone initialization failed', { error: error.message });
      }
    }
      
      this.healthy = true;
      logger.info('✅ MemoryService initialized');
  }

  isHealthy() {
    return this.healthy;
  }

  /**
   * Get conversation history for a conversation ID
   * Returns a simplified format for problem type classification
   * If query is provided, uses semantic search to retrieve top relevant messages from Pinecone
   * @param {string} conversationId
   * @param {number} limit
   * @param {string} query - Optional query for semantic search
   * @returns {Promise<Array>} Array of conversation messages
   */
  async getConversationHistory(conversationId, limit = 10, query = null) {
    if (!conversationId) {
      return [];
    }

    // Use Pinecone semantic search if query is provided and Pinecone is configured
    if (query && this.pineconeHost && config.pinecone?.apiKey && this.openaiClient) {
      try {
        // Generate embedding for the query
        const queryEmbedding = await this._generateEmbedding(query);
        
        // Query Pinecone with semantic search
        const url = `${this.pineconeHost}/query`;
        const payload = {
          vector: queryEmbedding,
          topK: limit * 2, // Get more results, then filter
          includeMetadata: true,
          namespace: this.pineconeNamespace,
          filter: {
            conversation_id: { $eq: conversationId },
            type: { $eq: 'conversation_context' }
          }
        };
        const headers = {
          'Content-Type': 'application/json',
          'Api-Key': config.pinecone.apiKey
        };

        const { data } = await axios.post(url, payload, { headers });
        const matches = data.matches || [];

        // Format messages from Pinecone results
        const messages = matches
          .map(match => {
            const metadata = match.metadata || {};
            const userQuery = metadata.user_query || '';
            const agentResponse = metadata.agent_response || '';
            const timestamp = metadata.timestamp || '';

            if (!userQuery && !agentResponse) {
              return null;
        }

            // Extract workflowStage - handle both snake_case (from Python) and camelCase
            // Python stores as 'workflow_stage' in Pinecone metadata, but we also check for 'workflowStage'
            const workflowStage = metadata.workflow_stage || metadata.workflowStage || null;

            // Format for both problem type classifier and conversational agent
            // Agent expects: user_query and agent_response fields
            // Problem classifier expects: content field (for backward compatibility)
            return {
              // For conversational agent (primary format)
              user_query: userQuery,
              agent_response: agentResponse,
              // For problem type classifier (backward compatibility)
              role: 'user',
              content: userQuery,
              timestamp: timestamp,
              score: match.score || 0.0, // Relevance score from semantic search
              workflowStage: workflowStage, // Set at top level for easy access
              metadata: {
                agent_id: metadata.agent_id || null,
                workflowStage: workflowStage, // Also in metadata for compatibility
                // Include any other extra metadata fields
                ...Object.fromEntries(
                  Object.entries(metadata).filter(([key]) => 
                    !['user_query', 'agent_response', 'agent_id', 'timestamp', 'type', 
                      'conversation_id', 'workflow_stage', 'workflowStage'].includes(key)
                  )
                )
              }
            };
          })
          .filter(Boolean)
          .slice(0, limit); // Take top K most relevant

        if (messages.length > 0) {
          logger.info('✅ Retrieved relevant conversation history from Pinecone', {
            conversationId,
            count: messages.length,
            query: query.substring(0, 50) + '...'
          });
          return messages;
        }
      } catch (error) {
        logger.warn('⚠️ Failed to retrieve conversation history from Pinecone, falling back', {
          error: error.message,
          conversationId
        });
      }
    }

    // Fallback: return empty array if Pinecone is not available or query is not provided
    // The actual conversation history is retrieved by the conversational agent via Pinecone
    return [];
    }
    
  /**
   * Generate embedding using OpenAI API
   * @private
   */
  async _generateEmbedding(text) {
    if (!this.openaiClient) {
      throw new Error('OpenAI client not initialized');
    }

    try {
      const response = await this.openaiClient.embeddings.create({
        model: this.embeddingModel,
        input: text,
        dimensions: this.embeddingDimension,
      });

      return response.data[0].embedding;
    } catch (error) {
      logger.error('❌ Failed to generate embedding', {
        error: error.message,
        model: this.embeddingModel,
        dimensions: this.embeddingDimension
      });
      throw error;
    }
  }

  /**
   * Store conversation context to Pinecone
   * @param {string} conversationId - Conversation identifier
   * @param {string} agentId - Agent identifier
   * @param {string} userQuery - User's query
   * @param {string} agentResponse - Agent's response
   * @param {object} context - Optional additional context (problem_type, workflow_stage, etc.)
   * @returns {Promise<object>} Result with stored status and vector_id
   */
  async storeConversationContext(conversationId, agentId, userQuery, agentResponse, context = {}) {
    if (!conversationId || !userQuery || !agentResponse) {
      logger.warn('⚠️ Missing required parameters for storing conversation context', {
        hasConversationId: !!conversationId,
        hasUserQuery: !!userQuery,
        hasAgentResponse: !!agentResponse
      });
      return {
        stored: false,
        message: 'Missing required parameters'
      };
    }

    // Use Pinecone if configured
    if (this.pineconeHost && config.pinecone?.apiKey && this.openaiClient) {
      try {
        // Combine query and response for embedding (same format as Python)
        const textToEmbed = `Query: ${userQuery}\n\nResponse: ${agentResponse}`;
        const embedding = await this._generateEmbedding(textToEmbed);
        
        // Generate unique vector ID (same format as Python)
        const timestamp = new Date().toISOString().replace(/[-:]/g, '').replace(/\..+/, '').replace('T', '');
        const vectorId = `conv:${conversationId}:${agentId || 'conversational_agent'}:${timestamp}`;
        
        // Prepare metadata (same format as Python)
        const vectorMetadata = {
          conversation_id: conversationId,
          agent_id: agentId || 'conversational_agent',
          user_query: userQuery,
          agent_response: agentResponse,
          timestamp: new Date().toISOString(),
          type: 'conversation_context',
          ...context // Include any additional context (problem_type, workflow_stage, etc.)
        };
        
        // Store in Pinecone
        const url = `${this.pineconeHost}/vectors/upsert`;
        const payload = {
          namespace: this.pineconeNamespace,
          vectors: [{
            id: vectorId,
            values: embedding,
            metadata: vectorMetadata
          }]
        };
        const headers = {
          'Content-Type': 'application/json',
          'Api-Key': config.pinecone.apiKey
        };

        await axios.post(url, payload, { headers });
        
        logger.info('✅ Conversation context stored in Pinecone', {
          conversationId,
          agentId: agentId || 'conversational_agent',
          vectorId
        });
        
        return {
          stored: true,
          vector_id: vectorId,
          message: `Conversation context saved (ID: ${vectorId})`
        };
      } catch (error) {
        logger.error('❌ Failed to store conversation context in Pinecone', {
          error: error.message,
          conversationId,
          agentId
        });
        return {
          stored: false,
          message: `Error saving context: ${error.message}`
        };
      }
    }

    // Fallback if Pinecone not configured
    logger.warn('⚠️ Pinecone not configured, cannot store conversation context');
    return {
      stored: false,
      message: 'Pinecone not configured'
    };
  }

  /**
   * Clear working memory for a conversation
   */
  clearWorkingMemory(conversationId) {
    this.workingMemory.delete(conversationId);
  }
}

