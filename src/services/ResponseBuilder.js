/**
 * Response Builder Service
 * Constructs TurnEnvelope responses in ACT-R compatible format
 */

import { logger } from '../utils/logger.js';
import OpenAI from 'openai';
import config from '../config/index.js';

export default class ResponseBuilder {
  constructor(promptService = null) {
    this.promptService = promptService;
    this.healthy = true;
    this.openai = null;
    
    // Initialize OpenAI client if API key is available
    if (config.openai.enabled && config.openai.apiKey) {
      this.openai = new OpenAI({
        apiKey: config.openai.apiKey
      });
    }
  }

  async initialize() {
    logger.info('✅ ResponseBuilder initialized');
  }

  isHealthy() {
    return this.healthy;
  }

  /**
   * Build response with optional agent results
   */
  async buildResponse({ query, intent, templates, memoryContext, requestId, conversationId, agentResults }) {
    // If agent results are available, build answer from them
    let ack = this.buildAcknowledgment(query, intent, templates);
    let answer = null;
    let conversationalResponse = null;
    
    if (agentResults && !agentResults.timeout && !agentResults.error) {
      logger.info('📊 Building answer from agent results', {
        hasResults: !!agentResults.results,
        resultsCount: agentResults.results?.length || 0,
        hasSummary: !!agentResults.summary,
        summaryKeys: agentResults.summary ? Object.keys(agentResults.summary) : []
      });
      
      // Build actual answer from agent results
      const successfulResults = agentResults.results?.filter(r => r.success) || [];
      if (successfulResults.length > 0) {
        answer = this.buildAnswerFromResults(query, intent, successfulResults, agentResults.summary);
        ack = answer; // Use the answer as acknowledgment
        logger.info('✅ Built answer from successful results', { answerLength: answer?.length || 0 });
      } else if (agentResults.summary) {
        // Try to get answer from summary
        let rawAnswer = agentResults.summary.synthesizedAnswer || 
                 agentResults.summary.answer || 
                 agentResults.summary.summary ||
                 null;
        
        // Helper to extract readable text from potentially JSON-encoded strings
        const extractReadableText = (text) => {
          if (!text) return null;
          if (typeof text !== 'string') return String(text);
          
          // Try to parse as JSON if it looks like JSON
          if (text.trim().startsWith('{') || text.trim().startsWith('[')) {
            try {
              const parsed = JSON.parse(text);
              // If parsed object has 'output' field, extract it
              if (parsed && typeof parsed === 'object' && parsed.output && typeof parsed.output === 'string') {
                return parsed.output;
              }
              // If it's just a string in JSON, return it
              if (typeof parsed === 'string') {
                return parsed;
              }
            } catch (e) {
              // Not valid JSON, return as-is
            }
          }
          return text;
        };
        
        answer = extractReadableText(rawAnswer);
        if (answer) {
          ack = answer;
          logger.info('✅ Built answer from summary', { answerLength: answer.length });
        } else {
          logger.warn('⚠️ Summary exists but no answer found', { summaryKeys: Object.keys(agentResults.summary) });
        }
      } else {
        logger.warn('⚠️ Agent results exist but no successful results or summary');
      }
    } else if (agentResults) {
      logger.warn('⚠️ Agent results have error or timeout', { 
        timeout: agentResults.timeout, 
        error: agentResults.error 
      });
    }
    
    // Generate conversational response using OpenAI if available
    try {
      conversationalResponse = await this.generateConversationalResponse({
        query,
        intent,
        templates,
        memoryContext,
        agentResults,
        rawAnswer: answer || ack
      });
    } catch (error) {
      logger.warn('⚠️ Failed to generate conversational response, using fallback', { 
        error: error.message 
      });
      conversationalResponse = answer || ack;
    }
    
    // Build declarative plan (what needs to be done)
    const declarativePlan = templates.map(template => ({
      action: `execute_template_${template.id}`,
      templateId: template.id,
      templateName: template.name,
      domain: template.domain,
      relevance: template.relevance,
      direction: 'user_directed'
    }));

    // Build procedural plan (how it will be done)
    const proceduralPlan = templates.flatMap(template => 
      (template.schema?.agents || []).map((agentId, index) => ({
        id: `task-${Date.now()}-${index}`,
        title: `Activate ${agentId} for analysis`,
        service: agentId.toLowerCase(),
        capability: this.mapAgentToCapability(agentId),
        direction: 'system_directed',
        deps: index > 0 ? [`task-${Date.now()}-${index-1}`] : []
      }))
    );

    // Build questions/clarifications if needed
    const ask = this.buildClarifications(query, intent, templates);

    // Construct TurnEnvelope
    const turnEnvelope = {
      ack: answer || ack,
      plan: {
        declarative: declarativePlan,
        procedural: proceduralPlan
      },
      ask,
      memory: {
        workingMemory: memoryContext.workingMemory || [],
        retrieved: memoryContext.shortTermMemory?.length || 0,
        conversationTurns: memoryContext.conversationHistory?.length || 0
      },
      delta: agentResults ? {
        agentResults: agentResults.results || [],
        summary: agentResults.summary || null,
        metrics: agentResults.metrics || null
      } : null,
      decisions: [],
      meta: {
        concepts: this.extractConcepts(query, intent),
        provenance: intent.confidence > 0.7 ? 'OpenAI-GPT4' : 'Fallback',
        processingMode: agentResults ? 'complete_with_results' : 'immediate_response',
        templatesUsed: templates.map(t => t.name)
      }
    };

    // Build full response
    return {
      query,
      intentClassification: intent,
      conversationalResponse: conversationalResponse || answer || ack,
      response: conversationalResponse || answer || ack,
      turnEnvelope,
      agentResults: agentResults ? {
        agents: agentResults.agents || [],
        results: agentResults.results || [],
        summary: agentResults.summary || null,
        metrics: agentResults.metrics || null,
        timeout: agentResults.timeout || false,
        error: agentResults.error || null,
        discovery: agentResults.discovery || null  // Include discovery metadata (confidence scores, dynamic agent info)
      } : null,
      processedAt: new Date().toISOString(),
      requestId,
      conversationId,
      templates: templates.map(t => ({ 
        id: t.id, 
        name: t.name, 
        relevance: t.relevance,
        relevanceBreakdown: t.relevanceBreakdown || null
      }))
    };
  }

