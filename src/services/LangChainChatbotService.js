/**
 * LangChain Chatbot Service with Pinecone Memory
 * Provides conversational AI using LangChain with persistent memory via Pinecone
 */

import { ChatOpenAI } from '@langchain/openai';
import { ChatPromptTemplate, MessagesPlaceholder } from '@langchain/core/prompts';
import { HumanMessage, AIMessage, SystemMessage } from '@langchain/core/messages';
import { Pinecone } from '@pinecone-database/pinecone';
import { PineconeStore } from '@langchain/pinecone';
import { OpenAIEmbeddings } from '@langchain/openai';
import OpenAI from 'openai';
import axios from 'axios';
import config from '../config/index.js';
import { logger } from '../utils/logger.js';

export default class LangChainChatbotService {
  constructor() {
    this.llm = null;
    this.pineconeClient = null;
    this.embeddings = null;
    this.openaiClient = null; // Direct OpenAI client for embeddings with dimensions
    this.vectorStore = null;
    this.initialized = false;
    this.memoryStore = new Map(); // In-memory fallback for conversation history
    this.embeddingDimension = 1024; // Default dimension
    this.embeddingModel = 'text-embedding-3-large'; // Default model
    this.pineconeHost = null;
    this.pineconeIndexName = null;
    this.pineconeNamespace = 'default';
  }

  async initialize() {
    if (this.initialized) {
      return;
    }

    logger.info('🤖 Initializing LangChain Chatbot Service...');

    try {
      // Initialize OpenAI LLM
      if (!config.openai.enabled || !config.openai.apiKey) {
        throw new Error('OpenAI API key is required for LangChain chatbot');
      }

      this.llm = new ChatOpenAI({
        openAIApiKey: config.openai.apiKey,
        modelName: config.openai.model || 'gpt-4-turbo-preview',
        temperature: config.openai.temperature || 0.7,
        maxTokens: config.openai.maxTokens || 2000,
      });

      logger.info('✅ OpenAI LLM initialized');

      // Pinecone REST configuration (serverless)
      if (config.pinecone?.enabled && config.pinecone?.apiKey && (config.pinecone?.host || config.pinecone?.indexName)) {
        this.pineconeHost = (config.pinecone.host || '').replace(/\/$/, '');
        this.pineconeIndexName = config.pinecone.indexName || null;
        this.pineconeNamespace = config.pinecone.namespace || 'default';
        this.embeddingDimension = config.pinecone.dimension || 1024;
        this.embeddingModel = config.pinecone.embeddingModel || 'text-embedding-3-large';

        if (!this.pineconeHost && this.pineconeIndexName && config.pinecone.environment) {
          // Construct host from index + environment if not provided
          this.pineconeHost = `https://${this.pineconeIndexName}.svc.${config.pinecone.environment}.pinecone.io`;
        }

        if (!this.pineconeHost) {
          throw new Error('Pinecone host is required for serverless REST API');
        }

        logger.info('✅ Pinecone REST configured', {
          host: this.pineconeHost,
          index: this.pineconeIndexName,
          namespace: this.pineconeNamespace,
          dimension: this.embeddingDimension
        });

        // Initialize OpenAI client for embeddings with fixed dimensions
        this.openaiClient = new OpenAI({ apiKey: config.openai.apiKey });

        // Verify embedding dimension
        const testEmbedding = await this._generateEmbedding('test');
        if (testEmbedding.length !== this.embeddingDimension) {
          throw new Error(`Embedding dimension mismatch: got ${testEmbedding.length}, expected ${this.embeddingDimension}`);
        }
        logger.info(`✅ Embedding dimension verified: ${testEmbedding.length} dimensions`);
      } else {
        logger.info('ℹ️ Pinecone not configured, using in-memory memory only');
        logger.info('   Set PINECONE_API_KEY and PINECONE_HOST in .env to enable Pinecone');
      }

      this.initialized = true;
      logger.info('✅ LangChain Chatbot Service initialized');
    } catch (error) {
      logger.error('❌ Failed to initialize LangChain Chatbot Service', {
        error: error.message,
        stack: error.stack
      });
      throw error;
    }
  }

