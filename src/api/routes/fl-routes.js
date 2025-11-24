/**
 * Federated Learning REST API Routes
 * 
 * Provides HTTP endpoints for:
 * - FL run management (create, status, metrics)
 * - Client registration
 * - Model registry operations
 * - Inference (real-time and batch)
 * - Monitoring and observability
 * 
 * Integrates with:
 * - Redis Streams for async operations
 * - CloudEvents for event publishing
 * - Supabase for metadata persistence
 * - Python FL server/client processes
 */

import express from 'express';
import { createClient } from '@supabase/supabase-js';
import Redis from 'ioredis';
import { v4 as uuidv4 } from 'uuid';
import { spawn } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const router = express.Router();

// Initialize clients
const supabase = createClient(
  process.env.SUPABASE_URL || '',
  process.env.SUPABASE_KEY || ''
);

const redis = new Redis({
  host: process.env.REDIS_HOST || 'localhost',
  port: parseInt(process.env.REDIS_PORT || '6379'),
  db: 0,
});

// Track running FL processes
const runningProcesses = new Map();

// ============================================================================
// FL Run Management
// ============================================================================

/**
 * POST /api/fl/runs
 * Create a new federated learning training run
 */
router.post('/runs', async (req, res) => {
  try {
    const {
      run_name,
      dataset_name = 'call_center_csat',
      model_type = 'logistic_regression',
      num_rounds = 5,
      min_clients = 2,
      strategy = 'FedAvg',
      target_metric = 'accuracy',
      privacy_budget = null,
      server_address = '0.0.0.0:8080'
    } = req.body;

    if (!run_name) {
      return res.status(400).json({ error: 'run_name is required' });
    }

    // Generate run ID
    const run_id = `fl_run_${Date.now()}_${uuidv4().substring(0, 8)}`;

    // Create run configuration
    const run_config = {
      run_id,
      run_name,
      dataset_name,
      model_type,
      num_rounds,
      min_clients,
      strategy,
      target_metric,
      privacy_budget,
      server_address,
      status: 'initialized',
      created_at: new Date().toISOString(),
      current_round: 0,
      registered_clients: []
    };

    // Store in Redis
    await redis.set(`fl:run:${run_id}`, JSON.stringify(run_config));

    // Store in Supabase for persistence
    const { data, error } = await supabase
      .from('fl_runs')
      .insert({
        run_id,
        run_name,
        dataset_name,
        model_type,
        num_rounds,
        min_clients,
        strategy,
        target_metric,
        privacy_budget,
        server_address,
        status: 'initialized',
        config: run_config
      })
      .select()
      .single();

    if (error) {
      console.error('Supabase insert error:', error);
      // Continue even if Supabase fails (Redis is source of truth)
    }

    // Publish CloudEvent
    const event_id = `${Date.now()}-${uuidv4().substring(0, 8)}`;
    const cloudevent = {
      specversion: '1.0',
      id: event_id,
      type: 'com.flowerai.fl.run.created',
      source: 'urn:flowerai:api',
      subject: run_id,
      time: new Date().toISOString(),
      datacontenttype: 'application/json',
      dataschema: 'https://schemas.flowerai.com/run.created/1-0-0.json',
      data: run_config
    };

    await redis.set(`event:${event_id}`, JSON.stringify(cloudevent));
    await redis.xadd('fl:events', '*', 
      'event_id', event_id,
      'type', cloudevent.type,
      'subject', run_id,
      'timestamp', cloudevent.time
    );

    res.status(201).json({
      success: true,
      run_id,
      run_config,
      message: `Federated learning run '${run_name}' created`
    });
  } catch (error) {
    console.error('Error creating FL run:', error);
    res.status(500).json({ error: 'Failed to create FL run' });
  }
});

/**
 * GET /api/fl/runs/:runId
 * Get FL run status and configuration
 */
router.get('/runs/:runId', async (req, res) => {
  try {
    const { runId } = req.params;

    // Get from Redis
    const runData = await redis.get(`fl:run:${runId}`);
    
    if (!runData) {
      return res.status(404).json({ error: 'FL run not found' });
    }

    const run_config = JSON.parse(runData);

    // Get registered clients
    const clientKeys = await redis.keys(`fl:client:${runId}:*`);
    const clients = await Promise.all(
      clientKeys.map(async (key) => {
        const clientData = await redis.get(key);
        return clientData ? JSON.parse(clientData) : null;
      })
    );

    res.json({
      success: true,
      run_config,
      clients: clients.filter(c => c !== null)
    });
  } catch (error) {
    console.error('Error fetching FL run:', error);
    res.status(500).json({ error: 'Failed to fetch FL run' });
  }
});

