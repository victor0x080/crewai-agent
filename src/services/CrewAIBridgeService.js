/**
 * CrewAI Bridge Service
 * Manages communication between Node.js and Python CrewAI agents via Redis Streams
 */

import { createClient as createRedisClient } from 'redis';
import config from '../config/index.js';
import { logger } from '../utils/logger.js';
import { v4 as uuidv4 } from 'uuid';

export default class CrewAIBridgeService {
  constructor() {
    this.redis = null;
    this.healthy = false;
    this.pendingTasks = new Map(); // taskId -> { resolve, reject, timeout }
    this.defaultTimeout = 120000; // 120 seconds to match server orchestration window
  }

  async initialize() {
    if (!config.redis.enabled) {
      logger.warn('Redis not enabled, CrewAI bridge will not be available');
      return;
    }

    try {
      this.redis = createRedisClient({
        url: `redis://${config.redis.host}:${config.redis.port}`,
        password: config.redis.password
      });

      this.redis.on('error', (err) => {
        if (err.code !== 'ECONNREFUSED' && err.code !== 'ETIMEDOUT') {
          logger.error('Redis client error:', { error: err.message });
        }
      });

      await this.redis.connect();
      this.healthy = true;
      
      // Start listening for agent responses
      this.startResponseListener();
      
      logger.info('✅ CrewAI Bridge Service initialized with Redis');
    } catch (error) {
      logger.error('❌ CrewAI Bridge Service initialization failed', { error: error.message });
      this.healthy = false;
    }
  }

  isHealthy() {
    return this.healthy && this.redis?.isOpen;
  }

  /**
   * Map agent ID to their Redis input stream
   * Agents listen to different streams based on their role in the workflow
   */
  getAgentStream(agentId) {
    // Normalize agent ID (lowercase, remove special chars)
    const normalizedId = agentId.toLowerCase().replace(/[^a-z0-9-]/g, '-');
    // Alias map to match runner group ids that differ from registry ids
    const aliasMap = {
      'ingress-normalization': 'ingress-normalizer',
      'question-router-planner': 'qrp-planner',
      'goal-policy-elicitation': 'goal-policy',
      'counterfactual-experiment': 'counterfactual-experiment', // already same
      'rca-change-detective': 'change-detective-rca',
      'inventory-position': 'inventory-position',
      'capacity-leadtime': 'capacity-leadtime',
      'supply-planning': 'supply-planning',
      'production-scheduling': 'production-scheduling',
      'logistics-allocation': 'logistics-allocation',
      'campaign-sku-mapper': 'campaign-sku-mapper',
      'elasticity-uplift': 'elasticity-uplift'
    };
    const idForStreams = aliasMap[normalizedId] || normalizedId;
    
    // Per-agent dedicated input stream
    return `stream:agent:${idForStreams}:in`;
  }

  /**
   * Execute a Python CrewAI agent via Redis Streams
   * @param {string} agentId - Agent identifier
   * @param {object} task - Task details
   * @param {number} timeout - Timeout in ms (default 30000)
   * @returns {Promise<object>} Agent execution result
   */
  async executeAgent(agentId, task, timeout = this.defaultTimeout) {
    if (!this.isHealthy()) {
      throw new Error('CrewAI Bridge not available - Redis not connected');
    }

    const taskId = uuidv4();
    const streamName = this.getAgentStream(agentId);
    
    logger.info(`🤖 Executing CrewAI agent via Redis`, {
      agentId,
      taskId,
      stream: streamName
    });

    // Create promise that will be resolved when response arrives
    const resultPromise = new Promise((resolve, reject) => {
      // Set timeout
      const timeoutId = setTimeout(() => {
        this.pendingTasks.delete(taskId);
        reject(new Error(`Agent execution timeout after ${timeout}ms`));
      }, timeout);

      // Store promise resolvers
      this.pendingTasks.set(taskId, {
        resolve,
        reject,
        timeout: timeoutId
      });
    });

    // Publish task to Redis Stream in CloudEvents format
    try {
      // Create CloudEvent-compliant message
      const eventId = uuidv4();
      const cloudevent = {
        specversion: '1.0',
        id: eventId,
        type: 'crewai.task.request',
        source: `urn:nodejs-backend:${process.pid}`,
        subject: agentId,
        time: new Date().toISOString(),
        dataschema: 'https://schemas.mesh/TaskRequest.json',
        data: {
          task_id: taskId,
          agent_id: agentId,
          task_type: task.type || 'generic',
          task_description: task.description || task.title || '',
          inputs: task.inputs || {},
          priority: task.priority || 'medium',
          timestamp: new Date().toISOString(),
          requester: 'nodejs-backend'
        }
      };

      // Store full event as JSON string (fallback when RedisJSON not available)
      // Agents expect event:{eventId} to contain the full CloudEvent
      await this.redis.set(`event:${eventId}`, JSON.stringify(cloudevent));
      
      // Add pointer to stream (as agents expect)
      await this.redis.xAdd(streamName, '*', {
        event_id: eventId,
        type: cloudevent.type,
        subject: cloudevent.subject,
        dataschema: cloudevent.dataschema
      });
      
      logger.info(`✅ Task published to Redis Stream`, { taskId, streamName, eventId });
      
      // Also listen to agent output streams for responses
      // Agents publish to different output streams, so we need to monitor multiple streams
      this.monitorAgentOutputStreams(agentId, taskId, timeout);
    } catch (error) {
      this.pendingTasks.delete(taskId);
      throw new Error(`Failed to publish task to Redis: ${error.message}`);
    }

    // Wait for result
    return resultPromise;
  }

