/**
 * Problem Type Classifier Service
 * Classifies executive queries into problem types for problem-first conversational workflow
 * 
 * Problem types:
 * - alert: "alert me if there is a risk"
 * - understand: "help me understand this situation"
 * - solve: "solve this problem"
 * - monitor: "monitor this situation"
 * - automate: "automate this process"
 */

import OpenAI from 'openai';
import config from '../config/index.js';
import { logger } from '../utils/logger.js';

export default class ProblemTypeClassifier {
  constructor() {
    this.openai = null;
    this.healthy = false;
  }

  async initialize() {
    if (!config.openai.enabled) {
      logger.warn('OpenAI not configured, ProblemTypeClassifier will use fallback classification');
      return;
    }

    try {
      this.openai = new OpenAI({ apiKey: config.openai.apiKey });
      
      // Test the connection
      await this.openai.models.list();
      this.healthy = true;
      
      logger.info('✅ ProblemTypeClassifier initialized with OpenAI');
    } catch (error) {
      logger.error('❌ ProblemTypeClassifier initialization failed', { error: error.message });
      this.healthy = false;
    }
  }

  isHealthy() {
    return this.healthy;
  }

  /**
   * Classify the problem type from user query
   * @param {string} query - User query
   * @param {object} context - Additional context (conversation history, datasource, etc.)
   * @returns {Promise<object>} Problem type classification result
   */
  async classifyProblemType(query, context = {}) {
    // Store query for use in determineWorkflowStage
    this._currentQuery = query;
    if (!this.openai) {
      logger.warn('⚠️ OpenAI client not initialized - using fallback');
      return this.getFallbackProblemType(query);
    }

    try {
      const systemPrompt = `You are a problem type classifier for a business executive conversational interface.

The system operates on a problem-first approach. Executives always start with a specific problem type, not open-ended questions.

Classify the user's query into one of these problem types:

1. **alert** - User wants to be alerted about risks, issues, or anomalies
   Examples: "alert me if there is a risk", "notify me when sales drop", "warn me about inventory issues"

2. **understand** - User wants to understand a situation, analyze data, or get insights
   Examples: "help me understand this situation", "what's happening with sales", "explain this trend"

3. **solve** - User wants to solve a specific problem or make a decision
   Examples: "solve this problem", "how do I fix this", "what should I do about this"

4. **monitor** - User wants to monitor a situation, track metrics, or watch for changes
   Examples: "monitor this situation", "track these metrics", "watch for changes in demand"

5. **automate** - User wants to automate a process or workflow
   Examples: "automate this process", "set up automation for", "create a workflow for"

6. **general** - General questions that don't fit the above categories (fallback)
   Examples: "what is X", "tell me about Y", general knowledge questions

IMPORTANT:
- The system always starts with a narrowly defined problem space
- Even if the query seems general, try to classify it into one of the problem types
- If truly general (knowledge questions), use "general"
- Consider the conversation context when available

Return a JSON object with:
{
  "problemType": "alert" | "understand" | "solve" | "monitor" | "automate" | "general",
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation",
  "problemSpace": "narrowly defined problem space description",
  "workflowStage": "interpret" | "recommend" | "what-if" | "full-llm" | null
}`;

      const conversationContext = context.conversationHistory 
        ? `\n\nPrevious conversation context:\n${JSON.stringify(context.conversationHistory.slice(-3), null, 2)}`
        : '';

      const completion = await this.openai.chat.completions.create({
        model: config.openai.model,
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: `${query}${conversationContext}` }
        ],
        temperature: 0.2,
        max_tokens: 300,
        response_format: { type: 'json_object' }
      });

      const content = completion.choices[0]?.message?.content || '{}';
      const parsed = JSON.parse(content);

      // Determine workflow stage based on problem type, conversation history, and datasource
      const workflowStage = this.determineWorkflowStage(
        parsed.problemType,
        context.conversationHistory || [],
        this._currentQuery || query,
        parsed.problemSpace, // Keep for backward compatibility, but not used for workflow determination
        context.datasource || null // Pass datasource from datacube to check if interpretation is needed
      );

