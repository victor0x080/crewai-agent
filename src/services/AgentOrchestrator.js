/**
 * Agent Orchestrator Service
 * Coordinates 55 CrewAI Python agents for intelligent task execution
 */

import config from '../config/index.js';
import { logger } from '../utils/logger.js';
import { agentRegistry } from '../agents/registry.js';
import CrewAIBridgeService from './CrewAIBridgeService.js';

export default class AgentOrchestrator {
  constructor(crewAIBridgeInstance = null) {
    this.crewAIBridge = crewAIBridgeInstance;
    this.healthy = false;
    this.activeAgents = new Map();
    this.useRealAgents = config.redis.enabled; // Use real agents if Redis available
  }

  async initialize() {
    // Initialize or reuse CrewAI bridge for real Python agent communication
    if (config.redis.enabled) {
      try {
        if (!this.crewAIBridge) {
          this.crewAIBridge = new CrewAIBridgeService();
          await this.crewAIBridge.initialize();
        } else if (!this.crewAIBridge.isHealthy()) {
          await this.crewAIBridge.initialize();
        }
        
        if (this.crewAIBridge && this.crewAIBridge.isHealthy()) {
          logger.info('✅ AgentOrchestrator initialized with REAL CrewAI agents via Redis');
          this.useRealAgents = true;
          const availableAgents = await this.crewAIBridge.getAvailableAgents();
          if (availableAgents.length > 0) {
            logger.info(`🤖 Found ${availableAgents.length} active Python agents: ${availableAgents.join(', ')}`);
          } else {
            logger.warn('⚠️ No Python agents currently active - will use simulated execution');
            this.useRealAgents = false;
          }
        } else {
          logger.warn('⚠️ CrewAI bridge unhealthy - using simulated agents');
          this.useRealAgents = false;
        }
      } catch (error) {
        logger.warn('Redis not available, using simulated orchestration', { error: error.message });
        this.useRealAgents = false;
      }
    } else {
      logger.info('Redis disabled - using simulated agent execution');
      this.useRealAgents = false;
    }

    this.healthy = true;
    logger.info(`✅ AgentOrchestrator initialized with ${agentRegistry.length} agent definitions`);
    logger.info(`   Mode: ${this.useRealAgents ? 'REAL Python CrewAI agents' : 'Simulated agents'}`);
  }

  isHealthy() {
    return this.healthy;
  }

  /**
   * Get agent registry
   */
  async getAgentRegistry() {
    return agentRegistry.map(agent => ({
      ...agent,
      status: this.activeAgents.has(agent.id) ? 'active' : 'idle'
    }));
  }

  /**
   * Orchestrate agents based on templates and intent
   * @param {object} params - Orchestration parameters
   * @returns {Promise<object>} Orchestration results
   */
  async orchestrate(params) {
    const { query, intent, templates, context, conversationId, userId, tenantId } = params;
    const startTime = Date.now();

    logger.info('🤖 Starting agent orchestration', {
      query: query.slice(0, 60),
      intent: intent.intent,
      templatesCount: templates.length
    });

    // STEP 1: Select agents based on templates
    const selectedAgents = this.selectAgents(templates, intent);
    
    logger.info('✅ Agents selected', {
      count: selectedAgents.length,
      agents: selectedAgents.map(a => a.name)
    });

    // STEP 2: Execute agents (parallel or sequential based on dependencies)
    const agentResults = await this.executeAgents(selectedAgents, {
      query,
      intent,
      context,
      conversationId,
      userId,
      tenantId
    });

    // STEP 3: Aggregate results
    const aggregated = this.aggregateResults(agentResults, query, intent);

    const totalTime = Date.now() - startTime;
    logger.info('✅ Agent orchestration complete', {
      totalTime: `${totalTime}ms`,
      agentsExecuted: agentResults.length,
      successCount: agentResults.filter(r => r.success).length
    });

    return {
      agents: selectedAgents.map(a => a.name),
      results: agentResults,
      summary: aggregated,
      metrics: {
        totalTime,
        agentsInvolved: selectedAgents.length,
        successRate: agentResults.filter(r => r.success).length / agentResults.length
      }
    };
  }