/**
 * POST /api/fl/runs/:runId/start
 * Start FL server for a run
 */
router.post('/runs/:runId/start', async (req, res) => {
  try {
    const { runId } = req.params;

    // Check if already running
    if (runningProcesses.has(runId)) {
      return res.status(400).json({ error: 'FL server already running for this run' });
    }

    // Get run config
    const runData = await redis.get(`fl:run:${runId}`);
    if (!runData) {
      return res.status(404).json({ error: 'FL run not found' });
    }

    const run_config = JSON.parse(runData);

    // Start FL server process
    const pythonPath = path.join(__dirname, '../../../agents/crewai_python/federated/fl_server.py');
    const serverProcess = spawn('python', [
      pythonPath,
      '--run-id', runId,
      '--num-rounds', run_config.num_rounds.toString(),
      '--min-clients', run_config.min_clients.toString(),
      '--min-available', run_config.min_clients.toString(),
      '--server-address', run_config.server_address
    ]);

    runningProcesses.set(runId, serverProcess);

    // Handle process output
    serverProcess.stdout.on('data', (data) => {
      console.log(`[FL Server ${runId}] ${data}`);
    });

    serverProcess.stderr.on('data', (data) => {
      console.error(`[FL Server ${runId}] ERROR: ${data}`);
    });

    serverProcess.on('close', (code) => {
      console.log(`[FL Server ${runId}] Process exited with code ${code}`);
      runningProcesses.delete(runId);
    });

    // Update status
    run_config.status = 'running';
    run_config.started_at = new Date().toISOString();
    await redis.set(`fl:run:${runId}`, JSON.stringify(run_config));

    res.json({
      success: true,
      run_id: runId,
      status: 'running',
      message: 'FL server started'
    });
  } catch (error) {
    console.error('Error starting FL server:', error);
    res.status(500).json({ error: 'Failed to start FL server' });
  }
});

/**
 * POST /api/fl/runs/:runId/stop
 * Stop FL server for a run
 */
router.post('/runs/:runId/stop', async (req, res) => {
  try {
    const { runId } = req.params;

    const serverProcess = runningProcesses.get(runId);
    if (!serverProcess) {
      return res.status(404).json({ error: 'No running FL server found for this run' });
    }

    serverProcess.kill('SIGTERM');
    runningProcesses.delete(runId);

    // Update status
    const runData = await redis.get(`fl:run:${runId}`);
    if (runData) {
      const run_config = JSON.parse(runData);
      run_config.status = 'stopped';
      run_config.stopped_at = new Date().toISOString();
      await redis.set(`fl:run:${runId}`, JSON.stringify(run_config));
    }

    res.json({
      success: true,
      run_id: runId,
      status: 'stopped',
      message: 'FL server stopped'
    });
  } catch (error) {
    console.error('Error stopping FL server:', error);
    res.status(500).json({ error: 'Failed to stop FL server' });
  }
});

// ============================================================================
// Client Management
// ============================================================================

/**
 * POST /api/fl/runs/:runId/clients
 * Register a federated learning client
 */