      return {
        problemType: parsed.problemType || 'general',
        confidence: parsed.confidence || 0.5,
        reasoning: parsed.reasoning || 'Classification completed',
        problemSpace: parsed.problemSpace || query,
        workflowStage: workflowStage || parsed.workflowStage || 'interpret',
        keywords: this.extractKeywords(query, parsed.problemType)
      };

    } catch (error) {
      logger.error('❌ Problem type classification error', { 
        error: error.message,
        stack: error.stack
      });
      return this.getFallbackProblemType(query);
    }
  }

  /**
   * Determine workflow stage based on problem type and conversation history
   * Workflow: interpret → recommend → what-if → full-llm
   * 
   * Note: For setup/configuration queries (alert, monitor, automate):
   * - If there's a datasource from datacube to interpret → start at "interpret" to understand the data first
   * - If there's NO datasource → start at "full-llm" to configure without interpretation
   */
  determineWorkflowStage(problemType, conversationHistory = [], query = '', problemSpace = null, datasource = null) {
    // Check if this is a setup/configuration query
    const isSetupQuery = this.isSetupQuery(problemType, query);
    
    // Check if there's a datasource from datacube (instead of problem space)
    const hasDatasource = datasource && 
                         (Array.isArray(datasource) ? datasource.length > 0 : 
                          typeof datasource === 'object' ? Object.keys(datasource).length > 0 : 
                          !!datasource);
    
    // If no history and it's a setup query
    if ((!conversationHistory || conversationHistory.length === 0) && isSetupQuery) {
      // If there's a datasource from datacube, interpret it first before setting up
      if (hasDatasource) {
        return 'interpret';
      }
      // If no datasource, use full-llm to configure
      return 'full-llm';
    }
    
    // If no history and not a setup query, start at interpret stage
    if (!conversationHistory || conversationHistory.length === 0) {
      return 'interpret';
    }

    // Count stages in conversation history
    const stages = conversationHistory
      .map(msg => msg.workflowStage || msg.metadata?.workflowStage)
      .filter(Boolean);

    const lastStage = stages[stages.length - 1] || 'interpret';

    // If current query is a setup query
    if (isSetupQuery) {
      // If there's a datasource from datacube, interpret it first to understand the data before configuring
      if (hasDatasource) {
        return 'interpret';
      }
      // If no datasource, use full-llm to configure
      return 'full-llm';
    }

    // Determine next stage based on problem type and current stage
    const stageProgression = {
      'interpret': 'recommend',
      'recommend': 'what-if',
      'what-if': 'full-llm',
      'full-llm': 'full-llm' // Stay at full-llm once reached
    };

    // For certain problem types, skip stages
    if (problemType === 'alert' || problemType === 'monitor') {
      // Alerts and monitoring typically go: interpret → full-llm (skip recommend/what-if)
      // But if starting fresh with a setup query, already at full-llm
      if (lastStage === 'interpret') {
        return 'full-llm';
      }
    }

    if (problemType === 'automate') {
      // Automation typically needs: interpret → recommend → full-llm
      if (lastStage === 'recommend') {
        return 'full-llm';
      }
    }

    // Default progression
    return stageProgression[lastStage] || 'interpret';
  }

  /**
   * Check if query is a setup/configuration query (no data to interpret yet)
   * Setup queries need full-llm stage, not interpret stage
   */
  isSetupQuery(problemType, query = '') {
    const lower = query.toLowerCase();
    
    // Alert and monitor queries that are setup tasks
    if (problemType === 'alert' || problemType === 'monitor') {
      // Setup patterns: "alert me if", "notify me when", "monitor", "track", "watch"
      const setupPatterns = [
        'alert me', 'notify me', 'warn me', 'tell me when',
        'monitor', 'track', 'watch', 'keep an eye on',
        'set up', 'configure', 'create alert', 'setup'
      ];
      return setupPatterns.some(pattern => lower.includes(pattern));
    }
    
    // Automate queries are typically setup tasks
    if (problemType === 'automate') {
      return true; // Automation is always a setup task
    }
    
    // Understand and solve queries typically have data to interpret
    // unless they're asking "how to" or "what is" (setup/explanation)
    if (problemType === 'understand' || problemType === 'solve') {
      const setupPatterns = ['how to', 'what is', 'how do i', 'how can i'];
      return setupPatterns.some(pattern => lower.includes(pattern));
    }
    
    return false;
  }

  /**
   * Extract keywords from query based on problem type
   */
  extractKeywords(query, problemType) {
    const lower = query.toLowerCase();
    const keywords = [];

    // Problem type specific keywords
    const typeKeywords = {
      alert: ['alert', 'warn', 'notify', 'risk', 'issue', 'problem', 'anomaly'],
      understand: ['understand', 'explain', 'analyze', 'what', 'why', 'how', 'insight'],
      solve: ['solve', 'fix', 'resolve', 'address', 'handle', 'deal with'],
      monitor: ['monitor', 'track', 'watch', 'observe', 'follow', 'keep an eye on'],
      automate: ['automate', 'automatic', 'workflow', 'process', 'routine', 'schedule']
    };

    const relevantKeywords = typeKeywords[problemType] || [];
    relevantKeywords.forEach(keyword => {
      if (lower.includes(keyword)) {
        keywords.push(keyword);
      }
    });

    return keywords;
  }

  /**
   * Fallback problem type classification using keyword matching
   */
  getFallbackProblemType(query) {
    const lower = query.toLowerCase();
    
    // Store query for workflow stage determination
    this._currentQuery = query;

    if (lower.includes('alert') || lower.includes('warn') || lower.includes('notify') || lower.includes('risk')) {
      const isSetup = this.isSetupQuery('alert', query);
      return {
        problemType: 'alert',
        confidence: 0.7,
        reasoning: 'Keyword-based classification (fallback)',
        problemSpace: query,
        workflowStage: isSetup ? 'full-llm' : 'interpret',
        keywords: ['alert', 'warn', 'notify', 'risk']
      };
    }

    if (lower.includes('understand') || lower.includes('explain') || lower.includes('what') || lower.includes('why') || lower.includes('how')) {
      return {
        problemType: 'understand',
        confidence: 0.7,
        reasoning: 'Keyword-based classification (fallback)',
        problemSpace: query,
        workflowStage: 'interpret',
        keywords: ['understand', 'explain']
      };
    }

    if (lower.includes('solve') || lower.includes('fix') || lower.includes('resolve')) {
      return {
        problemType: 'solve',
        confidence: 0.7,
        reasoning: 'Keyword-based classification (fallback)',
        problemSpace: query,
        workflowStage: 'interpret',
        keywords: ['solve', 'fix']
      };
    }

    if (lower.includes('monitor') || lower.includes('track') || lower.includes('watch')) {
      const isSetup = this.isSetupQuery('monitor', query);
      return {
        problemType: 'monitor',
        confidence: 0.7,
        reasoning: 'Keyword-based classification (fallback)',
        problemSpace: query,
        workflowStage: isSetup ? 'full-llm' : 'interpret',
        keywords: ['monitor', 'track']
      };
    }

    if (lower.includes('automate') || lower.includes('automatic') || lower.includes('workflow')) {
      // Automation is always a setup task
      return {
        problemType: 'automate',
        confidence: 0.7,
        reasoning: 'Keyword-based classification (fallback)',
        problemSpace: query,
        workflowStage: 'full-llm', // Automation is always setup
        keywords: ['automate']
      };
    }

    return {
      problemType: 'general',
      confidence: 0.5,
      reasoning: 'Default fallback classification',
      problemSpace: query,
      workflowStage: 'interpret',
      keywords: []
    };
  }
}