  /**
   * Select appropriate agents based on templates
   */
  selectAgents(templates, intent) {
    const agentIds = new Set();

    // Extract agents from templates
    templates.forEach(template => {
      const agents = template.schema?.agents || [];
      agents.forEach(agentId => agentIds.add(agentId));
    });

    // If no agents specified in templates, use default agents based on intent
    if (agentIds.size === 0) {
      const defaultAgents = this.getDefaultAgentsForIntent(intent.intent);
      defaultAgents.forEach(agentId => agentIds.add(agentId));
    }

    // Look up agent definitions from registry
    const selected = [];
    agentIds.forEach(agentId => {
      const agent = agentRegistry.find(a => a.id === agentId.toLowerCase());
      if (agent) {
        selected.push(agent);
      }
    });

    return selected;
  }

  /**
   * Get default agents for an intent when no template is found
   */
  getDefaultAgentsForIntent(intent) {
    const defaults = {
      ANALYSIS: ['sda', 'caa', 'asa'],
      // Keep SIMULATION lean to reduce latency and avoid unnecessary parallel calls
      SIMULATION: ['ssa'],
      QUESTION: ['fqa', 'asa'],
      DECISION: ['opt', 'asa'],
      ACTION: ['opt', 'asa'],
      GENERAL: ['asa']
    };

    return defaults[intent] || defaults.GENERAL;
  }

  /**
   * Execute agents (REAL Python CrewAI agents via Redis or simulated fallback)
   */
  async executeAgents(agents, params) {
    const { query, intent, context } = params;
    const results = [];

    // Re-check for real agents before executing (agents may have started after initialization)
    let useReal = this.useRealAgents && this.crewAIBridge;
    if (this.crewAIBridge && this.crewAIBridge.isHealthy()) {
      const availableAgents = await this.crewAIBridge.getAvailableAgents();
      if (availableAgents.length > 0) {
        useReal = true;
        logger.info(`🤖 Found ${availableAgents.length} active agents - using REAL Python CrewAI agents`);
      } else {
        logger.warn(`⚠️ No active agents found (${agents.length} agents needed) - using simulated execution`);
        useReal = false;
      }
    }

    // Decide between real or simulated execution
    if (useReal) {
      logger.info(`🤖 Executing ${agents.length} REAL Python CrewAI agents`);
      return await this.executeRealAgents(agents, params);
    } else {
      logger.info(`🎭 Executing ${agents.length} SIMULATED agents`);
      return await this.executeSimulatedAgents(agents, params);
    }
  }

  /**
   * Execute REAL Python CrewAI agents via Redis Streams
   */
  async executeRealAgents(agents, params) {
    const { query, intent, context } = params;
    const startTime = Date.now();

    // Prepare tasks for Python agents
    // Filter to only agents that are actively heartbeating (fresh within 60s)
    const availability = await Promise.all(
      agents.map(async (agent) => ({
        agent,
        available: this.crewAIBridge ? await this.crewAIBridge.isAgentAvailable(agent.id) : false
      }))
    );

    const agentTasks = availability
      .filter(({ available }) => available)
      .map(({ agent }) => agent)
      .map(agent => ({
      agentId: agent.id,
      task: {
        type: agent.capabilities[0] || 'general_analysis',
        title: `${agent.name}: ${query.slice(0, 60)}...`,
        description: `Perform ${intent.intent} analysis for query: ${query}`,
        inputs: {
          query,
          intent: intent.intent,
          context,
          capabilities: agent.capabilities,
          domain: intent.category || 'general'
        },
        priority: 'high'
      }
    }));

    if (agentTasks.length === 0) {
      // No active agents available; return empty results promptly
      return [];
    }

    try {
      // Execute all agents in parallel via Redis
      const results = await this.crewAIBridge.executeAgentsParallel(agentTasks);
      
      // Transform results to match expected format
      return results.map((result, index) => {
        const agent = agents[index];
        
        if (result.success) {
          return {
            agentId: agent.id,
            agentName: agent.name,
            success: true,
            result: result.result,
            executionTime: Date.now() - startTime,
            mode: 'real_python_crewai'
          };
        } else {
          return {
            agentId: agent.id,
            agentName: agent.name,
            success: false,
            error: result.error,
            executionTime: 0,
            mode: 'real_python_crewai_failed'
          };
        }
      });
    } catch (error) {
      logger.error('❌ Real agent execution failed, falling back to simulation', { error: error.message });
      return await this.executeSimulatedAgents(agents, params);
    }
  }

