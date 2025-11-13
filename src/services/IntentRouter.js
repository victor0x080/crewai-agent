/**
 * Intent Router Service
 * Classifies user intent using OpenAI GPT-4
 */

import OpenAI from 'openai';
import config from '../config/index.js';
import { logger } from '../utils/logger.js';

export default class IntentRouter {
  constructor(promptService = null) {
    this.openai = null;
    this.promptService = promptService;
    this.healthy = false;
  }

  async initialize() {
    if (!config.openai.enabled) {
      logger.warn('OpenAI not configured, IntentRouter will use fallback classification');
      return;
    }

    try {
      this.openai = new OpenAI({ apiKey: config.openai.apiKey });
      
      // Test the connection
      await this.openai.models.list();
      this.healthy = true;
      
      logger.info('✅ IntentRouter initialized with OpenAI');
    } catch (error) {
      logger.error('❌ IntentRouter initialization failed', { error: error.message });
      this.healthy = false;
    }
  }

  isHealthy() {
    return this.healthy;
  }

  /**
   * Classify user intent using OpenAI GPT-4
   * @param {string} message - User message
   * @param {object} context - Additional context
   * @returns {Promise<object>} Intent classification result
   */
  async classifyIntent(message, context = {}) {
    if (!this.openai) {
      logger.warn('⚠️ OpenAI client not initialized - using fallback');
      logger.warn('   Check IntentRouter initialization logs for OpenAI connection errors');
      return this.getFallbackIntent(message);
    }

    try {
      // Load prompt from database (REQUIRED - no hardcoded fallback)
      if (!this.promptService) {
        logger.error('❌ PromptService not available for IntentRouter');
        return this.getFallbackIntent(message);
      }

      const prompt = await this.promptService.getPrompt('intent_classifier');
      if (!prompt || !prompt.content) {
        logger.error('❌ intent_classifier prompt not found in database');
        return this.getFallbackIntent(message);
      }

      // Check if prompt has error flag
      if (prompt.metadata && prompt.metadata.error) {
        logger.error('❌ Prompt has error flag - likely not properly configured in Supabase');
        return this.getFallbackIntent(message);
      }

      const systemPrompt = prompt.content;
      const promptMetadata = prompt.metadata || {};
      
      logger.info('✅ Using intent_classifier prompt from Supabase', {
        model: promptMetadata.model || config.openai.model,
        hasContent: !!systemPrompt
      });

      const completion = await this.openai.chat.completions.create({
        model: promptMetadata.model || config.openai.model,
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: message }
        ],
        temperature: promptMetadata.temperature || 0.2,
        max_tokens: promptMetadata.max_tokens || 300,
        response_format: { type: 'json_object' }
      });

      const content = completion.choices[0]?.message?.content || '{}';
      const parsed = JSON.parse(content);

      return {
        type: (parsed.category || 'general').replace(/_/g, '-'),
        intent: parsed.intent || 'GENERAL',
        confidence: parsed.confidence || 0.5,
        explanation: `Classified as ${parsed.intent} with ${Math.round((parsed.confidence || 0.5) * 100)}% confidence`,
        keywords: parsed.keywords || [],
        entities: parsed.entities || {},
        category: parsed.category || 'general'
      };

    } catch (error) {
      logger.error('❌ Intent classification error', { 
        error: error.message,
        stack: error.stack,
        type: error.constructor.name
      });
      return this.getFallbackIntent(message);
    }
  }

  /**
   * Fallback intent classification using keyword matching
   */
  getFallbackIntent(message) {
    const lower = message.toLowerCase();

    // Simple keyword-based classification
    if (lower.includes('trend') || lower.includes('analysis') || lower.includes('analyze')) {
      return {
        type: 'analysis',
        intent: 'ANALYSIS',
        confidence: 0.6,
        explanation: 'Keyword-based classification (fallback)',
        keywords: ['trend', 'analysis'],
        entities: {},
        category: 'market_analysis'
      };
    }

    if (lower.includes('what') || lower.includes('how') || lower.includes('why')) {
      return {
        type: 'question',
        intent: 'QUESTION',
        confidence: 0.6,
        explanation: 'Keyword-based classification (fallback)',
        keywords: [],
        entities: {},
        category: 'general'
      };
    }

    if (lower.includes('forecast') || lower.includes('predict') || lower.includes('simulate')) {
      return {
        type: 'simulation',
        intent: 'SIMULATION',
        confidence: 0.6,
        explanation: 'Keyword-based classification (fallback)',
        keywords: ['forecast', 'simulate'],
        entities: {},
        category: 'operational_analysis'
      };
    }

    return {
      type: 'general',
      intent: 'GENERAL',
      confidence: 0.5,
      explanation: 'Default fallback classification',
      keywords: [],
      entities: {},
      category: 'general'
    };
  }
}

