/**
 * IMS Agent Workflow Backend Server
 * Clean implementation of the intelligent agent orchestration system
 */

import { createServer } from 'http';
import { parse } from 'url';
import express from 'express';
import config from './config/index.js';
import IntentRouter from './services/IntentRouter.js';
import TemplateEngine from './services/TemplateEngine.js';
import AgentOrchestrator from './services/AgentOrchestrator.js';
import MemoryService from './services/MemoryService.js';
import ResponseBuilder from './services/ResponseBuilder.js';
import PromptService from './services/PromptService.js';
import CrewAIBridgeService from './services/CrewAIBridgeService.js';
import LangChainChatbotService from './services/LangChainChatbotService.js';
import ProblemTypeClassifier from './services/ProblemTypeClassifier.js';
import WorkflowRequirementTracker from './services/WorkflowRequirementTracker.js';
import { logger } from './utils/logger.js';
import { validateProcessMessageRequest } from './utils/validators.js';
import contactCenterRoutes from './api/routes/contact-center-routes.js';
import { eventBus } from './api/routes/contact-center-routes.js';
import signalsRoutes from './api/routes/signals-routes.js';
import decisionStackRoutes from './api/routes/decision-stack-routes.js';
import WebSocketHub from './services/ws/WebSocketHub.js';
// import CoachingRouter from './services/contact-center/CoachingRouter.js'; // Not used - crew consumes directly from stream:contact_center:issues
import { RetailDatacubeService } from './services/datacube/RetailDatacubeService.js';