  /**
   * Execute SIMULATED agents (fallback when Python agents unavailable)
   */
  async executeSimulatedAgents(agents, params) {
    const { query, intent, context } = params;
    const executions = agents.map(async (agent) => {
      const executionId = `exec-${Date.now()}-${agent.id}`;
      this.activeAgents.set(agent.id, { executionId, startTime: Date.now() });

      try {
        logger.info(`🎭 Simulating agent: ${agent.name}`, { agentId: agent.id });

        const result = await this.simulateAgentExecution(agent, query, intent, context);
        this.activeAgents.delete(agent.id);

        return {
          agentId: agent.id,
          agentName: agent.name,
          success: true,
          result,
          executionTime: Date.now() - (this.activeAgents.get(agent.id)?.startTime || Date.now()),
          mode: 'simulated'
        };
      } catch (error) {
        this.activeAgents.delete(agent.id);
        logger.error(`❌ Agent simulation failed: ${agent.name}`, { error: error.message });

        return {
          agentId: agent.id,
          agentName: agent.name,
          success: false,
          error: error.message,
          executionTime: 0,
          mode: 'simulated_failed'
        };
      }
    });

    return await Promise.all(executions);
  }

  /**
   * Simulate agent execution (placeholder - used when Python agents not available)
   * Provides realistic simulated responses based on agent capabilities
   */
  async simulateAgentExecution(agent, query, intent, context) {
    // Simulate processing time
    await new Promise(resolve => setTimeout(resolve, Math.random() * 1000 + 500));

    // Generate agent-specific simulated responses based on capabilities
    const agentId = agent.id.toLowerCase();
    const agentName = agent.name;
    const capability = agent.capabilities[0] || 'general_analysis';
    
    let simulatedOutput = '';
    
    // Generate agent-specific responses
    if (agentId.includes('forecast') || agentId === 'fqa') {
      simulatedOutput = `Based on historical trends and current market indicators, the forecast shows moderate growth potential. Key factors include seasonal patterns, market demand signals, and external economic indicators.`;
    } else if (agentId.includes('semantic') || agentId === 'sda') {
      simulatedOutput = `Semantic analysis of the query reveals key entities: ${intent.entities ? Object.keys(intent.entities).join(', ') : 'general domain'}. Data retrieval suggests relevant datasets across multiple sources.`;
    } else if (agentId.includes('scenario') || agentId === 'ssa') {
      simulatedOutput = `Scenario simulation indicates multiple possible outcomes. Best case: positive trend with 15-20% growth. Base case: moderate growth of 5-10%. Worst case: potential decline of 5-10%.`;
    } else if (agentId.includes('risk') || agentId === 'ira') {
      simulatedOutput = `Risk assessment identifies moderate to high risk factors. Key concerns include market volatility, supply chain dependencies, and competitive pressures. Mitigation strategies recommended.`;
    } else if (agentId.includes('optim') || agentId === 'opt') {
      simulatedOutput = `Optimization analysis suggests potential improvements through resource reallocation, process efficiency gains, and strategic adjustments. Estimated impact: 10-15% improvement opportunity.`;
    } else if (agentId.includes('synthesis') || agentId === 'asa') {
      simulatedOutput = `Synthesizing insights from multiple sources: The query requires comprehensive analysis across forecasting, risk assessment, and optimization domains. Integrated recommendation suggests strategic approach with phased implementation.`;
    } else if (agentId.includes('marketing') || agentId.includes('budget')) {
      simulatedOutput = `Marketing analysis indicates optimal budget allocation across channels. Recommended split: Digital (40%), Traditional (30%), Experimental (20%), Reserve (10%). Expected ROI: 2.5-3.0x.`;
    } else if (agentId.includes('sales') || agentId.includes('pipeline')) {
      simulatedOutput = `Sales pipeline analysis shows strong conversion potential. Current pipeline value: $X, conversion rate: Y%, time-to-close: Z days. Recommended actions: focus on high-value opportunities.`;
    } else if (agentId.includes('elasticity') || agentId.includes('uplift')) {
      simulatedOutput = `Elasticity analysis suggests price sensitivity varies by segment. Optimal pricing strategy: premium segment (low elasticity), standard segment (moderate elasticity), value segment (high elasticity).`;
    } else if (agentId.includes('inventory') || agentId.includes('supply')) {
      simulatedOutput = `Supply chain analysis indicates current inventory levels are within optimal range. Lead times: 7-14 days. Stockout risk: Low. Reorder recommendations: maintain current levels with seasonal adjustments.`;
    } else if (agentId.includes('attribution') || agentId === 'caa') {
      simulatedOutput = `Causal attribution analysis identifies key drivers: primary factor (60% impact), secondary factor (25% impact), tertiary factors (15% combined). Statistical significance: p < 0.05.`;
    } else {
      // Generic simulated response
      simulatedOutput = `${agentName} has analyzed the query and identified relevant patterns. Analysis indicates ${intent.intent.toLowerCase()} approach is appropriate. Key insights: trends suggest positive direction, with ${Math.floor(70 + Math.random() * 20)}% confidence in the assessment.`;
    }

    // Return simulated result with actual analysis
    return {
      agent: agent.name,
      capability: capability,
      output: `[SIMULATED] ${simulatedOutput}`,
      confidence: 0.7 + Math.random() * 0.2,
      data: {
        intent: intent.intent,
        query: query,
        processed: true,
        simulated: true,
        timestamp: new Date().toISOString(),
        agentId: agentId
      }
    };
  }

