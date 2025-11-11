/**
 * Memory Service
 * Manages hierarchical memory (working, short-term, long-term)
 */

import { createClient } from '@supabase/supabase-js';
import config from '../config/index.js';
import { logger } from '../utils/logger.js';

export default class MemoryService {
  constructor() {
    this.supabase = null;
    this.healthy = false;
    this.workingMemory = new Map(); // In-process cache
  }

  async initialize() {
    if (!config.supabase.enabled) {
      logger.warn('Supabase not configured, MemoryService will use in-memory only');
      this.healthy = true; // Still healthy, just limited
      return;
    }

    try {
      this.supabase = createClient(
        config.supabase.url,
        config.supabase.serviceRoleKey || config.supabase.anonKey
      );
      
      this.healthy = true;
      logger.info('✅ MemoryService initialized');
    } catch (error) {
      logger.error('❌ MemoryService initialization failed', { error: error.message });
      this.healthy = false;
    }
  }

  isHealthy() {
    return this.healthy;
  }

  /**
   * Get context for a conversation
   * @param {string} conversationId
   * @param {string} userId
   * @param {object} params - Query parameters (query, intent, etc.)
   * @returns {Promise<object>} Memory context
   */
  async getContext(conversationId, userId, params = {}) {
    const context = {
      workingMemory: [],
      shortTermMemory: [],
      longTermMemory: [],
      conversationHistory: []
    };

    // Check working memory (in-process cache)
    const cached = this.workingMemory.get(conversationId);
    if (cached) {
      context.workingMemory = cached.items || [];
    }

    // Retrieve from Supabase if available
    if (this.supabase) {
      try {
        // Get conversation history
        const { data: conversations } = await this.supabase
          .from('conversations')
          .select('*')
          .eq('id', conversationId)
          .order('created_at', { ascending: false })
          .limit(10);

        if (conversations && conversations.length > 0) {
          context.conversationHistory = conversations;
        }

        // Get relevant memories (if knowledge_base table exists)
        const { data: memories } = await this.supabase
          .from('knowledge_base')
          .select('*')
          .eq('user_id', userId)
          .limit(5);

        if (memories && memories.length > 0) {
          context.shortTermMemory = memories.filter(m => m.memory_type === 'short_term');
          context.longTermMemory = memories.filter(m => m.memory_type === 'long_term');
        }

      } catch (error) {
        logger.warn('Memory retrieval error', { error: error.message });
      }
    }

    return context;
  }

  /**
   * Store execution results in memory
   */
  async storeExecution(data) {
    const { conversationId, userId, query, intent, agentResults } = data;

    // Store in working memory cache
    const existing = this.workingMemory.get(conversationId) || { items: [] };
    existing.items.push({
      query,
      intent,
      agentResults: agentResults?.summary || {},
      timestamp: new Date().toISOString()
    });
    
    // Keep only last 10 items in working memory
    if (existing.items.length > 10) {
      existing.items = existing.items.slice(-10);
    }
    
    this.workingMemory.set(conversationId, existing);

    // Store in Supabase if available
    if (this.supabase) {
      try {
        await this.supabase
          .from('conversations')
          .insert({
            id: conversationId,
            user_id: userId,
            message: query,
            intent: intent.intent,
            response: JSON.stringify(agentResults?.summary || {}),
            created_at: new Date().toISOString()
          });

        logger.info('✅ Execution stored in memory', { conversationId });
      } catch (error) {
        logger.warn('Failed to store execution in Supabase', { error: error.message });
      }
    }
  }

  /**
   * Clear working memory for a conversation
   */
  clearWorkingMemory(conversationId) {
    this.workingMemory.delete(conversationId);
  }
}

