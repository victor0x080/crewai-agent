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
        
        // Calculate detailed relevance based on multiple factors (more lenient scoring)
        const templatesWithRelevance = keywordResults.map(t => {
          const relevanceBreakdown = {
            base: 0.55, // Base relevance (increased - templates found in search get higher base)
            searchMatch: 0.1, // Bonus for being found in keyword search
            intentMatch: 0,
            nameMatch: 0,
            descriptionMatch: 0,
            domainMatch: 0,
            keywordDensity: 0,
            exactPhraseMatch: 0
          };
          
          const templateName = (t.name || '').toLowerCase();
          const templateDesc = (t.description || '').toLowerCase();
          const templateDomain = (t.domain || 'general').toLowerCase();
          const intentLower = intent.toLowerCase();
          const msgLower = message.toLowerCase();
          
          // Factor 1: Intent match in template name (0-0.2) - more lenient
          if (templateName.includes(intentLower)) {
            // Exact match gets full score
            if (templateName === intentLower || templateName.startsWith(intentLower + ' ') || templateName.endsWith(' ' + intentLower)) {
              relevanceBreakdown.intentMatch = 0.2;
            } else {
              // Partial match gets partial score
              relevanceBreakdown.intentMatch = 0.12;
            }
          } else {
            // Even if intent doesn't match exactly, check for similar words
            const intentWords = intentLower.split(/[\s\-_]+/);
            const nameWords = templateName.split(/[\s\-_]+/);
            const intentInName = intentWords.some(iw => nameWords.some(nw => nw.includes(iw) || iw.includes(nw)));
            if (intentInName) {
              relevanceBreakdown.intentMatch = 0.08;
            }
          }
          
          // Factor 2: Name keyword matching (0-0.18) - more generous
          const nameWords = templateName.split(/[\s\-_]+/).filter(w => w.length > 2);
          const msgWords = msgLower.split(/[\s\-_]+/).filter(w => w.length > 2);
          const nameMatches = msgWords.filter(word => nameWords.some(nw => nw.includes(word) || word.includes(nw))).length;
          if (nameMatches > 0) {
            // More generous scoring: 0.04 per match instead of 0.03
            relevanceBreakdown.nameMatch = Math.min(nameMatches * 0.04, 0.18);
          }
          
          // Factor 3: Description keyword matching (0-0.25) - more generous
          const descWords = templateDesc.split(/[\s\-_]+/).filter(w => w.length > 2);
          const descMatches = msgWords.filter(word => descWords.some(dw => dw.includes(word) || word.includes(dw))).length;
          if (descMatches > 0) {
            // More generous: use absolute count with higher multiplier
            const matchScore = Math.min(descMatches * 0.05, 0.25);
            // Also add ratio-based bonus
            const matchRatio = descMatches / Math.max(msgWords.length, 1);
            const ratioBonus = Math.min(matchRatio * 0.1, 0.1);
            relevanceBreakdown.descriptionMatch = Math.min(matchScore + ratioBonus, 0.25);
          }
          
          // Factor 4: Domain matching (0-0.12) - more generous
          // Check if query keywords suggest a specific domain
          const domainKeywords = {
            'marketing': ['campaign', 'advertising', 'promotion', 'marketing', 'budget', 'ad', 'ads'],
            'supply_chain': ['inventory', 'supply', 'demand', 'forecast', 'stock', 'replenishment', 'warehouse'],
            'sales': ['sales', 'pipeline', 'revenue', 'customer', 'deal', 'opportunity'],
            'analytics': ['analysis', 'insight', 'data', 'report', 'metric', 'trend', 'analytics'],
            'pricing': ['price', 'pricing', 'cost', 'revenue', 'margin', 'discount']
          };
          
          for (const [domain, keywords] of Object.entries(domainKeywords)) {
            if (templateDomain === domain) {
              const domainMatchCount = keywords.filter(kw => msgLower.includes(kw)).length;
              if (domainMatchCount > 0) {
                // More generous: 0.03 per match instead of 0.02
                relevanceBreakdown.domainMatch = Math.min(domainMatchCount * 0.03, 0.12);
              }
            }
          }
          
          // Factor 5: Keyword density (0-0.15) - more generous
          // How many important keywords from the message appear in template
          const importantKeywords = ['forecast', 'demand', 'simulation', 'scenario', 'analysis', 
                                    'optimization', 'planning', 'strategy', 'evaluation', 'assessment',
                                    'roi', 'performance', 'trend', 'insight', 'report'];
          const foundKeywords = importantKeywords.filter(kw => 
            msgLower.includes(kw) && (templateName.includes(kw) || templateDesc.includes(kw))
          ).length;
          if (foundKeywords > 0) {
            // More generous: 0.03 per keyword instead of 0.02
            relevanceBreakdown.keywordDensity = Math.min(foundKeywords * 0.03, 0.15);
          }
          
          // Factor 6: Exact phrase matching (0-0.12) - more generous
          // Check for 2-3 word phrases from message in template
          const msgPhrases = [];
          for (let i = 0; i < msgWords.length - 1; i++) {
            msgPhrases.push(msgWords.slice(i, i + 2).join(' '));
          }
          for (let i = 0; i < msgWords.length - 2; i++) {
            msgPhrases.push(msgWords.slice(i, i + 3).join(' '));
          }
          
          const phraseMatches = msgPhrases.filter(phrase => 
            templateName.includes(phrase) || templateDesc.includes(phrase)
          ).length;
          if (phraseMatches > 0) {
            // More generous: 0.04 per phrase instead of 0.03
            relevanceBreakdown.exactPhraseMatch = Math.min(phraseMatches * 0.04, 0.12);
          }
          
          // Calculate total relevance (sum of all factors, capped at 1.0)
          const totalRelevance = Math.min(
            Object.values(relevanceBreakdown).reduce((sum, val) => sum + val, 0),
            1.0
          );
          
          // Round to 3 decimal places for precision
          const finalRelevance = Math.round(totalRelevance * 1000) / 1000;
          
          return {
            id: t.id,
            name: t.name,
            description: t.description,
            domain: t.domain || 'general',
            relevance: finalRelevance,
            relevanceBreakdown: {
              base: Math.round(relevanceBreakdown.base * 1000) / 1000,
              searchMatch: Math.round(relevanceBreakdown.searchMatch * 1000) / 1000,
              intentMatch: Math.round(relevanceBreakdown.intentMatch * 1000) / 1000,
              nameMatch: Math.round(relevanceBreakdown.nameMatch * 1000) / 1000,
              descriptionMatch: Math.round(relevanceBreakdown.descriptionMatch * 1000) / 1000,
              domainMatch: Math.round(relevanceBreakdown.domainMatch * 1000) / 1000,
              keywordDensity: Math.round(relevanceBreakdown.keywordDensity * 1000) / 1000,
              exactPhraseMatch: Math.round(relevanceBreakdown.exactPhraseMatch * 1000) / 1000,
              total: finalRelevance
            },
            schema: t.template_schema || {},
            source: 'keyword_search'
          };
        });
        
        // Sort by relevance
        templatesWithRelevance.sort((a, b) => b.relevance - a.relevance);

        // Enforce strict minimum relevance (default 0.72)
        const minRelevance = 0.72;
        const filtered = templatesWithRelevance.filter(t => t.relevance >= minRelevance);
        logger.info('🎯 Applying relevance threshold', { minRelevance, before: templatesWithRelevance.length, after: filtered.length });

        return filtered;
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