  /**
   * Generate conversational response using OpenAI
   * Creates ChatGPT-like natural language responses with conversation context
   */
  async generateConversationalResponse({ query, intent, templates, memoryContext, agentResults, rawAnswer }) {
    // If OpenAI is not available, return raw answer
    if (!this.openai) {
      logger.debug('OpenAI not available, using raw answer');
      return rawAnswer;
    }

    try {
      // Format conversation history for context
      const conversationHistory = this.formatConversationHistory(memoryContext);
      
      // Format agent results for context
      const agentResultsText = this.formatAgentResults(agentResults);
      
      // Build system prompt
      const systemPrompt = `You are a helpful business intelligence assistant. You provide clear, conversational responses to user queries based on data analysis and insights.

Your responses should:
- Be natural and conversational, like ChatGPT
- Reference previous conversation context when relevant
- Incorporate insights from data analysis naturally
- Be concise but informative
- Use a friendly, professional tone
- If agent results are provided, incorporate them naturally into your response
- If no agent results are available yet, acknowledge the query and explain what you're doing`;

      // Build user message with context
      const userMessage = this.buildConversationalPrompt({
        query,
        intent,
        templates,
        conversationHistory,
        agentResultsText,
        rawAnswer
      });

      logger.info('🤖 Generating conversational response with OpenAI', {
        hasHistory: conversationHistory.length > 0,
        hasAgentResults: !!agentResultsText,
        model: config.openai.model
      });

      // Call OpenAI API
      const completion = await this.openai.chat.completions.create({
        model: config.openai.model,
        messages: [
          { role: 'system', content: systemPrompt },
          ...conversationHistory,
          { role: 'user', content: userMessage }
        ],
        temperature: config.openai.temperature,
        max_tokens: config.openai.maxTokens
      });

      const response = completion.choices[0]?.message?.content?.trim();
      
      if (response) {
        logger.info('✅ Generated conversational response', { 
          length: response.length 
        });
        return response;
      } else {
        logger.warn('⚠️ OpenAI returned empty response');
        return rawAnswer;
      }
    } catch (error) {
      logger.error('❌ Error generating conversational response', {
        error: error.message,
        stack: error.stack
      });
      // Fallback to raw answer on error
      return rawAnswer;
    }
  }

  /**
   * Format conversation history for OpenAI messages
   */
  formatConversationHistory(memoryContext) {
    const messages = [];
    
    // Get conversation history from memory context
    const history = memoryContext.conversationHistory || [];
    const workingMemory = memoryContext.workingMemory || [];
    
    // Combine and sort by timestamp
    const allTurns = [
      ...history.map(h => ({
        query: h.message || h.query,
        response: h.response ? (typeof h.response === 'string' ? JSON.parse(h.response) : h.response) : null,
        timestamp: h.created_at || h.timestamp
      })),
      ...workingMemory.map(w => ({
        query: w.query,
        response: w.agentResults,
        timestamp: w.timestamp
      }))
    ].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
    
    // Format last 10 turns as conversation context
    const recentTurns = allTurns.slice(-10);
    
    for (const turn of recentTurns) {
      if (turn.query) {
        messages.push({ role: 'user', content: turn.query });
      }
      if (turn.response) {
        // Extract response text from agent results
        const responseText = this.extractResponseText(turn.response);
        if (responseText) {
          messages.push({ role: 'assistant', content: responseText });
        }
      }
    }
    
    return messages;
  }

