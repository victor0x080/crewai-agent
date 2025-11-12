/**
 * Agent Orchestrator Service
 * Coordinates 55 CrewAI Python agents for intelligent task execution
 */

import config from '../config/index.js';
import { logger } from '../utils/logger.js';
import { agentRegistry } from '../agents/registry.js';
import CrewAIBridgeService from './CrewAIBridgeService.js';
import UnifiedAgentDiscoveryService from './UnifiedAgentDiscoveryService.js';

export default class AgentOrchestrator {
  constructor(crewAIBridgeInstance = null) {
    this.crewAIBridge = crewAIBridgeInstance;
    this.healthy = false;
    this.activeAgents = new Map();
    this.useRealAgents = config.redis.enabled; // Use real agents if Redis available
    this.discoveryService = new UnifiedAgentDiscoveryService({ threshold: 0.72 });
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

    try {
      await this.discoveryService.initialize();
    } catch (e) {
      logger.warn('UnifiedAgentDiscoveryService init failed', { error: e.message });
    }
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

    // STEP 1: Try discovery first to check confidence scores
    const entities = intent.entities || {};
    const discovery = await this.discoveryService.discoverAndExecuteAgents(query, intent, entities, templates);
    
    // STEP 2: If high confidence agents found, use them; otherwise check templates/defaults
    let selectedAgents = [];
    
    if ((discovery.highConfidence || []).length > 0) {
      const ids = new Set(discovery.highConfidence.map(a => a.id.toLowerCase()));
      selectedAgents = agentRegistry.filter(a => ids.has(a.id));
      logger.info(`🔎 Discovery selected ${selectedAgents.length} high-confidence agent(s): ${selectedAgents.map(a => a.name).join(', ')}`);
    } else {
      // No high-confidence matches: prioritize dynamic agent creation over templates
      if (discovery.dynamicAgentSpec) {
        // Dynamic agent spec available - skip templates and create dynamic agent
        logger.info('🔧 Dynamic agent spec available - skipping templates/defaults');
        selectedAgents = []; // Clear to trigger dynamic agent creation
      } else if (templates && templates.length > 0) {
        // No dynamic spec but templates available - use them
        selectedAgents = this.selectAgents(templates, intent);
        logger.info('✅ Agents selected from templates', {
          count: selectedAgents.length,
          agents: selectedAgents.map(a => a.name)
        });
      } else {
        // No templates and no dynamic spec - will use defaults
        logger.info('⚠️  No high-confidence agents, no templates, no dynamic spec - using defaults');
      }
    }

    // Execute selected agents if we have any (but not if we have a dynamic spec to create)
    if (selectedAgents.length > 0 && !discovery.dynamicAgentSpec) {
      const agentResults = await this.executeAgents(selectedAgents, {
        query, intent, context, conversationId, userId, tenantId
      });
      const aggregated = this.aggregateResults(agentResults, query, intent);
      const totalTime = Date.now() - startTime;
      
      // Map confidence scores for selected agents
      const confidenceMap = new Map();
      (discovery.discovered || []).forEach(agent => {
        confidenceMap.set(agent.id.toLowerCase(), agent.confidence);
      });
      const agentConfidences = selectedAgents.map(a => ({
        agentId: a.id,
        agentName: a.name,
        confidence: confidenceMap.get(a.id.toLowerCase()) || null
      }));
      
      return {
        agents: selectedAgents.map(a => a.name),
        results: agentResults,
        summary: aggregated,
        metrics: {
          totalTime,
          agentsInvolved: selectedAgents.length,
          successRate: agentResults.filter(r => r.success).length / (agentResults.length || 1)
        },
        discovery: { 
          used: true, 
          highConfidence: discovery.highConfidence || [],
          confidenceScores: agentConfidences,
          threshold: this.discoveryService.threshold,
          maxConfidence: discovery.discovered && discovery.discovered.length > 0 
            ? Math.max(...discovery.discovered.map(a => a.confidence)) 
            : null
        }
      };
    }

    // If no agents chosen and we have a dynamic spec, create dynamic agent
    if (discovery.dynamicAgentSpec) {
        logger.info('🔧 Dynamic agent spec generated - creating agent via Python factory');
        
        // Call Python factory to create the agent
        const agentCreationResult = await this.createDynamicAgent(discovery.dynamicAgentSpec);
        
        if (agentCreationResult.success) {
          logger.info('✅ Dynamic agent created successfully', {
            agentId: agentCreationResult.agent_id,
            agentName: agentCreationResult.agent_name
          });
          
          // Start the runner process for this dynamic agent
          const runnerResult = await this.startDynamicAgentRunner(agentCreationResult.agent_id);
          if (!runnerResult.success) {
            logger.warn('⚠️  Failed to start dynamic agent runner, but continuing', {
              agentId: agentCreationResult.agent_id,
              error: runnerResult.error
            });
          } else {
            logger.info('✅ Dynamic agent runner started', {
              agentId: agentCreationResult.agent_id,
              pid: runnerResult.pid
            });
          }
          
          // Wait a bit for runner to initialize and connect to Redis
          await new Promise(resolve => setTimeout(resolve, 2000));
          
          // Execute the newly created agent via Redis stream
          const dynamicAgent = {
            id: agentCreationResult.agent_id,
            name: agentCreationResult.agent_name,
            capabilities: agentCreationResult.capabilities || [],
            category: 'dynamic'
          };
          
          const agentResults = await this.executeAgents([dynamicAgent], {
            query, intent, context, conversationId, userId, tenantId
          });
          
          const aggregated = this.aggregateResults(agentResults, query, intent);
          const totalTime = Date.now() - startTime;
          
          // Include confidence scores from discovery
          const confidenceMap = new Map();
          (discovery.discovered || []).forEach(agent => {
            confidenceMap.set(agent.id.toLowerCase(), agent.confidence);
          });
          
          return {
            agents: [agentCreationResult.agent_name],
            results: agentResults,
            summary: aggregated,
            metrics: {
              totalTime,
              agentsInvolved: 1,
              successRate: agentResults.filter(r => r.success).length / (agentResults.length || 1)
            },
            discovery: {
              used: true,
              dynamicAgentCreated: true,
              agentId: agentCreationResult.agent_id,
              agentSpec: discovery.dynamicAgentSpec,
              threshold: this.discoveryService.threshold,
              maxConfidence: discovery.discovered && discovery.discovered.length > 0 
                ? Math.max(...discovery.discovered.map(a => a.confidence)) 
                : null,
              topConfidenceScores: (discovery.discovered || [])
                .sort((a, b) => b.confidence - a.confidence)
                .slice(0, 5)
                .map(a => ({ agentId: a.id, agentName: a.name, confidence: a.confidence }))
            }
          };
        } else {
          logger.error('❌ Failed to create dynamic agent', { error: agentCreationResult.error });
          const totalTime = Date.now() - startTime;
          return {
            agents: [],
            results: [],
            summary: {
              query,
              intent: intent.intent,
              agentsInvolved: 0,
              successCount: 0,
              failureCount: 1,
              averageConfidence: 0,
              outputs: [],
              synthesizedAnswer: `Failed to create dynamic agent: ${agentCreationResult.error}`,
              processingTime: totalTime
            },
            metrics: { totalTime, agentsInvolved: 0, successRate: 0 },
            discovery: {
              used: false,
              dynamicAgentCreated: false,
              error: agentCreationResult.error,
              agentSpec: discovery.dynamicAgentSpec
            }
          };
        }
    }

    // Fallback: if we get here, something went wrong
    logger.warn('No agents selected and no dynamic agent created - returning empty result');
    const totalTime = Date.now() - startTime;
    return {
      agents: [],
      results: [],
      summary: {
        query,
        intent: intent.intent,
        agentsInvolved: 0,
        successCount: 0,
        failureCount: 0,
        averageConfidence: 0,
        outputs: [],
        synthesizedAnswer: 'No suitable agents found and dynamic agent creation failed or was not triggered.',
        processingTime: totalTime
      },
      metrics: {
        totalTime,
        agentsInvolved: 0,
        successRate: 0
      },
      discovery: {
        used: true,
        highConfidence: discovery.highConfidence || [],
        threshold: this.discoveryService.threshold
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

    // Build tasks directly for the provided agents (do not gate on heartbeat)
    // This ensures newly started dynamic agents receive tasks immediately
    const agentTasks = agents.map(agent => ({
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

    // At least one task should be present; if not, return promptly
    if (agentTasks.length === 0) return [];

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

  /**
   * Start a dynamic agent runner process
   * The runner listens on Redis stream and executes tasks for the dynamic agent
   */
  async startDynamicAgentRunner(agentId) {
    const { spawn } = await import('child_process');
    const path = await import('path');
    const { fileURLToPath } = await import('url');
    const fs = await import('fs');
    
    try {
      // Calculate project root: src/services/AgentOrchestrator.js -> src -> project root
      const currentFile = fileURLToPath(import.meta.url);
      const servicesDir = path.dirname(currentFile); // src/services
      const srcDir = path.dirname(servicesDir); // src
      const projectRoot = path.dirname(srcDir); // project root
      const venvPython = path.join(projectRoot, 'venv', 'bin', 'python3');
      const pythonCmd = fs.existsSync(venvPython) ? venvPython : 'python3';
      
      const runnerPath = path.join(projectRoot, 'agents', 'crewai_python', 'runners', 'dynamic_runner.py');
      const crewaiDir = path.join(projectRoot, 'agents', 'crewai_python');
      
      // Verify runner exists
      if (!fs.existsSync(runnerPath)) {
        logger.error('❌ Dynamic runner script not found', { runnerPath, projectRoot });
        return {
          success: false,
          error: `Runner script not found at ${runnerPath}`
        };
      }
      
      // Get environment variables
      const env = { ...process.env };
      env['API_URL'] = process.env.API_URL || 'http://localhost:3001';
      env['REDIS_HOST'] = process.env.REDIS_HOST || 'localhost';
      env['REDIS_PORT'] = process.env.REDIS_PORT || '6379';
      if (process.env.REDIS_PASSWORD) {
        env['REDIS_PASSWORD'] = process.env.REDIS_PASSWORD;
      }
      
      logger.info('🚀 Starting dynamic agent runner', {
        agentId,
        pythonCmd,
        runnerPath
      });
      
      // Spawn runner process (runs in background, listens on Redis stream)
      const runnerProcess = spawn(pythonCmd, [runnerPath, agentId], {
        cwd: crewaiDir,
        env,
        stdio: ['ignore', 'pipe', 'pipe'], // Don't inherit stdin, capture stdout/stderr
        detached: false // Keep attached to parent process
      });
      
      // Log runner output
      runnerProcess.stdout.on('data', (data) => {
        logger.debug(`[Dynamic Runner ${agentId}] ${data.toString().trim()}`);
      });
      
      runnerProcess.stderr.on('data', (data) => {
        logger.warn(`[Dynamic Runner ${agentId}] ${data.toString().trim()}`);
      });
      
      runnerProcess.on('error', (error) => {
        logger.error(`❌ Failed to start dynamic agent runner for ${agentId}`, {
          error: error.message
        });
      });
      
      runnerProcess.on('exit', (code) => {
        if (code !== 0 && code !== null) {
          logger.warn(`⚠️  Dynamic agent runner ${agentId} exited with code ${code}`);
        }
      });
      
      // Give runner a moment to initialize
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      return {
        success: true,
        pid: runnerProcess.pid,
        agentId
      };
      
    } catch (error) {
      logger.error('❌ Error starting dynamic agent runner', { error: error.message });
      return {
        success: false,
        error: error.message
      };
    }
  }

  /**
   * Create dynamic agent using Python factory
   * Calls create_dynamic_agent.py with the spec from OpenAI
   */
  async createDynamicAgent(agentSpec) {
    const { spawn } = await import('child_process');
    const path = await import('path');
    const { fileURLToPath } = await import('url');
    const fs = await import('fs');
    
    return new Promise((resolve) => {
      try {
        // Determine Python command (venv or system)
        // Calculate project root: src/services/AgentOrchestrator.js -> src -> project root
        const currentFile = fileURLToPath(import.meta.url);
        const servicesDir = path.dirname(currentFile); // src/services
        const srcDir = path.dirname(servicesDir); // src
        const projectRoot = path.dirname(srcDir); // project root
        const venvPython = path.join(projectRoot, 'venv', 'bin', 'python3');
        const pythonCmd = fs.existsSync(venvPython) ? venvPython : 'python3';
        
        // Path to Python script
        const scriptPath = path.join(projectRoot, 'agents', 'crewai_python', 'factory', 'create_dynamic_agent.py');
        
        // Verify script exists
        if (!fs.existsSync(scriptPath)) {
          logger.error('❌ Python script not found', { scriptPath, projectRoot });
          resolve({
            success: false,
            error: `Python script not found at ${scriptPath}`
          });
          return;
        }
        
        logger.info('🐍 Calling Python factory to create dynamic agent', {
          pythonCmd,
          scriptPath,
          agentName: agentSpec.agentName
        });
        
        // Spawn Python process with spec as JSON argument
        const pythonProcess = spawn(pythonCmd, [scriptPath, JSON.stringify(agentSpec)], {
          cwd: projectRoot,
          stdio: ['pipe', 'pipe', 'pipe']
        });
        
        let stdout = '';
        let stderr = '';
        
        pythonProcess.stdout.on('data', (data) => {
          stdout += data.toString();
        });
        
        pythonProcess.stderr.on('data', (data) => {
          stderr += data.toString();
          // Log stderr messages (info/debug) but don't treat as errors
          const msg = data.toString().trim();
          if (msg) {
            logger.debug('🐍 Python factory log', { message: msg });
          }
        });
        
        pythonProcess.on('close', (code) => {
          if (code === 0) {
            try {
              const result = JSON.parse(stdout);
              resolve(result);
            } catch (parseError) {
              logger.error('❌ Failed to parse Python factory output', {
                error: parseError.message,
                stdout,
                stderr
              });
              resolve({
                success: false,
                error: `Failed to parse factory output: ${parseError.message}`,
                stdout,
                stderr
              });
            }
          } else {
            logger.error('❌ Python factory failed', {
              exitCode: code,
              stderr
            });
            resolve({
              success: false,
              error: stderr || `Python process exited with code ${code}`,
              stdout,
              stderr
            });
          }
        });
        
        pythonProcess.on('error', (error) => {
          logger.error('❌ Failed to spawn Python process', { error: error.message });
          resolve({
            success: false,
            error: `Failed to spawn Python process: ${error.message}`
          });
        });
        
        // Set timeout (30 seconds)
        setTimeout(() => {
          if (!pythonProcess.killed) {
            pythonProcess.kill();
            resolve({
              success: false,
              error: 'Python factory timeout after 30 seconds'
            });
          }
        }, 30000);
        
      } catch (error) {
        logger.error('❌ Error calling Python factory', { error: error.message });
        resolve({
          success: false,
          error: `Error calling Python factory: ${error.message}`
        });
      }
    });
  }
}