// Initialize services
const promptService = new PromptService();
const intentRouter = new IntentRouter(promptService);
const templateEngine = new TemplateEngine();
const crewAIBridge = new CrewAIBridgeService();
const agentOrchestrator = new AgentOrchestrator(crewAIBridge);
const memoryService = new MemoryService();
const responseBuilder = new ResponseBuilder(promptService);
const langChainChatbot = new LangChainChatbotService();
const problemTypeClassifier = new ProblemTypeClassifier();
const workflowRequirementTracker = new WorkflowRequirementTracker();
const retailDatacube = new RetailDatacubeService(
  process.env.CUBE_API_URL || 'http://localhost:4000',
  process.env.CUBEJS_API_SECRET || 'secret'
);

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
    await problemTypeClassifier.initialize();
    
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
      
      // Declare conversationHistory in outer scope so it's accessible throughout
      let conversationHistory = [];
      let datasource = null;
      
      try {
        // Retrieve datasource from datacube early (before classification) for workflow determination
        try {
          // Try to get a general datasource to determine if data is available
          const datacubeResult = await retailDatacube.getCrossDomainInsights({
            dateRange: 'last 12 weeks',
            includeAnomalies: true
          });
          if (datacubeResult) {
            datasource = Array.isArray(datacubeResult) ? datacubeResult : 
                        (datacubeResult.data || datacubeResult);
            logger.debug('📊 Retrieved initial datasource from datacube', {
              requestId,
              hasData: !!datasource
            });
          }
        } catch (datasourceError) {
          logger.debug('Could not retrieve initial datasource from datacube', {
            requestId,
            error: datasourceError.message
          });
          // Continue without datasource
        }
        
        // Classify problem type for problem-first approach
        let problemClassification = null;
        try {
          // Get conversation history for context using semantic search (top relevant messages from Pinecone)
          try {
            conversationHistory = await memoryService.getConversationHistory(conversationId, 10, message);
          } catch (historyError) {
            logger.debug('Could not retrieve conversation history for classification', {
              error: historyError.message
            });
            // Continue with empty history
            conversationHistory = [];
          }
          
          problemClassification = await problemTypeClassifier.classifyProblemType(message, {
            conversationHistory: conversationHistory || [],
            datasource: datasource // Pass datasource to classifier for workflow stage determination
          });
          
          logger.info('🎯 Problem type classified', {
            requestId,
            problemType: problemClassification.problemType,
            workflowStage: problemClassification.workflowStage,
            confidence: problemClassification.confidence
          });
        } catch (classifyError) {
          logger.warn('⚠️ Problem type classification failed, using defaults', {
            requestId,
            error: classifyError.message
          });
          // Use fallback
          problemClassification = problemTypeClassifier.getFallbackProblemType(message);
        }
        
        // Refine datasource based on problem type if needed (datasource already retrieved earlier)
        // The initial datasource is sufficient for workflow stage determination
        if (datasource && problemClassification) {
          logger.info('📊 Using datasource for workflow stage determination', {
            requestId,
            problemType: problemClassification.problemType,
            workflowStage: problemClassification.workflowStage,
            hasData: !!datasource
          });
        }
        
        // Execute CrewAI conversational agent via Redis with problem context
        // Pass pre-retrieved conversation history (MemoryService handles Pinecone retrieval)
        const agentResult = await crewAIBridge.executeAgent(
          'conversational',
          {
            task_description: 'Process user query in a conversational manner with problem-first approach',
            inputs: {
              query: message,
              conversation_id: conversationId,
              conversation_history: conversationHistory || [], // Pass pre-retrieved history from MemoryService
              context: {
                systemPrompt: context?.systemPrompt || 'You are a helpful AI assistant. Provide clear, concise, and accurate responses.',
                // Problem-first context
                problem_type: problemClassification?.problemType || 'general',
                problem_space: problemClassification?.problemSpace || message,
                workflow_stage: problemClassification?.workflowStage || 'interpret',
                problem_classification: problemClassification,
                datasource: datasource, // Include retrieved datasource from datacube
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
        
        // Store conversation to Pinecone after successful response
        try {
          await memoryService.storeConversationContext(
            conversationId,
            'conversational_agent',
            message,
            responseText,
            {
              problem_type: problemClassification?.problemType || 'general',
              workflow_stage: problemClassification?.workflowStage || 'interpret',
              problem_space: problemClassification?.problemSpace || message,
              ...(problemClassification || {})
            }
          );
        } catch (storeError) {
          logger.warn('⚠️ Failed to store conversation context', {
            error: storeError.message,
            conversationId
          });
          // Continue even if storage fails
        }
        
        // Ensure problemClassification is always defined
        if (!problemClassification) {
          problemClassification = problemTypeClassifier.getFallbackProblemType(message);
        }
        
        // Initialize requirement tracking for this stage
        let requirementStatus = null;
        try {
          const workflowStage = problemClassification.workflowStage || 'interpret';
          const problemType = problemClassification.problemType || 'general';
          
          workflowRequirementTracker.initializeTracking(
            conversationId,
            problemType,
            workflowStage
          );
          
          // Record decision about stage selection
          workflowRequirementTracker.recordDecision(
            conversationId,
            workflowStage,
            `Selected ${workflowStage} stage for ${problemType} problem`,
            `Problem type "${problemType}" with query "${message.substring(0, 50)}..." requires ${workflowStage} stage. ${problemClassification.reasoning || 'Based on problem classification.'}`,
            {
              problemType,
              problemSpace: problemClassification.problemSpace,
              confidence: problemClassification.confidence,
              isSetupQuery: problemClassification.workflowStage === 'full-llm' && (problemType === 'alert' || problemType === 'monitor' || problemType === 'automate')
            }
          );
          
          // Analyze response to detect met requirements
          const detectedRequirements = workflowRequirementTracker.analyzeResponseForRequirements(
            conversationId,
            workflowStage,
            responseText,
            problemType
          );
          
          // Get completion status
          requirementStatus = workflowRequirementTracker.getCompletionStatus(
            conversationId,
            workflowStage
          );
          
          // Check if all requirements are met (enforce completeness)
          const completionCheck = workflowRequirementTracker.checkCompletion(
            conversationId,
            workflowStage
          );
          
          if (!completionCheck.isComplete && completionCheck.unmetRequirements.length > 0) {
            // Get detailed guidance for unmet requirements
            const unmetWithGuidance = workflowRequirementTracker.getUnmetRequirementsWithDescriptions(
              conversationId,
              workflowStage
            );
            
            logger.warn('⚠️ Not all requirements met - response may be incomplete', {
              requestId,
              workflowStage,
              unmetCount: completionCheck.unmetRequirements.length,
              totalRequirements: completionCheck.totalRequirements,
              unmetRequirements: completionCheck.unmetRequirements
            });
            
            // Add unmet requirements info to status for visibility and enforcement
            if (requirementStatus) {
              requirementStatus.unmetRequirementsDetails = unmetWithGuidance;
              requirementStatus.completenessWarning = `⚠️ Only ${completionCheck.metRequirements}/${completionCheck.totalRequirements} requirements met. Response is INCOMPLETE and may not be production-ready.`;
              requirementStatus.allRequirementsMet = false;
              requirementStatus.productionReady = false;
              
              // Log specific unmet requirements for visibility
              logger.warn('📋 Unmet requirements details', {
                requestId,
                workflowStage,
                unmet: unmetWithGuidance.map(r => ({
                  requirement: r.requirement,
                  description: r.description
                }))
              });
            }
          } else if (completionCheck.isComplete) {
            logger.info('✅ All requirements met - response is complete and production-ready', {
              requestId,
              workflowStage,
              totalRequirements: completionCheck.totalRequirements
            });
            
            // Mark as production-ready
            if (requirementStatus) {
              requirementStatus.allRequirementsMet = true;
              requirementStatus.productionReady = true;
              requirementStatus.completenessWarning = null;
            }
          }
          
          logger.info('📋 Requirement tracking completed', {
            requestId,
            workflowStage,
            progress: requirementStatus?.progress,
            isComplete: requirementStatus?.isComplete,
            allRequirementsMet: completionCheck.isComplete
          });
        } catch (trackingError) {
          logger.warn('⚠️ Requirement tracking error (non-fatal)', {
            requestId,
            error: trackingError.message
          });
          // Continue without requirement tracking if it fails
        }
        
        // Build response from CrewAI agent result (include function calling metadata if present)
        response = {
          requestId,
          query: message,
          conversationId,
          response: responseText,
          // Problem classification at top level for easy access
          problem_type: problemClassification.problemType,
          workflow_stage: problemClassification.workflowStage,
          problem_space: problemClassification.problemSpace,
          // Cursor/Windsurf style structured fields
          function_calls: Array.isArray(agentResult.function_calls) ? agentResult.function_calls : [],
          metadata: typeof agentResult.metadata === 'object' && agentResult.metadata !== null
            ? {
                ...agentResult.metadata,
                problem_type: problemClassification.problemType,
                workflow_stage: problemClassification.workflowStage,
                problem_space: problemClassification.problemSpace
              }
            : { 
                conversation_id: conversationId,
                problem_type: problemClassification.problemType,
                workflow_stage: problemClassification.workflowStage,
                problem_space: problemClassification.problemSpace
              },
          timestamp: new Date().toISOString(),
          processingTime: agentResult.processingTime || (typeof agentResult.result === 'object' ? agentResult.result.processing_time : null) || (Date.now() - startTime),
          turnEnvelope: {
            ack: `I understand your question: "${message.slice(0, 50)}${message.length > 50 ? '...' : ''}"`,
            plan: {
              steps: [
                `Classified as ${problemClassification.problemType} problem`,
                `Workflow stage: ${problemClassification.workflowStage}`,
                'Processed query with CrewAI conversational agent',
                'Retrieved conversation history from Pinecone',
                'Generated response using CrewAI'
              ]
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
              taskId: agentResult.task_id,
              problemType: problemClassification.problemType,
              workflowStage: problemClassification.workflowStage,
              problemSpace: problemClassification.problemSpace,
              requirementTracking: requirementStatus ? {
                isComplete: requirementStatus.isComplete,
                allRequirementsMet: requirementStatus.allRequirementsMet || false,
                productionReady: requirementStatus.productionReady || false,
                progress: requirementStatus.progress,
                unmetRequirements: requirementStatus.requirements.filter(r => !r.met).map(r => r.requirement),
                completenessWarning: requirementStatus.completenessWarning || null
              } : null
            }
          },
          // Add requirement tracking to top level
          requirementTracking: requirementStatus ? {
            ...requirementStatus,
            allRequirementsMet: requirementStatus.allRequirementsMet || false,
            productionReady: requirementStatus.productionReady || false,
            completenessWarning: requirementStatus.completenessWarning || null,
            unmetRequirementsDetails: requirementStatus.unmetRequirementsDetails || null
          } : null
        };
      } catch (agentError) {
        // Log detailed error information for debugging
        logger.error('❌ CrewAI conversational agent error', {
          requestId,
          error: agentError.message,
          errorStack: agentError.stack,
          errorName: agentError.name,
          conversationId,
          // Common error causes:
          // - Redis connection issues
          // - Agent timeout (90 seconds)
          // - Python agent not running
          // - Redis stream errors
          // - Agent execution failures
          possibleCauses: [
            agentError.message?.includes('timeout') ? 'Agent execution timeout' : null,
            agentError.message?.includes('Redis') ? 'Redis connection issue' : null,
            agentError.message?.includes('not available') ? 'Agent service not available' : null,
            agentError.message?.includes('not connected') ? 'Redis not connected' : null
          ].filter(Boolean)
        });
        
        // Fall back to LangChain chatbot on error
        logger.info('🔄 Falling back to LangChain chatbot', { 
          requestId,
          reason: agentError.message || 'Unknown error',
          conversationId
        });
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
      langChainChatbot: langChainChatbot.isHealthy(),
      problemTypeClassifier: problemTypeClassifier ? problemTypeClassifier.isHealthy() : false
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

// Requirement tracking endpoint
async function handleGetRequirementTracking(req, res) {
  try {
    const { pathname } = parse(req.url, true);
    const parts = pathname.split('/');
    
    // /api/requirement-tracking/:conversationId/:workflowStage
    if (parts.length === 5 && parts[3] && parts[4]) {
      const conversationId = parts[3];
      const workflowStage = parts[4];
      
      const status = workflowRequirementTracker.getCompletionStatus(conversationId, workflowStage);
      
      if (!status) {
        res.writeHead(404, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Tracking not found for this conversation/stage' }));
        return;
      }
      
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(status));
      return;
    }
    
    // /api/requirement-tracking/summary
    if (parts.length === 4 && parts[3] === 'summary') {
      const summary = workflowRequirementTracker.getSummary();
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(summary));
      return;
    }
    
    res.writeHead(400, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'Invalid endpoint. Use /api/requirement-tracking/:conversationId/:workflowStage or /api/requirement-tracking/summary' }));
  } catch (error) {
    logger.error('Error getting requirement tracking:', error);
    res.writeHead(500, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'Failed to get requirement tracking' }));
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

// Create Express app for contact-center routes
const app = express();
app.use(express.json()); // For parsing application/json
app.use('/api/contact-center', contactCenterRoutes);
app.use('/api/signals', signalsRoutes);
app.use('/api/decision-stacks', decisionStackRoutes);

// Create HTTP server
const server = createServer(async (req, res) => {
  // Skip WebSocket upgrade requests - they're handled by WebSocketHub via 'upgrade' event
  // The upgrade event fires separately, so we just need to avoid processing it here
  if (req.headers.upgrade === 'websocket') {
    // Don't send a response - let the upgrade handler deal with it
    return;
  }
  
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
  
  // Handle Express routes (contact-center, signals, decision-stacks)
  if (pathname.startsWith('/api/contact-center') || 
      pathname.startsWith('/api/signals') || 
      pathname.startsWith('/api/decision-stacks')) {
    app(req, res);
    return;
  }
  
  try {
    // Route requests
    if (pathname === '/api/process-message' && method === 'POST') {
      await handleProcessMessage(req, res);
    } else if (pathname === '/api/health' && method === 'GET') {
      handleHealth(req, res);
    } else if (pathname === '/api/agents' && method === 'GET') {
      await handleGetAgents(req, res);
    } else if (pathname.startsWith('/api/requirement-tracking') && method === 'GET') {
      await handleGetRequirementTracking(req, res);
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

  // Initialize WebSocket hub BEFORE server starts listening
  // This ensures upgrade handler is registered before any connections
  const wsHub = new WebSocketHub(server, eventBus, process.env.REDIS_URL);
  
  // Start automatic router: issues -> coaching manager decisions
  // NOTE: Not needed - CrewAIManagerService consumes directly from stream:contact_center:issues
  // const router = new CoachingRouter(process.env.REDIS_URL);
  // router.start();
  
  server.listen(config.port, () => {
    logger.info(`🚀 IMS Agent Backend running on port ${config.port}`);
    logger.info(`📍 Environment: ${config.nodeEnv}`);
    logger.info(`🔗 OpenAI: ${config.openai.enabled ? '✅ Enabled' : '❌ Disabled'}`);
    logger.info(`🔗 Supabase: ${config.supabase.enabled ? '✅ Enabled' : '❌ Disabled'}`);
    logger.info(`🔗 Redis: ${config.redis.enabled ? '✅ Enabled' : '❌ Disabled'}`);
    logger.info(`\n📋 Endpoints:`);
    logger.info(`   POST http://localhost:${config.port}/api/process-message`);
    logger.info(`   GET  http://localhost:${config.port}/api/health`);
    logger.info(`   GET  http://localhost:${config.port}/api/agents`);
    logger.info(`   WS   ws://localhost:${config.port}/ws/rep/:repId\n`);
    
    // Start WebSocket hub AFTER server is listening
    wsHub.start();
    logger.info(`🌐 WebSocket hub started - clients can connect at ws://localhost:${config.port}/ws/rep/:repId`);
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