router.post('/runs/:runId/clients', async (req, res) => {
  try {
    const { runId } = req.params;
    const {
      client_id,
      client_name,
      data_silo_size,
      data_features,
      metadata = {}
    } = req.body;

    if (!client_id || !client_name || !data_silo_size || !data_features) {
      return res.status(400).json({ 
        error: 'client_id, client_name, data_silo_size, and data_features are required' 
      });
    }

    // Check if run exists
    const runData = await redis.get(`fl:run:${runId}`);
    if (!runData) {
      return res.status(404).json({ error: 'FL run not found' });
    }

    const run_config = JSON.parse(runData);

    // Create client info
    const client_info = {
      client_id,
      client_name,
      data_silo_size,
      data_features,
      metadata,
      registered_at: new Date().toISOString(),
      status: 'ready'
    };

    // Store client info
    await redis.set(`fl:client:${runId}:${client_id}`, JSON.stringify(client_info));

    // Update run config
    if (!run_config.registered_clients.includes(client_id)) {
      run_config.registered_clients.push(client_id);
      await redis.set(`fl:run:${runId}`, JSON.stringify(run_config));
    }

    // Publish CloudEvent
    const event_id = `${Date.now()}-${uuidv4().substring(0, 8)}`;
    const cloudevent = {
      specversion: '1.0',
      id: event_id,
      type: 'com.flowerai.fl.client.registered',
      source: 'urn:flowerai:api',
      subject: `${runId}/${client_id}`,
      time: new Date().toISOString(),
      data: client_info
    };

    await redis.set(`event:${event_id}`, JSON.stringify(cloudevent));
    await redis.xadd('fl:events', '*',
      'event_id', event_id,
      'type', cloudevent.type,
      'subject', `${runId}/${client_id}`,
      'timestamp', cloudevent.time
    );

    res.status(201).json({
      success: true,
      client_id,
      run_id: runId,
      message: `Client '${client_name}' registered`
    });
  } catch (error) {
    console.error('Error registering client:', error);
    res.status(500).json({ error: 'Failed to register client' });
  }
});

/**
 * GET /api/fl/runs/:runId/clients
 * List all clients for a run
 */
router.get('/runs/:runId/clients', async (req, res) => {
  try {
    const { runId } = req.params;

    const clientKeys = await redis.keys(`fl:client:${runId}:*`);
    const clients = await Promise.all(
      clientKeys.map(async (key) => {
        const clientData = await redis.get(key);
        return clientData ? JSON.parse(clientData) : null;
      })
    );

    res.json({
      success: true,
      count: clients.filter(c => c !== null).length,
      clients: clients.filter(c => c !== null)
    });
  } catch (error) {
    console.error('Error fetching clients:', error);
    res.status(500).json({ error: 'Failed to fetch clients' });
  }
});

// ============================================================================
// Model Registry
// ============================================================================

/**
 * GET /api/fl/models
 * List models in registry
 */
router.get('/models', async (req, res) => {
  try {
    const { run_id, limit = 10 } = req.query;

    let modelKeys = [];
    
    if (run_id) {
      // Get models for specific run
      const versions = await redis.zrange(`fl:registry:${run_id}`, 0, parseInt(limit) - 1, 'REV');
      modelKeys = versions.map(v => `fl:model:${v}`);
    } else {
      // Get all models
      const allKeys = await redis.keys('fl:model:*');
      modelKeys = allKeys
        .filter(k => !k.includes(':params:'))
        .slice(0, parseInt(limit));
    }

    const models = await Promise.all(
      modelKeys.map(async (key) => {
        const modelData = await redis.get(key);
        return modelData ? JSON.parse(modelData) : null;
      })
    );

    res.json({
      success: true,
      count: models.filter(m => m !== null).length,
      models: models.filter(m => m !== null)
    });
  } catch (error) {
    console.error('Error listing models:', error);
    res.status(500).json({ error: 'Failed to list models' });
  }
});

/**
 * GET /api/fl/models/:version
 * Get model details
 */
router.get('/models/:version', async (req, res) => {
  try {
    const { version } = req.params;

    const modelData = await redis.get(`fl:model:${version}`);
    
    if (!modelData) {
      return res.status(404).json({ error: 'Model not found' });
    }

    const model_record = JSON.parse(modelData);
    const params_exist = await redis.exists(`fl:model:params:${version}`);

    res.json({
      success: true,
      model_version: version,
      model_record,
      params_available: params_exist === 1
    });
  } catch (error) {
    console.error('Error fetching model:', error);
    res.status(500).json({ error: 'Failed to fetch model' });
  }
});

// ============================================================================
// Metrics & Monitoring
// ============================================================================

/**
 * GET /api/fl/runs/:runId/metrics
 * Get metrics for a run
 */
router.get('/runs/:runId/metrics', async (req, res) => {
  try {
    const { runId } = req.params;

    // Get run config
    const runData = await redis.get(`fl:run:${runId}`);
    if (!runData) {
      return res.status(404).json({ error: 'FL run not found' });
    }

    const run_config = JSON.parse(runData);

    // Get model metrics per round
    const versions = await redis.zrange(`fl:registry:${runId}`, 0, -1);
    const round_metrics = await Promise.all(
      versions.map(async (version) => {
        const modelData = await redis.get(`fl:model:${version}`);
        if (modelData) {
          const model_record = JSON.parse(modelData);
          return {
            round: model_record.round_num,
            metrics: model_record.metrics
          };
        }
        return null;
      })
    );

    res.json({
      success: true,
      run_config,
      num_rounds_completed: round_metrics.filter(m => m !== null).length,
      round_metrics: round_metrics.filter(m => m !== null)
    });
  } catch (error) {
    console.error('Error fetching metrics:', error);
    res.status(500).json({ error: 'Failed to fetch metrics' });
  }
});