  /**
   * Get conversation history from Pinecone or in-memory store
   */
  async getConversationHistory(conversationId, limit = 10) {
    if (!conversationId) {
      return [];
    }

    // Use Pinecone REST if configured
    if (this.pineconeHost && config.pinecone?.apiKey) {
      try {
        const dimension = this.embeddingDimension || 1024;
        const zeroVector = new Array(dimension).fill(0);
        const url = `${this.pineconeHost}/query`;
        const payload = {
          vector: zeroVector,
          topK: limit * 2,
          includeMetadata: true,
          namespace: this.pineconeNamespace,
          filter: { conversationId: { $eq: conversationId } }
        };
        const headers = {
          'Content-Type': 'application/json',
          'Api-Key': config.pinecone.apiKey
        };
        const { data } = await axios.post(url, payload, { headers });

        const matches = data.matches || [];
        const messages = matches
          .map(m => {
            try {
              return JSON.parse(m.metadata?.content || m.metadata?.pageContent || '{}');
            } catch {
              return null;
            }
          })
          .filter(Boolean)
          .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))
          .slice(-limit);

        if (messages.length > 0) return messages;
      } catch (error) {
        logger.warn('Failed to retrieve from Pinecone (REST), using in-memory', { error: error.message });
      }
    }

    // Fallback to in-memory
    const history = this.memoryStore.get(conversationId) || [];
    return history.slice(-limit);
  }

  /**
   * Save message to Pinecone or in-memory store
   */
  async saveMessage(conversationId, role, content, metadata = {}) {
    if (!conversationId) {
      return;
    }

    const message = {
      role,
      content,
      timestamp: new Date().toISOString(),
      conversationId,
      ...metadata
    };

    // Save to Pinecone via REST if configured
    if (this.pineconeHost && config.pinecone?.apiKey) {
      try {
        const embedding = await this._generateEmbedding(content);
        if (embedding.length !== this.embeddingDimension) {
          throw new Error(`Embedding dimension mismatch: got ${embedding.length}, expected ${this.embeddingDimension}`);
        }

        const messageId = `${conversationId}-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
        const url = `${this.pineconeHost}/vectors/upsert`;
        const payload = {
          namespace: this.pineconeNamespace,
          vectors: [{
            id: messageId,
            values: embedding,
            metadata: {
              conversationId,
              role,
              content: JSON.stringify(message),
              pageContent: JSON.stringify(message),
              timestamp: message.timestamp,
              ...metadata
            }
          }]
        };
        const headers = {
          'Content-Type': 'application/json',
          'Api-Key': config.pinecone.apiKey
        };

        await axios.post(url, payload, { headers });
        logger.info('✅ Message saved to Pinecone (REST)', { conversationId, messageId, namespace: this.pineconeNamespace });
      } catch (error) {
        logger.error('❌ Failed to save to Pinecone (REST), using in-memory', { error: error.message, conversationId, role });
      }
    }

    // Always save to in-memory as backup
    if (!this.memoryStore.has(conversationId)) {
      this.memoryStore.set(conversationId, []);
    }
    const history = this.memoryStore.get(conversationId);
    history.push(message);

    if (history.length > 50) {
      history.shift();
    }
  }

  /**
   * Process a message and return a response
   */
  async processMessage(message, conversationId, context = {}) {
    if (!this.initialized) {
      await this.initialize();
    }

    const startTime = Date.now();

    try {
      // Get conversation history
      const history = await this.getConversationHistory(conversationId, 10);
      
      // Build conversation context
      const conversationMessages = [];
      
      // Add system message if provided
      if (context.systemPrompt) {
        conversationMessages.push({
          role: 'system',
          content: context.systemPrompt
        });
      }

      // Add history
      history.forEach(msg => {
        if (msg.role === 'user') {
          conversationMessages.push(new HumanMessage(msg.content));
        } else if (msg.role === 'assistant') {
          conversationMessages.push(new AIMessage(msg.content));
        }
      });

      // Add current message
      conversationMessages.push(new HumanMessage(message));

      // Build messages array for LLM
      const messages = [];
      
      // Add system message if provided
      if (context.systemPrompt) {
        messages.push(new SystemMessage(context.systemPrompt));
      }
      
      // Add conversation history (all except the current message)
      const historyMessages = conversationMessages.slice(0, -1);
      messages.push(...historyMessages);
      
      // Add current user message
      messages.push(new HumanMessage(message));

      // Invoke LLM directly with messages
      const response = await this.llm.invoke(messages);

      const responseText = response.content || response.text || 'I apologize, but I could not generate a response.';

      // Save messages to memory
      await this.saveMessage(conversationId, 'user', message, context);
      await this.saveMessage(conversationId, 'assistant', responseText, {
        ...context,
        processingTime: Date.now() - startTime
      });

      const processingTime = Date.now() - startTime;
      logger.info('💬 Chatbot response generated', {
        conversationId,
        processingTime: `${processingTime}ms`,
        messageLength: message.length,
        responseLength: responseText.length
      });

      return {
        response: responseText,
        conversationId,
        timestamp: new Date().toISOString(),
        processingTime,
        historyLength: history.length
      };
    } catch (error) {
      logger.error('❌ Error processing message with chatbot', {
        conversationId,
        error: error.message,
        stack: error.stack
      });
      
      throw error;
    }
  }

  /**
   * Check if service is healthy
   */
  isHealthy() {
    return this.initialized && this.llm !== null;
  }

  /**
   * Clear conversation history
   */
  async clearConversation(conversationId) {
    if (this.memoryStore.has(conversationId)) {
      this.memoryStore.delete(conversationId);
    }
    
    // Note: Pinecone deletion would require additional implementation
    // For now, we just clear in-memory
    logger.info('🗑️ Conversation history cleared', { conversationId });
  }

  /**
   * Generate embedding using OpenAI API directly with dimensions parameter
   * This ensures the dimensions parameter is properly applied
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
}

