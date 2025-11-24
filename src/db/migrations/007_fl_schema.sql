-- Federated Learning Schema for Supabase
-- Stores FL run metadata, client registrations, and model registry

-- ============================================================================
-- FL Runs Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS fl_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id TEXT UNIQUE NOT NULL,
    run_name TEXT NOT NULL,
    dataset_name TEXT NOT NULL,
    model_type TEXT NOT NULL,
    num_rounds INTEGER NOT NULL,
    current_round INTEGER NOT NULL DEFAULT 0,
    min_clients INTEGER NOT NULL,
    strategy TEXT NOT NULL DEFAULT 'FedAvg',
    target_metric TEXT NOT NULL DEFAULT 'accuracy',
    privacy_budget DECIMAL(10, 4),
    server_address TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'initialized',
    config JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    stopped_at TIMESTAMPTZ,
    failed_at TIMESTAMPTZ,
    error_message TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_fl_runs_run_id ON fl_runs(run_id);
CREATE INDEX IF NOT EXISTS idx_fl_runs_status ON fl_runs(status);
CREATE INDEX IF NOT EXISTS idx_fl_runs_created_at ON fl_runs(created_at DESC);

-- Comments
COMMENT ON TABLE fl_runs IS 'Federated learning training runs';
COMMENT ON COLUMN fl_runs.run_id IS 'Unique run identifier (fl_run_*)';
COMMENT ON COLUMN fl_runs.current_round IS 'Current federated round number (0 = initial, increments each round)';
COMMENT ON COLUMN fl_runs.strategy IS 'Aggregation strategy (FedAvg, FedProx, etc.)';
COMMENT ON COLUMN fl_runs.privacy_budget IS 'Differential privacy epsilon budget';
COMMENT ON COLUMN fl_runs.status IS 'Run status: initialized, running, completed, stopped, failed';

