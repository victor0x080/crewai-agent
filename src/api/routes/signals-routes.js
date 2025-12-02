/**
 * Signals/Mesh Configuration API Routes
 * Provides endpoints for managing signals, agents, and mesh configuration
 */

import express from 'express';
import Redis from 'ioredis';
import { logger } from '../../utils/logger.js';

const router = express.Router();

// Initialize Redis client
const redis = new Redis({
  host: process.env.REDIS_HOST || 'localhost',
  port: parseInt(process.env.REDIS_PORT || '6379'),
  db: 0,
});

/**
 * GET /api/signals
 * Get all available signals with their status
 */
router.get('/', async (req, res) => {
  try {
    // Get active agents from Redis
    const agentKeys = await redis.keys('agent:*:status');
    const activeAgents = [];
    
    for (const key of agentKeys) {
      const status = await redis.get(key);
      const agentId = key.replace('agent:', '').replace(':status', '');
      const agentData = await redis.get(`agent:${agentId}:data`);
      
      if (status === 'active' && agentData) {
        try {
          activeAgents.push(JSON.parse(agentData));
        } catch (e) {
          // Skip invalid JSON
        }
      }
    }

    // Get signal configurations from Redis
    const signalKeys = await redis.keys('signal:*:config');
    const signals = [];
    
    for (const key of signalKeys) {
      const config = await redis.get(key);
      if (config) {
        try {
          const signalConfig = JSON.parse(config);
          const signalId = key.replace('signal:', '').replace(':config', '');
          signals.push({
            id: signalId,
            ...signalConfig,
            activeAgents: activeAgents.filter(a => a.signalId === signalId)
          });
        } catch (e) {
          // Skip invalid JSON
        }
      }
    }

    res.json({ signals, activeAgents });
  } catch (error) {
    logger.error('[SignalsRoutes] Error fetching signals:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * GET /api/signals/agents
 * Get all active agents
 */
router.get('/agents', async (req, res) => {
  try {
    const agentKeys = await redis.keys('agent:*:data');
    const agents = [];
    
    for (const key of agentKeys) {
      const agentData = await redis.get(key);
      if (agentData) {
        try {
          agents.push(JSON.parse(agentData));
        } catch (e) {
          // Skip invalid JSON
        }
      }
    }

    res.json({ agents, count: agents.length });
  } catch (error) {
    logger.error('[SignalsRoutes] Error fetching agents:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * GET /api/signals/agents/stats
 * Get agent statistics including CrewAI agents with heartbeats
 */
router.get('/agents/stats', async (req, res) => {
  try {
    // Check for CrewAI agent heartbeats
    const heartbeatKeys = await redis.keys('crewai:agent:*:heartbeat');
    const activeCrewAIAgents = [];
    
    for (const key of heartbeatKeys) {
      const heartbeat = await redis.get(key);
      if (heartbeat) {
        // Check if heartbeat is recent (within last 60 seconds)
        const heartbeatTime = new Date(heartbeat);
        const now = new Date();
        const age = (now - heartbeatTime) / 1000;
        
        if (age < 60) {
          // Extract agent ID from key: crewai:agent:{agentId}:heartbeat
          const match = key.match(/crewai:agent:(.+):heartbeat/);
          if (match) {
            const agentId = match[1];
            activeCrewAIAgents.push({
              id: agentId,
              name: agentId.split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' '),
              type: 'crewai',
              status: 'active',
              lastHeartbeat: heartbeat,
              age: Math.round(age)
            });
          }
        }
      }
    }

    // Get regular agents from agent:*:data
    const agentKeys = await redis.keys('agent:*:data');
    const regularAgents = [];
    
    for (const key of agentKeys) {
      const agentData = await redis.get(key);
      if (agentData) {
        try {
          regularAgents.push(JSON.parse(agentData));
        } catch (e) {
          // Skip invalid JSON
        }
      }
    }

    // Combine both types
    const allAgents = [...activeCrewAIAgents, ...regularAgents];
    
    // Calculate statistics
    const agentsByType = {};
    const agentsBySignal = {};
    
    allAgents.forEach(agent => {
      const type = agent.type || 'unknown';
      agentsByType[type] = (agentsByType[type] || 0) + 1;
      
      if (agent.signalId) {
        agentsBySignal[agent.signalId] = (agentsBySignal[agent.signalId] || 0) + 1;
      }
    });

    res.json({
      totalActiveAgents: allAgents.length,
      totalAgentTemplates: agentKeys.length,
      averageConfidence: 0.85, // Placeholder
      agentsBySignal,
      agentsByType,
      agents: allAgents
    });
  } catch (error) {
    logger.error('[SignalsRoutes] Error fetching agent stats:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * GET /api/signals/metrics
 * Get signal metrics (events today, active agents, etc.)
 */
router.get('/metrics', async (req, res) => {
  try {
    // Count events in mesh:events stream today
    const today = new Date().toISOString().split('T')[0];
    const streamMessages = await redis.xrange('mesh:events', '-', '+', 'COUNT', 1000);
    const todayEvents = streamMessages.filter(msg => {
      const timestamp = msg[1].find(f => f[0] === 'timestamp')?.[1] || '';
      return timestamp.startsWith(today);
    });

    // Count active agents
    const activeAgentKeys = await redis.keys('agent:*:status');
    const activeAgents = await Promise.all(
      activeAgentKeys.map(async (key) => {
        const status = await redis.get(key);
        return status === 'active' ? 1 : 0;
      })
    );
    const activeAgentCount = activeAgents.reduce((a, b) => a + b, 0);

    // Count enabled signals
    const signalKeys = await redis.keys('signal:*:config');
    const enabledSignals = await Promise.all(
      signalKeys.map(async (key) => {
        const config = await redis.get(key);
        if (config) {
          try {
            const signalConfig = JSON.parse(config);
            return signalConfig.enabled ? 1 : 0;
          } catch (e) {
            return 0;
          }
        }
        return 0;
      })
    );
    const enabledSignalCount = enabledSignals.reduce((a, b) => a + b, 0);

    res.json({
      totalEventsToday: todayEvents.length,
      activeAgents: activeAgentCount,
      enabledSignals: enabledSignalCount,
      totalSignals: signalKeys.length
    });
  } catch (error) {
    logger.error('[SignalsRoutes] Error fetching metrics:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * GET /api/signals/:signalId
 * Get a specific signal configuration
 */
router.get('/:signalId', async (req, res) => {
  try {
    const { signalId } = req.params;
    const config = await redis.get(`signal:${signalId}:config`);
    
    if (!config) {
      return res.status(404).json({ error: 'Signal not found' });
    }

    const signalConfig = JSON.parse(config);
    res.json({ id: signalId, ...signalConfig });
  } catch (error) {
    logger.error('[SignalsRoutes] Error fetching signal:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * POST /api/signals/:signalId/enable
 * Enable a signal
 */
router.post('/:signalId/enable', async (req, res) => {
  try {
    const { signalId } = req.params;
    const { filters } = req.body;
    
    const configKey = `signal:${signalId}:config`;
    let config = await redis.get(configKey);
    
    if (!config) {
      // Create new signal config
      config = {
        enabled: true,
        status: 'active',
        filters: filters || {},
        updatedAt: new Date().toISOString()
      };
    } else {
      config = JSON.parse(config);
      config.enabled = true;
      config.status = 'active';
      if (filters) config.filters = filters;
      config.updatedAt = new Date().toISOString();
    }

    await redis.set(configKey, JSON.stringify(config));
    
    // Publish event to mesh
    await redis.xadd('mesh:events', '*',
      'type', 'signal.enabled',
      'signalId', signalId,
      'timestamp', new Date().toISOString()
    );

    res.json({ id: signalId, ...config });
  } catch (error) {
    logger.error('[SignalsRoutes] Error enabling signal:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * POST /api/signals/:signalId/disable
 * Disable a signal
 */
router.post('/:signalId/disable', async (req, res) => {
  try {
    const { signalId } = req.params;
    const configKey = `signal:${signalId}:config`;
    const config = await redis.get(configKey);
    
    if (!config) {
      return res.status(404).json({ error: 'Signal not found' });
    }

    const signalConfig = JSON.parse(config);
    signalConfig.enabled = false;
    signalConfig.status = 'inactive';
    signalConfig.updatedAt = new Date().toISOString();

    await redis.set(configKey, JSON.stringify(signalConfig));
    
    // Publish event to mesh
    await redis.xadd('mesh:events', '*',
      'type', 'signal.disabled',
      'signalId', signalId,
      'timestamp', new Date().toISOString()
    );

    res.json({ id: signalId, ...signalConfig });
  } catch (error) {
    logger.error('[SignalsRoutes] Error disabling signal:', error);
    res.status(500).json({ error: error.message });
  }
});

export default router;