  /**
   * Monitor agent output streams for responses
   * Agents publish to streams like stream:mco:event:observation, stream:mco:event:recommendation, etc.
   */
  async monitorAgentOutputStreams(agentId, taskId, timeout) {
    logger.info(`🔍 Starting to monitor agent output stream`, { agentId, taskId, timeout });
    
    const normalizedId = agentId.toLowerCase().replace(/[^a-z0-9-]/g, '-');
    const aliasMap = {
      'ingress-normalization': 'ingress-normalizer',
      'question-router-planner': 'qrp-planner',
      'goal-policy-elicitation': 'goal-policy',
      'counterfactual-experiment': 'counterfactual-experiment',
      'rca-change-detective': 'change-detective-rca',
      'inventory-position': 'inventory-position',
      'capacity-leadtime': 'capacity-leadtime',
      'supply-planning': 'supply-planning',
      'production-scheduling': 'production-scheduling',
      'logistics-allocation': 'logistics-allocation',
      'campaign-sku-mapper': 'campaign-sku-mapper',
      'elasticity-uplift': 'elasticity-uplift'
    };
    const idForStreams = aliasMap[normalizedId] || normalizedId;
    // Per-agent dedicated output stream
    const outputStream = `stream:agent:${idForStreams}:out`;
    
    logger.info(`📡 Monitoring stream for agent`, { agentId, outputStream, normalizedId });
    
    // Set up a one-time listener for this specific task
    const startTime = Date.now();
    let lastReadId = '$'; // read only new messages by default

    // Pre-check recent messages to catch responses published just before listener started
    try {
      const recent = await this.redis.xRevRange(outputStream, '+', '-', { COUNT: 20 });
      if (recent && recent.length > 0) {
        for (const entry of recent) {
          // node-redis v4 returns [id, fields] for raw commands; client wrapper may return {id, message}
          const entryId = Array.isArray(entry) ? entry[0] : entry.id;
          const fields = Array.isArray(entry) ? entry[1] : entry.message;
          const eventId = fields.event_id;
          if (!eventId) continue;
          const eventDataJson = await this.redis.get(`event:${eventId}`);
          if (!eventDataJson) continue;
          const eventData = JSON.parse(eventDataJson);
          const responseTaskId = eventData?.data?.task_id;
          const matchesTask = responseTaskId && responseTaskId === taskId;
          if (matchesTask) {
            const pending = this.pendingTasks.get(taskId);
            if (pending) {
              // Remove from pending tasks FIRST to prevent race conditions
              this.pendingTasks.delete(taskId);
              clearTimeout(pending.timeout);
              
              const result = eventData.data.result || eventData.data;
              const status = eventData.data.status || 'success';
              if (status === 'error') {
                const errorMsg = eventData.data.error || result;
                pending.resolve({ success: false, result: { output: typeof result === 'string' ? result : JSON.stringify(result), agent: agentId, eventId, taskId: responseTaskId || taskId, error: errorMsg }, taskId, agentId });
              } else {
                pending.resolve({ success: status === 'success', result: { output: typeof result === 'string' ? result : JSON.stringify(result), agent: agentId, eventId, taskId: responseTaskId || taskId }, taskId, agentId });
              }
            }
            return; // resolved from pre-check
          }
          lastReadId = entryId; // set baseline to last seen id
        }
      }
    } catch (_) {
      // ignore pre-check errors
    }
    
    const checkInterval = setInterval(async () => {
      try {
        // Check if task already resolved
        if (!this.pendingTasks.has(taskId)) {
          clearInterval(checkInterval);
          return;
        }
        
        // Check if timeout exceeded
        if (Date.now() - startTime > timeout) {
          clearInterval(checkInterval);
          logger.warn(`⏱️ Timeout waiting for agent response`, { agentId, taskId, outputStream });
          return;
        }
        
        // Poll recent entries to avoid missing responses due to read races
        try {
          const recent = await this.redis.xRevRange(outputStream, '+', '-', { COUNT: 50 });
          if (recent && recent.length > 0) {
            for (const entry of recent) {
              const entryId = Array.isArray(entry) ? entry[0] : entry.id;
              const fields = Array.isArray(entry) ? entry[1] : entry.message;
              const eventId = fields?.event_id;
              if (!eventId) continue;
              const eventDataJson = await this.redis.get(`event:${eventId}`);
              if (!eventDataJson) continue;
              const eventData = JSON.parse(eventDataJson);
              const responseTaskId = eventData?.data?.task_id;
              const matchesTask = responseTaskId && responseTaskId === taskId;
              
              logger.info(`🔍 Checking response`, { 
                taskId, 
                responseTaskId, 
                matchesTask,
                eventId,
                agentId
              });
              
              if (matchesTask) {
                logger.info(`✅ Found matching response for task`, { taskId, agentId, eventId, responseTaskId });
                const pending = this.pendingTasks.get(taskId);
                if (pending) {
                  // Remove from pending tasks FIRST to prevent race conditions
                  this.pendingTasks.delete(taskId);
                  clearInterval(checkInterval);
                  clearTimeout(pending.timeout);
                  
                  const result = eventData.data.result || eventData.data;
                  const status = eventData.data.status || 'success';
                  if (status === 'error') {
                    const errorMsg = eventData.data.error || result;
                    pending.resolve({ success: false, result: { output: typeof result === 'string' ? result : JSON.stringify(result), agent: agentId, eventId, taskId: responseTaskId || taskId, error: errorMsg }, taskId, agentId });
                  } else {
                    pending.resolve({ success: status === 'success', result: { output: typeof result === 'string' ? result : JSON.stringify(result), agent: agentId, eventId, taskId: responseTaskId || taskId }, taskId, agentId });
                  }
                  return; // Exit interval when match found
                }
                // If pending task already resolved, continue polling (shouldn't happen but be safe)
                return;
              }
              lastReadId = entryId;
            }
          }
        } catch (error) {
          logger.debug('Error polling recent entries', { error: error.message, agentId, taskId });
        }
        // Continue polling - don't return here!
      } catch (error) {
        // Ignore errors in monitoring loop
        logger.debug('Error monitoring agent output stream', { error: error.message });
      }
    }, 500); // Check every 500ms
  }