  /**
   * Aggregate results from multiple agents
   */
  aggregateResults(agentResults, query, intent) {
    const successful = agentResults.filter(r => r.success);

    return {
      query,
      intent: intent.intent,
      agentsInvolved: agentResults.length,
      successCount: successful.length,
      failureCount: agentResults.length - successful.length,
      averageConfidence: successful.reduce((sum, r) => sum + (r.result?.confidence || 0), 0) / successful.length || 0,
      outputs: successful.map(r => ({
        agent: r.agentName,
        output: r.result?.output,
        confidence: r.result?.confidence
      })),
      synthesizedAnswer: this.synthesizeAnswer(successful, query),
      processingTime: agentResults.reduce((sum, r) => sum + r.executionTime, 0)
    };
  }

  /**
   * Synthesize final answer from agent outputs
   */
  synthesizeAnswer(successfulResults, query) {
    if (successfulResults.length === 0) {
      return 'Unable to generate insights at this time.';
    }

    const outputs = successfulResults.map(r => r.result?.output).filter(Boolean);
    
    // Simple synthesis (in production, this would use ASA - Answer Synthesis Agent)
    return `Based on analysis from ${successfulResults.length} agents, here are the insights for "${query.slice(0, 60)}...":\n\n` +
           outputs.map((o, i) => `${i + 1}. ${o}`).join('\n');
  }

  /**
   * Map agent to capability string
   */
  mapAgentToCapability(agentId) {
    const agent = agentRegistry.find(a => a.id === agentId);
    return agent?.capabilities[0] || 'general';
  }
}

