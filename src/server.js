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
import LangChainChatbotService from './services/LangChainChatbotService.js';
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
const langChainChatbot = new LangChainChatbotService();

/**
 * Normalize and extract agentTag from multiple possible locations (robust)
 */
function normalizeAgentTag(tag) {
  if (!tag || typeof tag !== 'string') return null;
  return tag.trim().toLowerCase();
}

function extractAgentTag(req, body) {
  // Prefer top-level
  let tag =
    body?.agentTag ||
    body?.agent_tag ||
    body?.agent ||
    body?.tag ||
    body?.context?.agentTag ||
    body?.context?.agent ||
    null;
  // Allow header override
  if (!tag && req?.headers) {
    tag = req.headers['x-agent-tag'] || req.headers['x-agent'] || null;
  }
  // Allow query string override
  try {
    const parsed = parse(req.url, true);
    const query = parsed && parsed.query;
    if (!tag && query && (query.agentTag || query.agent || query.tag)) {
      tag = query.agentTag || query.agent || query.tag;
    }
  } catch (_) {
    // ignore
  }
  return normalizeAgentTag(tag);
}

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
    await langChainChatbot.initialize();
    
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
    // Check for direct agent tag (skips intent/template discovery) - prefer explicit field
    const agentTagPrimary = normalizeAgentTag(requestData.agentTag);
    const agentTag = agentTagPrimary || extractAgentTag(req, requestData);
    
    logger.info('🎯 Request details', {
      requestId,
      message: message.slice(0, 60),
      conversationId: conversationId || 'none',
      agentTag: agentTag || 'none'
    });
    
    // If conversationId is provided, use CrewAI conversational agent
    // Otherwise, fall back to LangChain chatbot
    let response;
    
    if (conversationId) {
      logger.info('💬 Using CrewAI conversational agent (conversationId provided)', { requestId, conversationId });
      
      try {
        // Execute CrewAI conversational agent via Redis
        const agentResult = await crewAIBridge.executeAgent(
          'conversational',
          {
            task_description: 'Process user query in a conversational manner',
            inputs: {
              query: message,
              conversation_id: conversationId,
              context: {
                systemPrompt: context?.systemPrompt || 'You are a helpful AI assistant. Provide clear, concise, and accurate responses.',
                ...context
              }
            }
          },
          90000 // 90 second timeout
        );
        
        // Extract response text and history length
        const responseText = typeof agentResult.result === 'object' 
          ? (agentResult.result.output || agentResult.result.result || JSON.stringify(agentResult.result))
          : (agentResult.result || agentResult.response || 'I apologize, but I could not generate a response.');
        
        // Extract history_length from result (may be in nested structure)
        let historyLength = 0;
        if (typeof agentResult.result === 'object') {
          historyLength = agentResult.result.history_length || agentResult.result.historyLength || 0;
        }
        
        // Build response from CrewAI agent result (include function calling metadata if present)
        response = {
          requestId,
          query: message,
          conversationId,
          response: responseText,
          // Cursor/Windsurf style structured fields
          function_calls: Array.isArray(agentResult.function_calls) ? agentResult.function_calls : [],
          metadata: typeof agentResult.metadata === 'object' && agentResult.metadata !== null
            ? agentResult.metadata
            : { conversation_id: conversationId },
          timestamp: new Date().toISOString(),
          processingTime: agentResult.processingTime || (typeof agentResult.result === 'object' ? agentResult.result.processing_time : null) || (Date.now() - startTime),
          turnEnvelope: {
            ack: `I understand your question: "${message.slice(0, 50)}${message.length > 50 ? '...' : ''}"`,
            plan: {
              steps: ['Processed query with CrewAI conversational agent', 'Retrieved conversation history from Pinecone', 'Generated response using CrewAI']
            },
            ask: null,
            memory: {
              conversationHistory: historyLength
            },
            meta: {
              mode: 'conversational',
              service: 'CrewAI',
              agent: 'conversational',
              memoryBackend: 'Pinecone',
              requestId,
              taskId: agentResult.task_id
            }
          }
        };
      } catch (agentError) {
        logger.error('❌ CrewAI conversational agent error', {
          requestId,
          error: agentError.message,
          conversationId
        });
        
        // Fall back to LangChain chatbot on error
        logger.info('🔄 Falling back to LangChain chatbot', { requestId });
        const chatbotResponse = await langChainChatbot.processMessage(
          message,
          conversationId,
          {
            systemPrompt: context?.systemPrompt || 'You are a helpful AI assistant. Provide clear, concise, and accurate responses.',
            ...context
          }
        );
        
        response = {
          requestId,
          query: message,
          conversationId,
          response: chatbotResponse.response,
          timestamp: chatbotResponse.timestamp,
          processingTime: chatbotResponse.processingTime,
          turnEnvelope: {
            ack: `I understand your question: "${message.slice(0, 50)}${message.length > 50 ? '...' : ''}"`,
            plan: {
              steps: ['Processed query with LangChain chatbot (fallback)', 'Retrieved conversation history from Pinecone', 'Generated response using OpenAI']
            },
            ask: null,
            memory: {
              conversationHistory: chatbotResponse.historyLength || 0
            },
            meta: {
              mode: 'chatbot',
              service: 'LangChain',
              memoryBackend: langChainChatbot.pineconeHost ? 'Pinecone' : 'In-Memory',
              requestId,
              fallback: true,
              error: agentError.message
            }
          }
        };
      }
    } else {
      // No conversationId: use LangChain chatbot
      logger.info('💬 Using LangChain chatbot (no conversationId provided)', { requestId });
      
      const chatbotResponse = await langChainChatbot.processMessage(
        message,
        conversationId,
        {
          systemPrompt: context?.systemPrompt || 'You are a helpful AI assistant. Provide clear, concise, and accurate responses.',
          ...context
        }
      );
      
      response = {
        requestId,
        query: message,
        conversationId,
        response: chatbotResponse.response,
        timestamp: chatbotResponse.timestamp,
        processingTime: chatbotResponse.processingTime,
        turnEnvelope: {
          ack: `I understand your question: "${message.slice(0, 50)}${message.length > 50 ? '...' : ''}"`,
          plan: {
            steps: ['Processed query with LangChain chatbot', 'Retrieved conversation history from Pinecone', 'Generated response using OpenAI']
          },
          ask: null,
          memory: {
            conversationHistory: chatbotResponse.historyLength || 0
          },
          meta: {
            mode: 'chatbot',
            service: 'LangChain',
            memoryBackend: langChainChatbot.pineconeHost ? 'Pinecone' : 'In-Memory',
            requestId
          }
        }
      };
    }
    
    // Send response
    const processingTime = Date.now() - startTime;
    logger.info('⚡ Sending response', {
      requestId,
      processingTime: `${processingTime}ms`,
      mode: 'chatbot'
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
      memoryService: memoryService.isHealthy(),
      langChainChatbot: langChainChatbot.isHealthy()
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