  /**
   * Extract readable text from agent results or response object
   */
  extractResponseText(response) {
    if (!response) return null;
    
    if (typeof response === 'string') {
      try {
        const parsed = JSON.parse(response);
        return this.extractResponseText(parsed);
      } catch {
        return response;
      }
    }
    
    if (typeof response === 'object') {
      // Try common fields
      return response.synthesizedAnswer || 
             response.answer || 
             response.summary ||
             response.output ||
             response.ack ||
             null;
    }
    
    return null;
  }

  /**
   * Format agent results for inclusion in prompt
   */
  formatAgentResults(agentResults) {
    if (!agentResults || agentResults.timeout || agentResults.error) {
      return null;
    }

    const parts = [];
    
    if (agentResults.summary?.synthesizedAnswer) {
      parts.push(`Analysis Results:\n${agentResults.summary.synthesizedAnswer}`);
    } else if (agentResults.summary) {
      parts.push(`Summary: ${JSON.stringify(agentResults.summary, null, 2)}`);
    }
    
    if (agentResults.results && agentResults.results.length > 0) {
      const successfulResults = agentResults.results.filter(r => r.success);
      if (successfulResults.length > 0) {
        parts.push(`\nAgent Outputs:\n${successfulResults.map((r, i) => 
          `${i + 1}. ${r.agentName || r.agentId}: ${r.result?.output || r.result?.answer || 'Completed'}`
        ).join('\n')}`);
      }
    }
    
    return parts.length > 0 ? parts.join('\n\n') : null;
  }

  /**
   * Build conversational prompt for OpenAI
   */
  buildConversationalPrompt({ query, intent, templates, conversationHistory, agentResultsText, rawAnswer }) {
    const parts = [];
    
    parts.push(`User Query: ${query}`);
    parts.push(`Intent: ${intent.intent} (confidence: ${(intent.confidence * 100).toFixed(0)}%)`);
    
    if (templates.length > 0) {
      parts.push(`\nRelevant Workflows: ${templates.map(t => t.name).join(', ')}`);
    }
    
    if (agentResultsText) {
      parts.push(`\n${agentResultsText}`);
    } else if (rawAnswer) {
      parts.push(`\nCurrent Response: ${rawAnswer}`);
    }
    
    parts.push(`\nPlease provide a natural, conversational response that:`);
    parts.push(`- Directly addresses the user's query`);
    if (conversationHistory.length > 0) {
      parts.push(`- References previous conversation context naturally`);
    }
    if (agentResultsText) {
      parts.push(`- Incorporates the analysis results in a clear, understandable way`);
    }
    parts.push(`- Maintains a helpful, professional tone`);
    
    return parts.join('\n');
  }

  /**
   * Build answer from agent results
   */
  buildAnswerFromResults(query, intent, successfulResults, summary) {
    if (summary && summary.synthesizedAnswer) {
      return summary.synthesizedAnswer;
    }
    
    if (summary && summary.answer) {
      return summary.answer;
    }
    
    if (summary && summary.summary) {
      return summary.summary;
    }
    
    // Build answer from individual agent results
    const outputs = successfulResults
      .map(r => r.result?.output || r.result?.answer || r.result?.summary)
      .filter(Boolean);
    
    if (outputs.length === 0) {
      return `I've analyzed your query using ${successfulResults.length} agents, but couldn't generate a specific answer. Please try rephrasing your question.`;
    }
    
    const agentNames = successfulResults.map(r => r.agentName || r.agentId).join(', ');
    
    return `Based on analysis from ${successfulResults.length} agent(s) (${agentNames}), here's what I found:\n\n` +
           outputs.map((o, i) => `${i + 1}. ${o}`).join('\n\n');
  }

