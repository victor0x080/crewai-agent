/**
 * Template Engine Service
 * Discovers and executes workflow templates from Supabase
 */

import { createClient } from '@supabase/supabase-js';
import config from '../config/index.js';
import { logger } from '../utils/logger.js';

export default class TemplateEngine {
  constructor() {
    this.supabase = null;
    this.healthy = false;
  }

  async initialize() {
    if (!config.supabase.enabled) {
      logger.warn('Supabase not configured, TemplateEngine will return empty templates');
      return;
    }

    try {
      this.supabase = createClient(
        config.supabase.url,
        config.supabase.serviceRoleKey || config.supabase.anonKey
      );
      
      // Test connection
      const { data, error } = await this.supabase
        .from('workflow_templates')
        .select('id')
        .limit(1);
      
      if (error && error.code !== 'PGRST116') { // PGRST116 = table not found
        throw error;
      }
      
      this.healthy = true;
      logger.info('✅ TemplateEngine initialized with Supabase');
    } catch (error) {
      logger.error('❌ TemplateEngine initialization failed', { error: error.message });
      this.healthy = false;
    }
  }

  isHealthy() {
    return this.healthy;
  }

  /**
   * Discover relevant templates based on intent and query
   * @param {string} message - User message
   * @param {string} intent - Classified intent
   * @param {object} memoryContext - Memory context
   * @returns {Promise<Array>} Discovered templates
   */
  async discoverTemplates(message, intent, memoryContext = {}) {
    if (!this.supabase) {
      return this.getFallbackTemplates(intent);
    }

    try {
      // PRIMARY: Keyword and description search (works without pgvector)
      logger.info('🔍 Searching templates', { intent, message: message.substring(0, 50) });
      
      // Extract keywords from message for better matching
      const keywords = message.toLowerCase();
      const keywordCandidates = ['forecast','demand','simulation','scenario','sales','revenue','inventory','pricing','market','analysis','planning','optimization'];
      const msgWords = Array.from(new Set(keywords.split(/[^a-z0-9]+/i).filter(w => w.length > 3)));
      const matchedTokens = keywordCandidates.filter(tok => msgWords.includes(tok));
      
      // Build safe OR clauses: intent match + token matches in name/description
      const orClauses = [`name.ilike.%${intent}%`];
      matchedTokens.forEach(tok => {
        orClauses.push(`description.ilike.%${tok}%`);
        orClauses.push(`name.ilike.%${tok}%`);
      });
      // Always include a couple of general terms if none matched
      if (matchedTokens.length === 0) {
        orClauses.push('description.ilike.%analysis%');
        orClauses.push('description.ilike.%insight%');
      }

      const orFilter = orClauses.join(',');

      logger.info('📝 Template search params', { intent, matchedTokens, orFilter });
      
      // Note: Avoid JSON path filter inside .or() due to PostgREST parser limits.
      // We rely on name/description matching which is sufficient for our templates.
      const { data: keywordResults, error: keywordError } = await this.supabase
        .from('workflow_templates')
        .select('*')
        .or(orFilter)
        .limit(5);

      if (keywordError) {
        logger.error('❌ Keyword search failed', { error: keywordError.message, details: keywordError });
      }

      logger.info('📊 Template search results', { 
        found: keywordResults?.length || 0, 
        templates: keywordResults?.map(t => ({ id: t.id, name: t.name })) || []
      });

      if (keywordResults && keywordResults.length > 0) {
        logger.info('✅ Found templates via keyword search', { count: keywordResults.length });
        
        // Calculate relevance based on keyword matches
        const templatesWithRelevance = keywordResults.map(t => {
          let relevance = 0.5; // Base relevance
          
          // Boost if intent matches
          if (t.name?.toLowerCase().includes(intent.toLowerCase())) {
            relevance += 0.2;
          }
          
          // Boost if message keywords match description
          const descLower = (t.description || '').toLowerCase();
          const msgWords = keywords.split(' ').filter(w => w.length > 3);
          const matchCount = msgWords.filter(word => descLower.includes(word)).length;
          relevance += Math.min(matchCount * 0.05, 0.3);
          
          return {
            id: t.id,
            name: t.name,
            description: t.description,
            domain: t.domain || 'general',
            relevance: Math.min(relevance, 1.0),
            schema: t.template_schema || {},
            source: 'keyword_search'
          };
        });
        
        // Sort by relevance
        templatesWithRelevance.sort((a, b) => b.relevance - a.relevance);
        
        return templatesWithRelevance;
      }

      // FALLBACK: No templates found in database
      logger.warn('⚠️ No templates found in Supabase, using fallback', { intent });
      return this.getFallbackTemplates(intent);

    } catch (error) {
      logger.error('Template discovery error', { error: error.message });
      return this.getFallbackTemplates(intent);
    }
  }

  /**
   * Fallback templates when database is unavailable
   */
  getFallbackTemplates(intent) {
    const fallbackTemplates = {
      ANALYSIS: {
        id: 'fallback-analysis',
        name: 'General Analysis Template',
        description: 'Generic analysis workflow',
        domain: 'general',
        relevance: 0.5,
        schema: {
          agents: ['SDA', 'CAA', 'ASA'],
          steps: ['data_retrieval', 'analysis', 'synthesis']
        },
        source: 'fallback'
      },
      SIMULATION: {
        id: 'fallback-simulation',
        name: 'Scenario Simulation Template',
        description: 'What-if scenario analysis',
        domain: 'simulation',
        relevance: 0.5,
        schema: {
          // Keep fallback minimal to avoid latency and 429s; templates can expand
          agents: ['SSA'],
          steps: ['scenario_setup', 'simulation']
        },
        source: 'fallback'
      },
      QUESTION: {
        id: 'fallback-question',
        name: 'Q&A Template',
        description: 'Information retrieval workflow',
        domain: 'general',
        relevance: 0.5,
        schema: {
          agents: ['FQA', 'ASA'],
          steps: ['query', 'answer']
        },
        source: 'fallback'
      }
    };

    const template = fallbackTemplates[intent] || fallbackTemplates.QUESTION;
    return [template];
  }
}

