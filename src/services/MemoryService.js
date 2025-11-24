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
        // Get conversation history by user_id (since id is primary key, we get all user conversations)
        // Filter to get recent conversations for context
        const { data: conversations } = await this.supabase
          .from('conversations')
          .select('*')
          .eq('user_id', userId)
          .order('created_at', { ascending: false })
          .limit(20); // Get more to have better context

        if (conversations && conversations.length > 0) {
          // Sort by created_at ascending for chronological order
          context.conversationHistory = conversations.sort((a, b) => 
            new Date(a.created_at) - new Date(b.created_at)
          );
        }

        // Get relevant memories (if knowledge_base table exists)
        // Get short-term memories (most recent 10)
        const { data: shortTermMemories, error: shortTermError } = await this.supabase
          .from('knowledge_base')
          .select('*')
          .eq('user_id', userId)
          .eq('memory_type', 'short_term')
          .order('created_at', { ascending: false })
          .limit(10);

        if (shortTermError) {
          logger.warn('Failed to retrieve short-term memories', { 
            error: shortTermError.message 
          });
        } else if (shortTermMemories && shortTermMemories.length > 0) {
          context.shortTermMemory = shortTermMemories;
        }

        // Get long-term memories (most recent 20)
        const { data: longTermMemories, error: longTermError } = await this.supabase
          .from('knowledge_base')
          .select('*')
          .eq('user_id', userId)
          .eq('memory_type', 'long_term')
          .order('created_at', { ascending: false })
          .limit(20);

        if (longTermError) {
          logger.warn('Failed to retrieve long-term memories', { 
            error: longTermError.message 
          });
        } else if (longTermMemories && longTermMemories.length > 0) {
          context.longTermMemory = longTermMemories;
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

    logger.info('💾 Storing execution in memory', {
      conversationId,
      userId,
      hasAgentResults: !!agentResults,
      hasSummary: !!agentResults?.summary
    });

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
    if (!this.supabase) {
      logger.warn('⚠️ Supabase not available, skipping persistent memory storage');
      return;
    }
    
    if (!this.healthy) {
      logger.warn('⚠️ MemoryService not healthy, skipping persistent memory storage');
      return;
    }

    // Store conversation history
    // Generate unique ID for each conversation turn (conversationId + timestamp)
    try {
      const turnId = `${conversationId}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
      const { error: convError } = await this.supabase
        .from('conversations')
        .insert({
          id: turnId,
          user_id: userId,
          message: query,
          intent: intent?.intent || 'GENERAL',
          response: agentResults?.summary ? JSON.stringify(agentResults.summary) : null,
          created_at: new Date().toISOString()
        });

      if (convError) {
        logger.warn('Failed to store conversation in Supabase', { 
          error: convError.message,
          code: convError.code,
          details: convError.details
        });
      } else {
        logger.info('✅ Conversation stored in Supabase', { conversationId });
      }
    } catch (error) {
      logger.warn('Failed to store execution in Supabase', { error: error.message });
    }

    // ALWAYS store short-term memory first, then promote if needed
    try {
      // Extract synthesized answer or agent outputs
      const synthesized =
        agentResults?.summary?.synthesizedAnswer ||
        agentResults?.summary?.outputs?.map?.((o) => o?.output)?.filter(Boolean)?.join('\n\n') ||
        agentResults?.results?.map?.((r) => r?.result?.output)?.filter(Boolean)?.join('\n\n') ||
        query;

      // ALWAYS store as short-term memory first (for every query)
      const shortTermMetadata = {
        conversationId,
        query,
        intent: intent?.intent || 'GENERAL',
        agentsInvolved: agentResults?.summary?.agentsInvolved ?? agentResults?.agents?.length ?? 0,
        successCount: agentResults?.summary?.successCount ?? 0,
        failureCount: agentResults?.summary?.failureCount ?? 0,
        timestamp: new Date().toISOString()
      };

      // Store short-term memory
      const { error: shortTermError, data: shortTermData } = await this.supabase
        .from('knowledge_base')
        .insert({
          user_id: userId,
          conversation_id: conversationId,
          memory_type: 'short_term',
          content: synthesized || query,
          metadata: shortTermMetadata
        })
        .select();

      if (shortTermError) {
        logger.error('❌ Failed to persist short-term memory to knowledge_base', { 
          error: shortTermError.message,
          code: shortTermError.code,
          details: shortTermError.details,
          hint: shortTermError.hint,
          userId,
          conversationId
        });
      } else {
        logger.info('✅ Short-term memory persisted to knowledge_base', { 
          id: shortTermData?.[0]?.id,
          userId,
          conversationId
        });
      }

      // Determine if this should ALSO be promoted to long-term memory
      // Criteria: High success rate, multiple agents involved, or important intent
      const shouldPromoteToLongTerm = 
        (agentResults?.summary?.successCount ?? 0) > 0 &&
        ((agentResults?.summary?.agentsInvolved ?? (agentResults?.agents?.length ?? 0)) >= 2 || 
         intent?.intent === 'DECISION' || 
         intent?.intent === 'ANALYSIS');

      if (!shouldPromoteToLongTerm) {
        return; // Only short-term stored, we're done
      }

      // Also store as long-term memory if criteria met
      const longTermMetadata = {
        ...shortTermMetadata,
        promotedAt: new Date().toISOString(),
        reason: 'High success rate or important intent'
      };

      const { error: longTermError, data: longTermData } = await this.supabase
        .from('knowledge_base')
        .insert({
          user_id: userId,
          conversation_id: conversationId,
          memory_type: 'long_term',
          content: synthesized || query,
          metadata: longTermMetadata
        })
        .select();

      if (longTermError) {
        logger.error('❌ Failed to persist long-term memory to knowledge_base', { 
          error: longTermError.message,
          code: longTermError.code,
          details: longTermError.details,
          hint: longTermError.hint,
          userId,
          conversationId
        });
      } else {
        logger.info('🧠 Long-term memory persisted to knowledge_base', { 
          id: longTermData?.[0]?.id,
          userId,
          conversationId
        });
      }
    } catch (error) {
      logger.error('Exception while persisting memory', { 
        error: error.message,
        stack: error.stack 
      });
    }
  }

  /**
   * Clear working memory for a conversation
   */
  clearWorkingMemory(conversationId) {
    this.workingMemory.delete(conversationId);
  }

  /**
   * Cleanup old short-term memories (keep only last 50 per user)
   * This should be called periodically or on demand
   */
  async cleanupOldShortTermMemories(userId, keepCount = 50) {
    if (!this.supabase) {
      return;
    }

    try {
      // Get all short-term memories for user, ordered by date
      const { data: allMemories } = await this.supabase
        .from('knowledge_base')
        .select('id')
        .eq('user_id', userId)
        .eq('memory_type', 'short_term')
        .order('created_at', { ascending: false });

      if (allMemories && allMemories.length > keepCount) {
        // Get IDs to delete (everything after keepCount)
        const idsToDelete = allMemories.slice(keepCount).map(m => m.id);

        if (idsToDelete.length > 0) {
          const { error } = await this.supabase
            .from('knowledge_base')
            .delete()
            .in('id', idsToDelete);

          if (error) {
            logger.warn('Failed to cleanup old short-term memories', { 
              error: error.message 
            });
          } else {
            logger.info('🧹 Cleaned up old short-term memories', { 
              deleted: idsToDelete.length,
              userId 
            });
          }
        }
      }
    } catch (error) {
      logger.warn('Exception during memory cleanup', { error: error.message });
    }
  }
}