  /**
   * Build immediate response for fast client feedback
   */
  buildImmediateResponse({ query, intent, templates, memoryContext, requestId, conversationId }) {
    // Build acknowledgment message
    const ack = this.buildAcknowledgment(query, intent, templates);

    // Build declarative plan (what needs to be done)
    const declarativePlan = templates.map(template => ({
      action: `execute_template_${template.id}`,
      templateId: template.id,
      templateName: template.name,
      domain: template.domain,
      relevance: template.relevance,
      direction: 'user_directed' // User-facing actions
    }));

    // Build procedural plan (how it will be done)
    const proceduralPlan = templates.flatMap(template => 
      (template.schema?.agents || []).map((agentId, index) => ({
        id: `task-${Date.now()}-${index}`,
        title: `Activate ${agentId} for analysis`,
        service: agentId.toLowerCase(),
        capability: this.mapAgentToCapability(agentId),
        direction: 'system_directed', // Background system tasks
        deps: index > 0 ? [`task-${Date.now()}-${index-1}`] : []
      }))
    );

    // Build questions/clarifications if needed
    const ask = this.buildClarifications(query, intent, templates);

    // Construct TurnEnvelope
    const turnEnvelope = {
      ack,
      plan: {
        declarative: declarativePlan,
        procedural: proceduralPlan
      },
      ask,
      memory: {
        workingMemory: memoryContext.workingMemory || [],
        retrieved: memoryContext.shortTermMemory?.length || 0,
        conversationTurns: memoryContext.conversationHistory?.length || 0
      },
      delta: null,
      decisions: [],
      meta: {
        concepts: this.extractConcepts(query, intent),
        provenance: intent.confidence > 0.7 ? 'OpenAI-GPT4' : 'Fallback',
        processingMode: 'immediate_response',
        templatesUsed: templates.map(t => t.name)
      }
    };

    // Build full response
    return {
      query,
      intentClassification: intent,
      conversationalResponse: this.buildConversationalResponse(ack, templates),
      response: this.buildConversationalResponse(ack, templates),
      turnEnvelope,
      processedAt: new Date().toISOString(),
      requestId,
      conversationId,
      templates: templates.map(t => ({ 
        id: t.id, 
        name: t.name, 
        relevance: t.relevance,
        relevanceBreakdown: t.relevanceBreakdown || null
      }))
    };
  }

  /**
   * Build acknowledgment message
   */
  buildAcknowledgment(query, intent, templates) {
    const templateNames = templates.map(t => t.name).join(', ');
    const intentType = intent.intent.toLowerCase();

    if (templates.length > 0) {
      return `I'm analyzing your ${intentType} query using the ${templateNames}. I'll provide insights shortly.`;
    }

    return `I'm processing your ${intentType} query and will surface insights shortly.`;
  }

  /**
   * Build clarifying questions if needed
   */
  buildClarifications(query, intent, templates) {
    const questions = [];

    // Low confidence - ask for clarification
    if (intent.confidence < 0.6) {
      questions.push({
        id: `clarify-${Date.now()}`,
        question: `To provide the best analysis, could you clarify what specific insights you're looking for?`,
        reason: 'low_confidence',
        confidence: intent.confidence
      });
    }

    // Missing entities - ask for details
    const entities = intent.entities || {};
    if (intent.intent === 'ANALYSIS' && !entities.period && !entities.timeframe) {
      questions.push({
        id: `timeframe-${Date.now()}`,
        question: `What time period should I analyze? (e.g., Q4 2024, last 6 months)`,
        reason: 'missing_timeframe'
      });
    }

    return questions;
  }

  /**
   * Extract concepts from query and intent
   */
  extractConcepts(query, intent) {
    const concepts = [];
    const keywords = intent.keywords || [];
    const entities = intent.entities || {};

    // Add intent as a concept
    concepts.push(intent.intent);

    // Add keywords as concepts
    keywords.forEach(kw => concepts.push(kw));

    // Add entity values as concepts
    Object.values(entities).forEach(val => {
      if (typeof val === 'string') {
        concepts.push(val);
      }
    });

    return concepts;
  }

  /**
   * Map agent ID to capability
   */
  mapAgentToCapability(agentId) {
    const mapping = {
      SDA: 'semantic_search',
      FQA: 'forecasting',
      CAA: 'causal_analysis',
      SSA: 'scenario_simulation',
      IRA: 'risk_assessment',
      OPT: 'optimization',
      ASA: 'answer_synthesis'
    };

    return mapping[agentId] || 'general_analysis';
  }

  /**
   * Build conversational response text
   */
  buildConversationalResponse(ack, templates) {
    const formatted = `\`\`\`json
{
  "acknowledgment": "${ack}",
  "templates": ${JSON.stringify(templates.map(t => ({ name: t.name, relevance: t.relevance, relevanceBreakdown: t.relevanceBreakdown || null })), null, 2)},
  "status": "processing"
}
\`\`\``;

    return formatted;
  }

  /**
   * Get fallback templates when database is unavailable
   */
  getFallbackTemplates(intent) {
    return [{
      id: `fallback-${intent.toLowerCase()}`,
      name: `${intent} Template`,
      description: `Generic ${intent.toLowerCase()} workflow`,
      domain: 'general',
      relevance: 0.5,
      schema: { agents: [], steps: [] },
      source: 'fallback'
    }];
  }
}