  /**
   * Execute multiple agents in parallel
   * @param {Array} agentTasks - Array of {agentId, task}
   * @returns {Promise<Array>} Array of results
   */
  async executeAgentsParallel(agentTasks) {
    logger.info(`🚀 Executing ${agentTasks.length} agents in parallel`);
    
    const promises = agentTasks.map(({ agentId, task }) =>
      this.executeAgent(agentId, task).catch(error => ({
        success: false,
        agentId,
        error: error.message
      }))
    );

    return await Promise.all(promises);
  }

  /**
   * Execute agents sequentially (for dependencies)
   * @param {Array} agentTasks - Array of {agentId, task, dependsOn}
   * @returns {Promise<Array>} Array of results
   */
  async executeAgentsSequential(agentTasks) {
    logger.info(`⏭️ Executing ${agentTasks.length} agents sequentially`);
    
    const results = [];
    const completedTasks = new Map();

    for (const { agentId, task, dependsOn } of agentTasks) {
      // Wait for dependencies
      if (dependsOn && dependsOn.length > 0) {
        const missingDeps = dependsOn.filter(dep => !completedTasks.has(dep));
        if (missingDeps.length > 0) {
          logger.warn(`⚠️ Task depends on incomplete tasks`, { agentId, missingDeps });
        }
      }

      try {
        const result = await this.executeAgent(agentId, task);
        results.push({ success: true, agentId, result });
        completedTasks.set(task.id, result);
      } catch (error) {
        logger.error(`❌ Agent execution failed`, { agentId, error: error.message });
        results.push({ success: false, agentId, error: error.message });
      }
    }

    return results;
  }

