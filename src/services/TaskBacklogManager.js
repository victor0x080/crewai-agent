/**
 * Task Backlog Manager
 * Manages task queuing, prioritization, and execution tracking for agent orchestration
 */

import { createClient as createRedisClient } from 'redis';
import config from '../config/index.js';
import { logger } from '../utils/logger.js';
import { v4 as uuidv4 } from 'uuid';

export default class TaskBacklogManager {
  constructor() {
    this.redis = null;
    this.healthy = false;
    this.maxConcurrentTasks = config.backlog?.maxConcurrent || 10;
    this.taskTimeout = config.backlog?.taskTimeout || 300000; // 5 minutes
    this.activeTasks = new Map();
    this.metrics = {
      totalProcessed: 0,
      totalFailed: 0,
      averageWaitTime: 0,
      averageProcessingTime: 0
    };
  }

  async initialize() {
    if (!config.redis.enabled) {
      logger.warn('Redis not enabled, TaskBacklogManager will operate in memory only');
      this.healthy = true;
      return;
    }

    try {
      this.redis = createRedisClient({
        url: `redis://${config.redis.host}:${config.redis.port}`,
        password: config.redis.password
      });

      this.redis.on('error', (err) => {
        if (err.code !== 'ECONNREFUSED') {
          logger.error('Redis client error in TaskBacklogManager:', { error: err.message });
        }
      });

      await this.redis.connect();
      this.healthy = true;
      
      // Start background worker
      this.startBackgroundWorker();
      
      logger.info('✅ TaskBacklogManager initialized with Redis');
    } catch (error) {
      logger.error('❌ TaskBacklogManager initialization failed', { error: error.message });
      this.healthy = false;
    }
  }

  /**
   * Add task to backlog
   * @param {object} task - Task details
   * @returns {Promise<string>} taskId
   */
  async enqueueTask(task) {
    const taskId = task.id || uuidv4();
    const priority = task.priority || 'medium';
    const timestamp = Date.now();

    const taskData = {
      id: taskId,
      type: task.type || 'agent_orchestration',
      query: task.query,
      intent: task.intent,
      agents: task.agents || [],
      context: task.context || {},
      priority,
      status: 'pending',
      enqueuedAt: timestamp,
      userId: task.userId,
      conversationId: task.conversationId,
      tenantId: task.tenantId,
      metadata: task.metadata || {}
    };

    if (this.redis && this.healthy) {
      // Use Redis Sorted Set for priority queue
      const queueKey = 'task:backlog:queue';
      const taskKey = `task:backlog:${taskId}`;
      
      // Store task data
      await this.redis.set(taskKey, JSON.stringify(taskData), {
        EX: 3600 // Expire in 1 hour
      });

      // Add to priority queue (lower score = higher priority)
      const score = this.calculatePriorityScore(priority, timestamp);
      await this.redis.zAdd(queueKey, { score, value: taskId });

      logger.info('📥 Task enqueued', { taskId, priority, queuePosition: await this.getQueuePosition(taskId) });
    } else {
      // In-memory fallback
      this.activeTasks.set(taskId, taskData);
      logger.info('📥 Task enqueued (in-memory)', { taskId, priority });
    }

    return taskId;
  }

  /**
   * Calculate priority score (lower = higher priority)
   */
  calculatePriorityScore(priority, timestamp) {
    const priorityWeights = {
      critical: 1,
      high: 2,
      medium: 3,
      low: 4
    };
    
    const weight = priorityWeights[priority] || 3;
    // Score = (priority_weight * 1000000) + timestamp
    // This ensures priority ordering, with FIFO as tiebreaker
    return (weight * 1000000) + timestamp;
  }

  /**
   * Dequeue next task from backlog
   * @returns {Promise<object|null>} task or null
   */
  async dequeueTask() {
    if (this.redis && this.healthy) {
      const queueKey = 'task:backlog:queue';
      
      // Get highest priority task (lowest score)
      const tasks = await this.redis.zRangeWithScores(queueKey, 0, 0);
      
      if (tasks.length === 0) {
        return null;
      }

      const { value: taskId, score } = tasks[0];
      
      // Remove from queue
      await this.redis.zRem(queueKey, taskId);
      
      // Get task data
      const taskKey = `task:backlog:${taskId}`;
      const taskDataStr = await this.redis.get(taskKey);
      
      if (!taskDataStr) {
        logger.warn('Task data not found', { taskId });
        return null;
      }

      const task = JSON.parse(taskDataStr);
      task.dequeuedAt = Date.now();
      task.status = 'processing';
      
      // Update task status
      await this.redis.set(taskKey, JSON.stringify(task), { EX: 3600 });
      
      // Track active task
      this.activeTasks.set(taskId, task);
      
      logger.info('📤 Task dequeued', { 
        taskId, 
        waitTime: task.dequeuedAt - task.enqueuedAt 
      });
      
      return task;
    } else {
      // In-memory fallback - get first task
      const taskId = this.activeTasks.keys().next().value;
      if (!taskId) return null;
      
      const task = this.activeTasks.get(taskId);
      task.dequeuedAt = Date.now();
      task.status = 'processing';
      
      return task;
    }
  }

