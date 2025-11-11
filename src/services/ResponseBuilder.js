/**
 * Response Builder Service
 * Constructs TurnEnvelope responses in ACT-R compatible format
 */

import { logger } from '../utils/logger.js';

export default class ResponseBuilder {
  constructor(promptService = null) {
    this.promptService = promptService;
    this.healthy = true;
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
  buildResponse({ query, intent, templates, memoryContext, requestId, conversationId, agentResults }) {
    // If agent results are available, build answer from them
    let ack = this.buildAcknowledgment(query, intent, templates);
    let answer = null;
    
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
        answer = agentResults.summary.synthesizedAnswer || 
                 agentResults.summary.answer || 
                 agentResults.summary.summary ||
                 null;
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
      conversationalResponse: answer || this.buildConversationalResponse(ack, templates),
      response: answer || this.buildConversationalResponse(ack, templates),
      turnEnvelope,
      agentResults: agentResults ? {
        agents: agentResults.agents || [],
        results: agentResults.results || [],
        summary: agentResults.summary || null,
        metrics: agentResults.metrics || null,
        timeout: agentResults.timeout || false,
        error: agentResults.error || null
      } : null,
      processedAt: new Date().toISOString(),
      requestId,
      conversationId,
      templates: templates.map(t => ({ id: t.id, name: t.name, relevance: t.relevance }))
    };
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
      templates: templates.map(t => ({ id: t.id, name: t.name, relevance: t.relevance }))
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
  "templates": ${JSON.stringify(templates.map(t => ({ name: t.name, relevance: t.relevance })), null, 2)},
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