  /**
   * Start listening for agent responses from Redis
   */
  async startResponseListener() {
    const responseStream = 'stream:crewai:responses';
    
    logger.info(`👂 Starting CrewAI response listener on ${responseStream}`);

    // Create consumer group
    try {
      await this.redis.xGroupCreate(responseStream, 'nodejs-backend', '$', {
        MKSTREAM: true
      });
    } catch (error) {
      if (!error.message.includes('BUSYGROUP')) {
        logger.error('Failed to create consumer group:', { error: error.message });
      }
    }

    // Start consuming responses
    this.listenForResponses(responseStream);
  }

  /**
   * Listen for agent responses (runs continuously)
   */
  async listenForResponses(streamName) {
    const consumerName = `consumer-${process.pid}`;
    
    while (this.isHealthy()) {
      try {
        // Read messages from stream
        const messages = await this.redis.xReadGroup(
          'nodejs-backend',
          consumerName,
          [{ key: streamName, id: '>' }],
          {
            COUNT: 10,
            BLOCK: 2000 // Block for 2 seconds
          }
        );

        if (!messages || messages.length === 0) {
          continue;
        }

        // Process each message
        for (const [stream, entries] of messages) {
          for (const { id, message } of entries) {
            await this.handleAgentResponse(id, message, streamName);
          }
        }
      } catch (error) {
        if (error.message !== 'Connection is closed.') {
          logger.error('Error reading from response stream:', { error: error.message });
        }
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
    }
  }

  /**
   * Handle an agent response message
   */
  async handleAgentResponse(messageId, message, streamName) {
    try {
      const taskId = message.task_id;
      const status = message.status;
      const result = message.result ? JSON.parse(message.result) : null;
      const error = message.error;

      logger.info(`📨 Received agent response`, {
        taskId,
        status,
        messageId
      });

      // Find pending task
      const pending = this.pendingTasks.get(taskId);
      if (!pending) {
        logger.warn(`⚠️ Received response for unknown task`, { taskId });
        // Acknowledge anyway to prevent redelivery
        await this.redis.xAck(streamName, 'nodejs-backend', messageId);
        return;
      }

      // Clear timeout
      clearTimeout(pending.timeout);
      this.pendingTasks.delete(taskId);

      // Resolve or reject promise
      if (status === 'success') {
        pending.resolve({
          success: true,
          result,
          taskId,
          agentId: message.agent_id
        });
      } else {
        pending.reject(new Error(error || 'Agent execution failed'));
      }

      // Acknowledge message
      await this.redis.xAck(streamName, 'nodejs-backend', messageId);
      
    } catch (error) {
      logger.error('Error handling agent response:', { error: error.message });
    }
  }

  /**
   * Check if a Python agent is available
   * @param {string} agentId - Agent identifier
   * @returns {Promise<boolean>} True if agent is available
   */
  async isAgentAvailable(agentId) {
    if (!this.isHealthy()) {
      return false;
    }

    try {
      // Check if agent has a heartbeat
      const heartbeatKey = `crewai:agent:${agentId}:heartbeat`;
      const heartbeat = await this.redis.get(heartbeatKey);
      
      if (!heartbeat) {
        return false;
      }

      // Check if heartbeat is recent (within last 60 seconds)
      const heartbeatTime = new Date(heartbeat);
      const now = new Date();
      const age = (now - heartbeatTime) / 1000;
      
      return age < 60;
    } catch (error) {
      logger.error('Error checking agent availability:', { agentId, error: error.message });
      return false;
    }
  }

  /**
   * Get list of available Python agents
   * @returns {Promise<Array>} List of available agent IDs
   */
  async getAvailableAgents() {
    if (!this.isHealthy()) {
      return [];
    }

    try {
      // Scan for heartbeat keys
      const keys = await this.redis.keys('crewai:agent:*:heartbeat');
      const agents = keys.map(key => {
        const match = key.match(/crewai:agent:(.+):heartbeat/);
        return match ? match[1] : null;
      }).filter(Boolean);

      return agents;
    } catch (error) {
      logger.error('Error getting available agents:', { error: error.message });
      return [];
    }
  }

  /**
   * Shutdown the bridge service
   */
  async shutdown() {
    logger.info('🛑 Shutting down CrewAI Bridge Service');
    
    // Reject all pending tasks
    for (const [taskId, pending] of this.pendingTasks.entries()) {
      clearTimeout(pending.timeout);
      pending.reject(new Error('Service shutting down'));
    }
    this.pendingTasks.clear();

    if (this.redis) {
      await this.redis.quit();
    }
  }
}