  /**
   * Mark task as completed
   */
  async completeTask(taskId, result) {
    const task = this.activeTasks.get(taskId);
    if (!task) {
      logger.warn('Task not found in active tasks', { taskId });
      return;
    }

    const completedAt = Date.now();
    const processingTime = completedAt - (task.dequeuedAt || task.enqueuedAt);
    const waitTime = (task.dequeuedAt || task.enqueuedAt) - task.enqueuedAt;

    // Update metrics
    this.metrics.totalProcessed++;
    this.metrics.averageProcessingTime = 
      (this.metrics.averageProcessingTime * (this.metrics.totalProcessed - 1) + processingTime) / 
      this.metrics.totalProcessed;
    this.metrics.averageWaitTime = 
      (this.metrics.averageWaitTime * (this.metrics.totalProcessed - 1) + waitTime) / 
      this.metrics.totalProcessed;

    if (this.redis && this.healthy) {
      const taskKey = `task:backlog:${taskId}`;
      const updatedTask = {
        ...task,
        status: 'completed',
        completedAt,
        result: result ? JSON.stringify(result).substring(0, 1000) : null, // Store summary
        processingTime,
        waitTime
      };
      
      await this.redis.set(taskKey, JSON.stringify(updatedTask), { EX: 3600 });
      
      // Store in completed tasks list (for analytics)
      await this.redis.lPush('task:backlog:completed', taskId);
      await this.redis.lTrim('task:backlog:completed', 0, 999); // Keep last 1000
    }

    this.activeTasks.delete(taskId);
    
    logger.info('✅ Task completed', { 
      taskId, 
      processingTime: `${processingTime}ms`,
      waitTime: `${waitTime}ms`
    });
  }

  /**
   * Mark task as failed
   */
  async failTask(taskId, error) {
    const task = this.activeTasks.get(taskId);
    if (!task) {
      logger.warn('Task not found in active tasks', { taskId });
      return;
    }

    const failedAt = Date.now();
    this.metrics.totalFailed++;

    if (this.redis && this.healthy) {
      const taskKey = `task:backlog:${taskId}`;
      const updatedTask = {
        ...task,
        status: 'failed',
        failedAt,
        error: error.message || String(error),
        processingTime: failedAt - (task.dequeuedAt || task.enqueuedAt)
      };
      
      await this.redis.set(taskKey, JSON.stringify(updatedTask), { EX: 3600 });
      
      // Store in failed tasks list (for troubleshooting)
      await this.redis.lPush('task:backlog:failed', taskId);
      await this.redis.lTrim('task:backlog:failed', 0, 99); // Keep last 100
    }

    this.activeTasks.delete(taskId);
    
    logger.error('❌ Task failed', { 
      taskId, 
      error: error.message || String(error)
    });
  }

  /**
   * Get current queue position for a task
   */
  async getQueuePosition(taskId) {
    if (this.redis && this.healthy) {
      const queueKey = 'task:backlog:queue';
      const rank = await this.redis.zRank(queueKey, taskId);
      return rank !== null ? rank + 1 : null;
    }
    return null;
  }

  /**
   * Get queue status
   */
  async getQueueStatus() {
    if (this.redis && this.healthy) {
      const queueKey = 'task:backlog:queue';
      const queueSize = await this.redis.zCard(queueKey);
      
      // Get tasks by priority
      const allTasks = await this.redis.zRangeWithScores(queueKey, 0, -1);
      
      const priorityBreakdown = {
        critical: 0,
        high: 0,
        medium: 0,
        low: 0
      };
      
      for (const { value: taskId } of allTasks) {
        const taskKey = `task:backlog:${taskId}`;
        const taskDataStr = await this.redis.get(taskKey);
        if (taskDataStr) {
          const task = JSON.parse(taskDataStr);
          priorityBreakdown[task.priority] = (priorityBreakdown[task.priority] || 0) + 1;
        }
      }
      
      return {
        queueSize,
        activeTasks: this.activeTasks.size,
        maxConcurrent: this.maxConcurrentTasks,
        priorityBreakdown,
        metrics: this.metrics
      };
    } else {
      return {
        queueSize: this.activeTasks.size,
        activeTasks: this.activeTasks.size,
        maxConcurrent: this.maxConcurrentTasks,
        priorityBreakdown: {},
        metrics: this.metrics
      };
    }
  }

  /**
   * Get task status
   */
  async getTaskStatus(taskId) {
    if (this.redis && this.healthy) {
      const taskKey = `task:backlog:${taskId}`;
      const taskDataStr = await this.redis.get(taskKey);
      
      if (!taskDataStr) {
        return { status: 'not_found' };
      }

      const task = JSON.parse(taskDataStr);
      const queuePosition = await this.getQueuePosition(taskId);
      
      return {
        ...task,
        queuePosition,
        estimatedWaitTime: queuePosition ? queuePosition * this.metrics.averageProcessingTime : 0
      };
    } else {
      const task = this.activeTasks.get(taskId);
      return task ? { ...task, queuePosition: null } : { status: 'not_found' };
    }
  }

  /**
   * Background worker to process queue
   */
  async startBackgroundWorker() {
    logger.info('🔄 Starting background task worker');
    
    setInterval(async () => {
      // Only process if we're below max concurrent limit
      if (this.activeTasks.size >= this.maxConcurrentTasks) {
        return;
      }

      // Check for stale tasks (timeout)
      const now = Date.now();
      for (const [taskId, task] of this.activeTasks.entries()) {
        if (task.status === 'processing') {
          const processingTime = now - (task.dequeuedAt || task.enqueuedAt);
          if (processingTime > this.taskTimeout) {
            logger.warn('⏱️ Task timeout', { taskId, processingTime });
            await this.failTask(taskId, new Error('Task timeout'));
          }
        }
      }
    }, 5000); // Check every 5 seconds
  }

  /**
   * Clear completed tasks (cleanup)
   */
  async clearCompleted() {
    if (this.redis && this.healthy) {
      await this.redis.del('task:backlog:completed');
      logger.info('🗑️ Cleared completed tasks');
    }
  }

  /**
   * Shutdown
   */
  async shutdown() {
    logger.info('🛑 Shutting down TaskBacklogManager');
    
    if (this.redis) {
      await this.redis.quit();
    }
  }
}