/**
 * GET /api/fl/events
 * Get recent FL events (SSE stream)
 */
router.get('/events', async (req, res) => {
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');

  const { run_id } = req.query;

  try {
    // Read recent events from stream
    const events = await redis.xrevrange('fl:events', '+', '-', 'COUNT', 50);

    for (const [id, fields] of events) {
      const event_id = fields[fields.indexOf('event_id') + 1];
      const subject = fields[fields.indexOf('subject') + 1];

      // Filter by run_id if provided
      if (run_id && !subject.includes(run_id)) {
        continue;
      }

      const eventData = await redis.get(`event:${event_id}`);
      if (eventData) {
        res.write(`data: ${eventData}\n\n`);
      }
    }

    res.write('data: {"type": "end"}\n\n');
    res.end();
  } catch (error) {
    console.error('Error streaming events:', error);
    res.status(500).json({ error: 'Failed to stream events' });
  }
});

// ============================================================================
// Inference
// ============================================================================

/**
 * POST /api/fl/predict
 * Real-time prediction using federated model
 */
router.post('/predict', async (req, res) => {
  try {
    const {
      model_version,
      input_features,
      feature_names = ['sentiment', 'call_duration_minutes', 'response_time']
    } = req.body;

    if (!model_version || !input_features) {
      return res.status(400).json({ 
        error: 'model_version and input_features are required' 
      });
    }

    // Check if model exists
    const modelData = await redis.get(`fl:model:${model_version}`);
    if (!modelData) {
      return res.status(404).json({ error: 'Model not found' });
    }

    // Mock prediction (in production, load actual model and run inference)
    const prediction_id = uuidv4().substring(0, 8);
    const prediction = {
      prediction_id,
      model_version,
      input_features,
      predicted_class: 1, // Mock: 1 = high CSAT
      confidence: 0.87,
      prediction_time: new Date().toISOString()
    };

    // Publish prediction event
    const event_id = `${Date.now()}-${uuidv4().substring(0, 8)}`;
    const cloudevent = {
      specversion: '1.0',
      id: event_id,
      type: 'com.flowerai.fl.prediction.made',
      source: 'urn:flowerai:inference',
      subject: prediction_id,
      time: new Date().toISOString(),
      data: prediction
    };

    await redis.set(`event:${event_id}`, JSON.stringify(cloudevent));
    await redis.xadd('fl:events', '*',
      'event_id', event_id,
      'type', cloudevent.type,
      'subject', prediction_id,
      'timestamp', cloudevent.time
    );

    res.json({
      success: true,
      prediction
    });
  } catch (error) {
    console.error('Error making prediction:', error);
    res.status(500).json({ error: 'Failed to make prediction' });
  }
});

/**
 * POST /api/fl/batch-score
 * Batch scoring using federated model
 */
router.post('/batch-score', async (req, res) => {
  try {
    const {
      model_version,
      batch_data,
      feature_names = ['sentiment', 'call_duration_minutes', 'response_time']
    } = req.body;

    if (!model_version || !batch_data || !Array.isArray(batch_data)) {
      return res.status(400).json({ 
        error: 'model_version and batch_data (array) are required' 
      });
    }

    // Check if model exists
    const modelData = await redis.get(`fl:model:${model_version}`);
    if (!modelData) {
      return res.status(404).json({ error: 'Model not found' });
    }

    // Mock batch predictions
    const predictions = batch_data.map((input_features, idx) => ({
      index: idx,
      input_features,
      predicted_class: Math.random() > 0.5 ? 1 : 0,
      confidence: 0.7 + Math.random() * 0.3
    }));

    res.json({
      success: true,
      model_version,
      num_predictions: predictions.length,
      predictions
    });
  } catch (error) {
    console.error('Error batch scoring:', error);
    res.status(500).json({ error: 'Failed to perform batch scoring' });
  }
});

export default router;