-- ============================================================================
-- FL Clients Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS fl_clients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id TEXT NOT NULL,
    client_id TEXT NOT NULL,
    client_name TEXT NOT NULL,
    data_silo_size INTEGER NOT NULL,
    data_features JSONB NOT NULL,
    metadata JSONB DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'ready',
    registered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ,
    UNIQUE(run_id, client_id),
    FOREIGN KEY (run_id) REFERENCES fl_runs(run_id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_fl_clients_run_id ON fl_clients(run_id);
CREATE INDEX IF NOT EXISTS idx_fl_clients_client_id ON fl_clients(client_id);
CREATE INDEX IF NOT EXISTS idx_fl_clients_status ON fl_clients(status);

-- Comments
COMMENT ON TABLE fl_clients IS 'Federated learning client registrations (data silos)';
COMMENT ON COLUMN fl_clients.data_silo_size IS 'Number of samples at this client';
COMMENT ON COLUMN fl_clients.data_features IS 'List of feature names available';
COMMENT ON COLUMN fl_clients.metadata IS 'Client metadata (region, org_type, etc.)';

-- ============================================================================
-- FL Models Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS fl_models (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_version TEXT UNIQUE NOT NULL,
    run_id TEXT NOT NULL,
    round_num INTEGER NOT NULL,
    metrics JSONB NOT NULL,
    metadata JSONB DEFAULT '{}',
    num_parameters INTEGER,
    parameter_shapes JSONB,
    params_storage_path TEXT,
    status TEXT NOT NULL DEFAULT 'saved',
    saved_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deployed_at TIMESTAMPTZ,
    FOREIGN KEY (run_id) REFERENCES fl_runs(run_id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_fl_models_model_version ON fl_models(model_version);
CREATE INDEX IF NOT EXISTS idx_fl_models_run_id ON fl_models(run_id);
CREATE INDEX IF NOT EXISTS idx_fl_models_round_num ON fl_models(round_num);
CREATE INDEX IF NOT EXISTS idx_fl_models_saved_at ON fl_models(saved_at DESC);

-- Comments
COMMENT ON TABLE fl_models IS 'Federated learning model registry';
COMMENT ON COLUMN fl_models.model_version IS 'Model version ID (run_id_rN)';
COMMENT ON COLUMN fl_models.round_num IS 'Federated round number (0 = initial)';
COMMENT ON COLUMN fl_models.metrics IS 'Model performance metrics (accuracy, f1, auc, etc.)';
COMMENT ON COLUMN fl_models.params_storage_path IS 'Path to model parameters (S3, Redis, etc.)';

-- ============================================================================
-- FL Metrics Table (Time Series)
-- ============================================================================

CREATE TABLE IF NOT EXISTS fl_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id TEXT NOT NULL,
    round_num INTEGER NOT NULL,
    client_id TEXT,
    metric_type TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value DECIMAL(10, 6) NOT NULL,
    metadata JSONB DEFAULT '{}',
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (run_id) REFERENCES fl_runs(run_id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_fl_metrics_run_id ON fl_metrics(run_id);
CREATE INDEX IF NOT EXISTS idx_fl_metrics_round_num ON fl_metrics(round_num);
CREATE INDEX IF NOT EXISTS idx_fl_metrics_client_id ON fl_metrics(client_id);
CREATE INDEX IF NOT EXISTS idx_fl_metrics_metric_name ON fl_metrics(metric_name);
CREATE INDEX IF NOT EXISTS idx_fl_metrics_recorded_at ON fl_metrics(recorded_at DESC);

-- Comments
COMMENT ON TABLE fl_metrics IS 'Time-series metrics for FL runs';
COMMENT ON COLUMN fl_metrics.metric_type IS 'Metric type: training, evaluation, aggregation';
COMMENT ON COLUMN fl_metrics.metric_name IS 'Metric name: accuracy, loss, f1, auc, etc.';
COMMENT ON COLUMN fl_metrics.client_id IS 'Client ID (null for aggregated metrics)';

-- ============================================================================
-- FL Events Table (Audit Log)
-- ============================================================================

CREATE TABLE IF NOT EXISTS fl_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id TEXT UNIQUE NOT NULL,
    event_type TEXT NOT NULL,
    source TEXT NOT NULL,
    subject TEXT NOT NULL,
    run_id TEXT,
    client_id TEXT,
    data JSONB NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (run_id) REFERENCES fl_runs(run_id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_fl_events_event_type ON fl_events(event_type);
CREATE INDEX IF NOT EXISTS idx_fl_events_run_id ON fl_events(run_id);
CREATE INDEX IF NOT EXISTS idx_fl_events_client_id ON fl_events(client_id);
CREATE INDEX IF NOT EXISTS idx_fl_events_timestamp ON fl_events(timestamp DESC);

-- Comments
COMMENT ON TABLE fl_events IS 'Audit log of FL events (CloudEvents)';
COMMENT ON COLUMN fl_events.event_type IS 'CloudEvent type (com.flowerai.fl.*)';
COMMENT ON COLUMN fl_events.source IS 'Event source URI';
COMMENT ON COLUMN fl_events.subject IS 'Event subject (run_id, client_id, model_version)';

-- ============================================================================
-- FL Predictions Table (Inference Log)
-- ============================================================================

CREATE TABLE IF NOT EXISTS fl_predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prediction_id TEXT UNIQUE NOT NULL,
    model_version TEXT NOT NULL,
    input_features JSONB NOT NULL,
    predicted_class INTEGER,
    predicted_value DECIMAL(10, 6),
    confidence DECIMAL(5, 4),
    prediction_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    FOREIGN KEY (model_version) REFERENCES fl_models(model_version) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_fl_predictions_model_version ON fl_predictions(model_version);
CREATE INDEX IF NOT EXISTS idx_fl_predictions_prediction_time ON fl_predictions(prediction_time DESC);

-- Comments
COMMENT ON TABLE fl_predictions IS 'Inference predictions log';
COMMENT ON COLUMN fl_predictions.predicted_class IS 'Predicted class (for classification)';
COMMENT ON COLUMN fl_predictions.predicted_value IS 'Predicted value (for regression)';
COMMENT ON COLUMN fl_predictions.confidence IS 'Prediction confidence score';

-- ============================================================================
-- Triggers for Updated At
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_fl_runs_updated_at
    BEFORE UPDATE ON fl_runs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- Views
-- ============================================================================

-- Active FL runs with client count
CREATE OR REPLACE VIEW v_fl_runs_active AS
SELECT 
    r.run_id,
    r.run_name,
    r.status,
    r.current_round,
    r.num_rounds,
    COUNT(DISTINCT c.client_id) as num_clients,
    r.created_at,
    r.started_at
FROM fl_runs r
LEFT JOIN fl_clients c ON r.run_id = c.run_id
WHERE r.status IN ('initialized', 'running')
GROUP BY r.run_id, r.run_name, r.status, r.current_round, r.num_rounds, r.created_at, r.started_at
ORDER BY r.created_at DESC;

COMMENT ON VIEW v_fl_runs_active IS 'Active FL runs with client counts';

-- Model performance summary
CREATE OR REPLACE VIEW v_fl_model_performance AS
SELECT 
    m.model_version,
    m.run_id,
    m.round_num,
    m.metrics->>'accuracy' as accuracy,
    m.metrics->>'f1' as f1,
    m.metrics->>'auc' as auc,
    m.saved_at
FROM fl_models m
ORDER BY m.run_id, m.round_num;

COMMENT ON VIEW v_fl_model_performance IS 'Model performance metrics per round';

-- ============================================================================
-- Row Level Security (RLS)
-- ============================================================================

-- Enable RLS
ALTER TABLE fl_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE fl_clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE fl_models ENABLE ROW LEVEL SECURITY;
ALTER TABLE fl_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE fl_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE fl_predictions ENABLE ROW LEVEL SECURITY;

-- Policies (adjust based on your auth setup)
-- For now, allow all authenticated users to read/write
CREATE POLICY "Allow all for authenticated users" ON fl_runs
    FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Allow all for authenticated users" ON fl_clients
    FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Allow all for authenticated users" ON fl_models
    FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Allow all for authenticated users" ON fl_metrics
    FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Allow all for authenticated users" ON fl_events
    FOR ALL USING (auth.role() = 'authenticated');

CREATE POLICY "Allow all for authenticated users" ON fl_predictions
    FOR ALL USING (auth.role() = 'authenticated');

-- ============================================================================
-- Sample Data (Optional)
-- ============================================================================

-- Insert sample FL run
-- INSERT INTO fl_runs (run_id, run_name, dataset_name, model_type, num_rounds, min_clients, strategy, target_metric, server_address, config)
-- VALUES (
--     'fl_run_sample_001',
--     'Call Center CSAT Prediction Q4',
--     'call_center_csat',
--     'logistic_regression',
--     5,
--     3,
--     'FedAvg',
--     'accuracy',
--     '0.0.0.0:8080',
--     '{"description": "Sample federated learning run"}'::jsonb
-- );

