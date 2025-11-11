/**
 * IMS Agent Workflow Backend Server
 * Clean implementation of the intelligent agent orchestration system
 */

import { createServer } from 'http';
import { parse } from 'url';
import config from './config/index.js';
import IntentRouter from './services/IntentRouter.js';
import TemplateEngine from './services/TemplateEngine.js';
import AgentOrchestrator from './services/AgentOrchestrator.js';
import MemoryService from './services/MemoryService.js';
import ResponseBuilder from './services/ResponseBuilder.js';
import PromptService from './services/PromptService.js';
import CrewAIBridgeService from './services/CrewAIBridgeService.js';
import { logger } from './utils/logger.js';
import { validateProcessMessageRequest } from './utils/validators.js';

// Initialize services
const promptService = new PromptService();
const intentRouter = new IntentRouter(promptService);
const templateEngine = new TemplateEngine();
const crewAIBridge = new CrewAIBridgeService();
const agentOrchestrator = new AgentOrchestrator(crewAIBridge);
const memoryService = new MemoryService();
const responseBuilder = new ResponseBuilder(promptService);

// Initialize all services
async function initialize() {
  logger.info('Initializing IMS Agent Backend...');
  
  try {
    await promptService.initialize();
    await intentRouter.initialize();
    await templateEngine.initialize();
    await crewAIBridge.initialize();
    await agentOrchestrator.initialize();
    await memoryService.initialize();
    await responseBuilder.initialize();
    
    // Preload commonly used prompts
    if (promptService.isHealthy()) {
      await promptService.preloadPrompts(['intent_classifier', 'conversation_creator']);
    }
    
    logger.info('✅ All services initialized successfully');
  } catch (error) {
    logger.error('❌ Service initialization failed:', error);
    process.exit(1);
  }
}

