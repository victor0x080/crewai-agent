/**
 * Decision Stack API Routes
 * Provides CRUD operations for decision stacks
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
 * GET /api/decision-stacks
 * Get all decision stacks
 */
router.get('/', async (req, res) => {
  try {
    const stackKeys = await redis.keys('decision-stack:*');
    const stacks = [];
    
    for (const key of stackKeys) {
      const stackData = await redis.get(key);
      if (stackData) {
        try {
          const stack = JSON.parse(stackData);
          stacks.push(stack);
        } catch (e) {
          logger.warn(`[DecisionStackRoutes] Invalid JSON for ${key}:`, e);
        }
      }
    }

    // Sort by lastModified (newest first)
    stacks.sort((a, b) => {
      const dateA = new Date(a.lastModified || 0);
      const dateB = new Date(b.lastModified || 0);
      return dateB - dateA;
    });

    res.json({ stacks });
  } catch (error) {
    logger.error('[DecisionStackRoutes] Error fetching stacks:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * GET /api/decision-stacks/:stackId
 * Get a specific decision stack
 */
router.get('/:stackId', async (req, res) => {
  try {
    const { stackId } = req.params;
    const stackData = await redis.get(`decision-stack:${stackId}`);
    
    if (!stackData) {
      return res.status(404).json({ error: 'Decision stack not found' });
    }

    const stack = JSON.parse(stackData);
    res.json(stack);
  } catch (error) {
    logger.error('[DecisionStackRoutes] Error fetching stack:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * POST /api/decision-stacks
 * Create a new decision stack
 */
router.post('/', async (req, res) => {
  try {
    const {
      name,
      description,
      template,
      status = 'draft',
      modules = {
        commonTerms: 0,
        eventPatterns: 0,
        tunedModels: 0,
        entityMap: 0,
        playsWorkflows: 0,
        promptTemplates: 0
      }
    } = req.body;

    if (!name || !description) {
      return res.status(400).json({ error: 'name and description are required' });
    }

    const stackId = `stack-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
    const stack = {
      id: stackId,
      name,
      description,
      status,
      version: '0.1.0',
      lastModified: new Date().toISOString().split('T')[0],
      template: template || 'Custom',
      modules
    };

    await redis.set(`decision-stack:${stackId}`, JSON.stringify(stack));
    
    // Publish event
    await redis.xadd('mesh:events', '*',
      'type', 'decision-stack.created',
      'stackId', stackId,
      'timestamp', new Date().toISOString()
    );

    res.status(201).json(stack);
  } catch (error) {
    logger.error('[DecisionStackRoutes] Error creating stack:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * PUT /api/decision-stacks/:stackId
 * Update a decision stack
 */
router.put('/:stackId', async (req, res) => {
  try {
    const { stackId } = req.params;
    const existingData = await redis.get(`decision-stack:${stackId}`);
    
    if (!existingData) {
      return res.status(404).json({ error: 'Decision stack not found' });
    }

    const existing = JSON.parse(existingData);
    const updates = req.body;
    
    // Merge updates
    const updated = {
      ...existing,
      ...updates,
      id: stackId, // Prevent ID changes
      lastModified: new Date().toISOString().split('T')[0]
    };

    // Increment version if status changed to active
    if (updates.status === 'active' && existing.status !== 'active') {
      const versionParts = updated.version.split('.');
      versionParts[1] = String(parseInt(versionParts[1]) + 1);
      updated.version = versionParts.join('.');
    }

    await redis.set(`decision-stack:${stackId}`, JSON.stringify(updated));
    
    // Publish event
    await redis.xadd('mesh:events', '*',
      'type', 'decision-stack.updated',
      'stackId', stackId,
      'timestamp', new Date().toISOString()
    );

    res.json(updated);
  } catch (error) {
    logger.error('[DecisionStackRoutes] Error updating stack:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * DELETE /api/decision-stacks/:stackId
 * Delete a decision stack
 */
router.delete('/:stackId', async (req, res) => {
  try {
    const { stackId } = req.params;
    const exists = await redis.exists(`decision-stack:${stackId}`);
    
    if (!exists) {
      return res.status(404).json({ error: 'Decision stack not found' });
    }

    await redis.del(`decision-stack:${stackId}`);
    
    // Publish event
    await redis.xadd('mesh:events', '*',
      'type', 'decision-stack.deleted',
      'stackId', stackId,
      'timestamp', new Date().toISOString()
    );

    res.json({ success: true, message: 'Decision stack deleted' });
  } catch (error) {
    logger.error('[DecisionStackRoutes] Error deleting stack:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * POST /api/decision-stacks/:stackId/clone
 * Clone a decision stack
 */
router.post('/:stackId/clone', async (req, res) => {
  try {
    const { stackId } = req.params;
    const existingData = await redis.get(`decision-stack:${stackId}`);
    
    if (!existingData) {
      return res.status(404).json({ error: 'Decision stack not found' });
    }

    const existing = JSON.parse(existingData);
    const newStackId = `stack-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
    
    const cloned = {
      ...existing,
      id: newStackId,
      name: `${existing.name} (Copy)`,
      status: 'draft',
      version: '0.1.0',
      lastModified: new Date().toISOString().split('T')[0]
    };

    await redis.set(`decision-stack:${newStackId}`, JSON.stringify(cloned));
    
    res.status(201).json(cloned);
  } catch (error) {
    logger.error('[DecisionStackRoutes] Error cloning stack:', error);
    res.status(500).json({ error: error.message });
  }
});

export default router;

