/**
 * Prompt Service
 * Loads AI prompts from Supabase database
 * Falls back to hardcoded defaults if database unavailable
 */

import { createClient } from '@supabase/supabase-js';
import config from '../config/index.js';
import { logger } from '../utils/logger.js';

export default class PromptService {
  constructor() {
    this.supabase = null;
    this.promptCache = new Map(); // Cache prompts in memory
    this.healthy = false;
  }

  async initialize() {
    if (!config.supabase.enabled) {
      logger.warn('Supabase not configured, PromptService will use hardcoded defaults');
      return;
    }

    try {
      this.supabase = createClient(
        config.supabase.url,
        config.supabase.serviceRoleKey || config.supabase.anonKey
      );
      
      this.healthy = true;
      logger.info('✅ PromptService initialized');
    } catch (error) {
      logger.error('❌ PromptService initialization failed', { error: error.message });
      this.healthy = false;
    }
  }

  isHealthy() {
    return this.healthy;
  }

  /**
   * Get prompt from Supabase database
   * @param {string} promptName - Name of the prompt (e.g., 'conversation_creator')
   * @returns {Promise<object>} Prompt object with content and metadata
   */
  async getPrompt(promptName) {
    // Check cache first
    if (this.promptCache.has(promptName)) {
      logger.info('📦 Using cached prompt', { promptName });
      return this.promptCache.get(promptName);
    }

    // Try loading from database
    if (this.supabase) {
      try {
        const { data, error } = await this.supabase
          .from('ai_prompts')
          .select('*')
          .eq('name', promptName)
          .single();

        if (!error && data) {
          logger.info('✅ Loaded prompt from database', { promptName });
          
          // Cache for future use
          this.promptCache.set(promptName, data);
          
          return data;
        } else {
          logger.warn('⚠️ Prompt not found in database', { 
            promptName, 
            error: error?.message 
          });
        }
      } catch (error) {
        logger.error('❌ Error loading prompt from database', { 
          promptName, 
          error: error.message 
        });
      }
    }

    // Fallback to hardcoded defaults
    logger.info('📋 Using hardcoded prompt', { promptName });
    return this.getDefaultPrompt(promptName);
  }

  /**
   * Populate prompt template with variables
   * @param {string} template - Prompt template with {{variable}} placeholders
   * @param {object} variables - Key-value pairs to substitute
   * @returns {string} Populated prompt
   */
  populatePrompt(template, variables) {
    if (!template || typeof template !== 'string') {
      return template;
    }

    // Replace {{variable}} with values from variables object
    return template.replace(/\{\{\s*(\w+)\s*\}\}/g, (match, key) => {
      if (key in variables) {
        return String(variables[key]);
      }
      logger.warn('⚠️ Variable not found in prompt template', { key });
      return match; // Keep original if not found
    });
  }

  /**
   * Get default prompt (ERROR - prompts MUST be in database)
   * NO HARDCODED DEFAULTS - This enforces database-driven prompts
   */
  getDefaultPrompt(promptName) {
    logger.error(`❌ Prompt "${promptName}" not found in database and NO hardcoded fallback available`);
    logger.error('   Please add this prompt to Supabase ai_prompts table');
    
    // Return minimal error prompt
    return {
      name: promptName,
      content: `ERROR: Prompt "${promptName}" not found in database. Please configure prompts in Supabase ai_prompts table.`,
      metadata: {
        model: 'gpt-4-turbo-preview',
        temperature: 0.7,
        max_tokens: 1000,
        error: true
      }
    };
  }

  /**
   * Clear prompt cache (useful when prompts are updated in database)
   */
  clearCache() {
    this.promptCache.clear();
    logger.info('🗑️ Prompt cache cleared');
  }

  /**
   * Preload commonly used prompts into cache
   */
  async preloadPrompts(promptNames = ['intent_classifier', 'conversation_creator']) {
    logger.info('📥 Preloading prompts', { count: promptNames.length });
    
    const promises = promptNames.map(name => this.getPrompt(name));
    await Promise.all(promises);
    
    logger.info('✅ Prompts preloaded', { count: this.promptCache.size });
  }
}