// Main request handler
async function handleProcessMessage(req, res) {
  const requestId = `req-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  const startTime = Date.now();
  
  logger.info('📨 Processing message', { requestId });
  
  try {
    // Parse request body
    let body = '';
    req.on('data', chunk => { body += chunk.toString(); });
    
    await new Promise((resolve, reject) => {
      req.on('end', resolve);
      req.on('error', reject);
    });
    
    const requestData = JSON.parse(body);
    
    // Validate request
    const validation = validateProcessMessageRequest(requestData);
    if (!validation.valid) {
      res.writeHead(400, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Invalid request', details: validation.errors }));
      return;
    }
    
    const { message, conversationId, context } = requestData;
    const userId = context?.userId || 'anonymous';
    const tenantId = context?.tenantId || 'default';
    
    logger.info('🎯 Request details', {
      requestId,
      message: message.slice(0, 60),
      conversationId,
      userId,
      tenantId
    });
    
    // STEP 1: Intent Classification (Fast, with timeout)
    logger.info('🔍 Classifying intent...', { requestId });
    const intentPromise = intentRouter.classifyIntent(message, context);
    const intentTimeout = new Promise(resolve => 
      setTimeout(() => resolve(null), 5000) // Increased to 5s for OpenAI API latency
    );
    
    let intent = await Promise.race([intentPromise, intentTimeout]);
    
    if (!intent) {
      const elapsed = Date.now() - startTime;
      logger.warn('⏱️ Intent classification timeout, using fallback', { 
        requestId,
        elapsed: `${elapsed}ms`,
        timeout: '5000ms'
      });
      intent = {
        type: 'analysis',
        intent: 'GENERAL_QUERY',
        confidence: 0.5,
        explanation: `Timeout after ${elapsed}ms - using fallback (OpenAI API may be slow)`
      };
    } else {
      const elapsed = Date.now() - startTime;
      logger.info('✅ Intent classified', {
        requestId,
        intent: intent.intent,
        confidence: intent.confidence,
        elapsed: `${elapsed}ms`
      });
    }
    
    // STEP 2: Memory Retrieval (Fast context enrichment)
    logger.info('🧠 Retrieving memory context...', { requestId });
    const memoryContext = await memoryService.getContext(conversationId, userId, {
      query: message,
      intent: intent.intent
    });
    
    // STEP 3: Template Discovery
    logger.info('📋 Discovering templates...', { requestId });
    const templates = await templateEngine.discoverTemplates(
      message,
      intent.intent,
      memoryContext
    );
    
    logger.info('✅ Templates discovered', {
      requestId,
      count: templates.length,
      templates: templates.map(t => t.name)
    });
    
    // STEP 4: Check if we should wait for agent results
    const waitForResults = requestData.waitForResults !== false; // Default: true (wait for results)
    const maxWaitTime = requestData.maxWaitTime || Math.max(config.maxAgentTimeoutMs, 120000); // At least 120s, or configured
    
    // STEP 5: Execute agents (wait for results if requested)
    let agentResults = null;
    if (templates.length > 0) {
      if (waitForResults) {
        logger.info('🤖 Executing agents (waiting for results)...', { requestId });
        
        const agentStartTime = Date.now();
        try {
          agentResults = await Promise.race([
            agentOrchestrator.orchestrate({
              query: message,
              intent,
              templates,
              context: memoryContext,
              conversationId,
              userId,
              tenantId
            }),
            new Promise((resolve) => 
              setTimeout(() => resolve({ timeout: true, error: 'Agent execution timeout', partialResults: null }), maxWaitTime)
            )
          ]);
          
          if (agentResults && !agentResults.timeout) {
            logger.info('✅ Agent orchestration complete', {
              requestId,
              agentsInvolved: agentResults.agents?.length || 0,
              totalTime: `${Date.now() - agentStartTime}ms`
            });
            
            // Store results in memory for future context
            await memoryService.storeExecution({
              conversationId,
              userId,
              query: message,
              intent,
              agentResults,
              timestamp: new Date().toISOString()
            });
          } else {
            // Timeout occurred - try to get partial results if available
            logger.warn('⏱️ Agent execution timeout', { requestId, maxWaitTime });
            // If orchestrate was called but timed out, we might have partial results
            // For now, set timeout flag but keep structure
            const timeoutSeconds = Math.round(maxWaitTime / 1000);
            agentResults = {
              timeout: true,
              message: 'Agent execution exceeded timeout',
              agents: [],
              results: [],
              summary: null,
              metrics: null,
              error: `Timeout after ${timeoutSeconds} seconds - agents may still be processing`
            };
          }
        } catch (agentError) {
          logger.error('❌ Agent orchestration error', {
            requestId,
            error: agentError.message,
            stack: agentError.stack
          });
          agentResults = { error: agentError.message };
        }
      } else {
        // Background processing (non-blocking)
        logger.info('🤖 Starting background agent orchestration', { requestId });
        setImmediate(async () => {
          try {
            const bgResults = await agentOrchestrator.orchestrate({
              query: message,
              intent,
              templates,
              context: memoryContext,
              conversationId,
              userId,
              tenantId
            });
            
            logger.info('✅ Background agent orchestration complete', {
              requestId,
              agentsInvolved: bgResults.agents.length,
              totalTime: `${Date.now() - startTime}ms`
            });
            
            await memoryService.storeExecution({
              conversationId,
              userId,
              query: message,
              intent,
              agentResults: bgResults,
              timestamp: new Date().toISOString()
            });
          } catch (bgError) {
            logger.error('❌ Background orchestration error', {
              requestId,
              error: bgError.message
            });
          }
        });
      }
    }
    
    // STEP 6: Build response with agent results
    const response = responseBuilder.buildResponse({
      query: message,
      intent,
      templates,
      memoryContext,
      requestId,
      conversationId,
      agentResults // Include agent results if available
    });
    
    // Send response
    const processingTime = Date.now() - startTime;
    logger.info('⚡ Sending response', {
      requestId,
      processingTime: `${processingTime}ms`,
      includesAgentResults: !!agentResults
    });
    
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(response));
    
  } catch (error) {
    logger.error('❌ Request processing error', {
      requestId,
      error: error.message,
      stack: error.stack
    });
    
    if (!res.headersSent) {
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({
        error: 'Internal server error',
        details: config.nodeEnv === 'development' ? error.message : undefined,
        requestId
      }));
    }
  }
}

// Health check endpoint
function handleHealth(req, res) {
  const health = {
    status: 'healthy',
    timestamp: new Date().toISOString(),
    services: {
      promptService: promptService.isHealthy(),
      intentRouter: intentRouter.isHealthy(),
      templateEngine: templateEngine.isHealthy(),
      agentOrchestrator: agentOrchestrator.isHealthy(),
      memoryService: memoryService.isHealthy()
    },
    config: {
      port: config.port,
      nodeEnv: config.nodeEnv,
      redisEnabled: config.redis.enabled,
      backgroundProcessing: config.enableBackgroundProcessing
    }
  };
  
  const allHealthy = Object.values(health.services).every(s => s);
  const statusCode = allHealthy ? 200 : 503;
  
  res.writeHead(statusCode, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify(health));
}

// Agent list endpoint
async function handleGetAgents(req, res) {
  try {
    const agents = await agentOrchestrator.getAgentRegistry();
    
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      count: agents.length,
      agents: agents.map(a => ({
        id: a.id,
        name: a.name,
        role: a.role,
        capabilities: a.capabilities,
        status: a.status
      }))
    }));
  } catch (error) {
    logger.error('Error getting agent registry:', error);
    res.writeHead(500, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'Failed to get agents' }));
  }
}

// Heartbeat endpoint for Python agents
async function handleAgentHeartbeat(req, res, managerId) {
  try {
    if (!crewAIBridge.isHealthy()) {
      res.writeHead(503, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Redis not available' }));
      return;
    }

    // Store heartbeat in Redis
    const heartbeatKey = `crewai:agent:${managerId}:heartbeat`;
    const timestamp = new Date().toISOString();
    
    await crewAIBridge.redis.setEx(heartbeatKey, 30, timestamp); // Expire in 90 seconds (agents send every 30s)

    logger.debug('💓 Agent heartbeat received', { managerId, timestamp });
    
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ 
      status: 'ok', 
      managerId,
      timestamp 
    }));
  } catch (error) {
    logger.error('Error handling agent heartbeat:', { managerId, error: error.message });
    res.writeHead(500, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'Failed to process heartbeat' }));
  }
}

// Create HTTP server
const server = createServer(async (req, res) => {
  // CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  
  if (req.method === 'OPTIONS') {
    res.writeHead(200);
    res.end();
    return;
  }
  
  const { pathname, query } = parse(req.url, true);
  const method = req.method;
  
  try {
    // Route requests
    if (pathname === '/api/process-message' && method === 'POST') {
      await handleProcessMessage(req, res);
    } else if (pathname === '/api/health' && method === 'GET') {
      handleHealth(req, res);
    } else if (pathname === '/api/agents' && method === 'GET') {
      await handleGetAgents(req, res);
    } else if (pathname.startsWith('/api/managers/') && pathname.endsWith('/heartbeat') && method === 'POST') {
      // Extract manager ID from path: /api/managers/{managerId}/heartbeat
      const parts = pathname.split('/');
      const managerId = parts[parts.length - 2];
      await handleAgentHeartbeat(req, res, managerId);
    } else {
      // 404 Not Found
      res.writeHead(404, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Not found' }));
    }
  } catch (error) {
    logger.error('Server error:', error);
    res.writeHead(500, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'Internal server error' }));
  }
});

// Start server
async function start() {
  await initialize();
  
  server.listen(config.port, () => {
    logger.info(`🚀 IMS Agent Backend running on port ${config.port}`);
    logger.info(`📍 Environment: ${config.nodeEnv}`);
    logger.info(`🔗 OpenAI: ${config.openai.enabled ? '✅ Enabled' : '❌ Disabled'}`);
    logger.info(`🔗 Supabase: ${config.supabase.enabled ? '✅ Enabled' : '❌ Disabled'}`);
    logger.info(`🔗 Redis: ${config.redis.enabled ? '✅ Enabled' : '❌ Disabled'}`);
    logger.info(`\n📋 Endpoints:`);
    logger.info(`   POST http://localhost:${config.port}/api/process-message`);
    logger.info(`   GET  http://localhost:${config.port}/api/health`);
    logger.info(`   GET  http://localhost:${config.port}/api/agents\n`);
  });
}

// Graceful shutdown
process.on('SIGTERM', () => {
  logger.info('SIGTERM received, shutting down gracefully...');
  server.close(() => {
    logger.info('Server closed');
    process.exit(0);
  });
});

process.on('SIGINT', () => {
  logger.info('SIGINT received, shutting down gracefully...');
  server.close(() => {
    logger.info('Server closed');
    process.exit(0);
  });
});

// Start the server
start().catch(error => {
  logger.error('Failed to start server:', error);
  process.exit(1);
});


