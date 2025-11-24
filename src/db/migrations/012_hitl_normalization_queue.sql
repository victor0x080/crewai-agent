-- Migration 012: Human-in-the-Loop Normalization Queue
-- 
-- Creates unified review queue for low-confidence normalization decisions.
-- Supports:
-- - Multi-dimensional routing (confidence, risk, complexity, PII)
-- - RBAC (role-based assignment)
-- - PII masking/unmasking with audit trail
-- - Batch review workflows
-- - SLA tracking
-- - Feedback loops to ML training

-- ============================================================================
-- HITL REVIEW QUEUE
-- ============================================================================

CREATE TABLE IF NOT EXISTS hitl_normalization_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Source data
    source_event_id TEXT NOT NULL,
    source TEXT NOT NULL,  -- 'amazon_ads', 'walmart_connect', etc.
    raw_data JSONB NOT NULL,
    
    -- Normalization attempt
    normalization_run_id UUID,  -- Links to normalization attempt
    schema_discovery_output JSONB,
    partial_normalizations JSONB,  -- What agents were able to normalize
    failed_fields JSONB,  -- Fields that couldn't be normalized
    
    -- Why it needs review
    review_reason TEXT NOT NULL,  -- 'low_confidence', 'validation_failed', 'anomaly_detected', 'pii_detected', 'conflict'
    confidence_scores JSONB,  -- Per-field confidence scores
    validation_errors JSONB,  -- Validation errors
    anomalies JSONB,  -- Detected anomalies
    
    -- Complexity scoring (for routing)
    complexity_score DECIMAL(3,2) DEFAULT 0.5,  -- 0-1 (0.5 = medium)
    field_count INT,
    unmapped_field_count INT,
    requires_domain_expertise BOOLEAN DEFAULT FALSE,
    
    -- PII handling
    contains_pii BOOLEAN DEFAULT FALSE,
    pii_fields TEXT[],  -- Fields containing PII
    masked_data JSONB,  -- Data with PII masked
    pii_access_log JSONB DEFAULT '[]'::jsonb,  -- Who accessed unmasked PII
    
    -- Routing and assignment
    priority TEXT DEFAULT 'medium',  -- 'low', 'medium', 'high', 'critical'
    assigned_to UUID,  -- User ID from auth.users
    assigned_role TEXT,  -- 'data_analyst', 'data_engineer', 'domain_expert'
    assigned_at TIMESTAMPTZ,
    
    -- Status tracking
    status TEXT DEFAULT 'pending',  -- 'pending', 'assigned', 'in_progress', 'resolved', 'escalated', 'rejected'
    resolution JSONB,  -- Final normalized data
    resolution_notes TEXT,
    resolved_by UUID,
    resolved_at TIMESTAMPTZ,
    
    -- SLA tracking
    created_at TIMESTAMPTZ DEFAULT NOW(),
    sla_deadline TIMESTAMPTZ,  -- Auto-calculated based on priority
    sla_breached BOOLEAN DEFAULT FALSE,
    time_to_assignment_ms BIGINT,
    time_to_resolution_ms BIGINT,
    
    -- Feedback loop
    feedback_quality TEXT,  -- 'excellent', 'good', 'poor'
    used_for_training BOOLEAN DEFAULT FALSE,
    training_label_id UUID,  -- Links to ml_training_labels
    
    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb,
    
    CONSTRAINT valid_status CHECK (status IN ('pending', 'assigned', 'in_progress', 'resolved', 'escalated', 'rejected')),
    CONSTRAINT valid_priority CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    CONSTRAINT valid_complexity CHECK (complexity_score >= 0 AND complexity_score <= 1)
);

CREATE INDEX idx_hitl_queue_status ON hitl_normalization_queue(status);
CREATE INDEX idx_hitl_queue_assigned_to ON hitl_normalization_queue(assigned_to);
CREATE INDEX idx_hitl_queue_priority ON hitl_normalization_queue(priority, created_at);
CREATE INDEX idx_hitl_queue_sla ON hitl_normalization_queue(sla_deadline) WHERE status NOT IN ('resolved', 'rejected');
CREATE INDEX idx_hitl_queue_source ON hitl_normalization_queue(source);


-- ============================================================================
-- REVIEW ACTIONS LOG
-- ============================================================================

CREATE TABLE IF NOT EXISTS hitl_review_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    queue_item_id UUID NOT NULL REFERENCES hitl_normalization_queue(id),
    
    action_type TEXT NOT NULL,  -- 'assign', 'accept', 'reject', 'edit_field', 'add_note', 'escalate', 'request_unmask'
    actor_id UUID NOT NULL,  -- User who performed action
    actor_role TEXT,
    
    action_details JSONB,  -- Type-specific details
    field_name TEXT,  -- For field edits
    old_value JSONB,
    new_value JSONB,
    
    performed_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT valid_action_type CHECK (action_type IN (
        'assign', 'accept', 'reject', 'edit_field', 'add_note', 'escalate', 
        'request_unmask', 'approve_unmask', 'view_pii'
    ))
);

CREATE INDEX idx_review_actions_queue ON hitl_review_actions(queue_item_id);
CREATE INDEX idx_review_actions_actor ON hitl_review_actions(actor_id);
CREATE INDEX idx_review_actions_type ON hitl_review_actions(action_type);


-- ============================================================================
-- RBAC POLICIES
-- ============================================================================

CREATE TABLE IF NOT EXISTS hitl_role_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_name TEXT NOT NULL UNIQUE,
    
    -- Review permissions
    can_review_low_complexity BOOLEAN DEFAULT TRUE,
    can_review_medium_complexity BOOLEAN DEFAULT FALSE,
    can_review_high_complexity BOOLEAN DEFAULT FALSE,
    
    -- PII permissions
    can_view_masked_pii BOOLEAN DEFAULT FALSE,
    can_view_unmasked_pii BOOLEAN DEFAULT FALSE,
    requires_approval_for_pii BOOLEAN DEFAULT TRUE,
    
    -- Actions
    can_approve BOOLEAN DEFAULT TRUE,
    can_reject BOOLEAN DEFAULT TRUE,
    can_edit_fields BOOLEAN DEFAULT TRUE,
    can_escalate BOOLEAN DEFAULT TRUE,
    can_assign_to_others BOOLEAN DEFAULT FALSE,
    
    -- Routing
    max_concurrent_assignments INT DEFAULT 5,
    auto_assign_priority TEXT[],  -- Priorities to auto-assign
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed default roles
INSERT INTO hitl_role_permissions (role_name, can_review_low_complexity, can_review_medium_complexity, can_review_high_complexity, can_view_unmasked_pii, can_assign_to_others, max_concurrent_assignments)
VALUES 
    ('data_analyst', TRUE, TRUE, FALSE, FALSE, FALSE, 10),
    ('data_engineer', TRUE, TRUE, TRUE, FALSE, TRUE, 15),
    ('domain_expert', TRUE, TRUE, TRUE, TRUE, TRUE, 5),
    ('admin', TRUE, TRUE, TRUE, TRUE, TRUE, 99)
ON CONFLICT (role_name) DO NOTHING;


-- ============================================================================
-- SLA CONFIGURATION
-- ============================================================================

CREATE TABLE IF NOT EXISTS hitl_sla_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    priority TEXT NOT NULL UNIQUE,
    sla_hours INT NOT NULL,
    escalation_hours INT,  -- Hours before auto-escalation
    
    CONSTRAINT valid_priority CHECK (priority IN ('low', 'medium', 'high', 'critical'))
);

INSERT INTO hitl_sla_config (priority, sla_hours, escalation_hours)
VALUES 
    ('low', 72, 48),      -- 3 days SLA, escalate after 2 days
    ('medium', 24, 12),   -- 1 day SLA, escalate after 12 hours
    ('high', 4, 2),       -- 4 hours SLA, escalate after 2 hours
    ('critical', 1, 0.5)  -- 1 hour SLA, escalate after 30 min
ON CONFLICT (priority) DO NOTHING;


-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Auto-calculate SLA deadline
CREATE OR REPLACE FUNCTION calculate_sla_deadline(p_priority TEXT)
RETURNS TIMESTAMPTZ AS $$
DECLARE
    v_sla_hours INT;
BEGIN
    SELECT sla_hours INTO v_sla_hours
    FROM hitl_sla_config
    WHERE priority = p_priority;
    
    RETURN NOW() + (v_sla_hours || ' hours')::INTERVAL;
END;
$$ LANGUAGE plpgsql;


-- Auto-calculate complexity score
CREATE OR REPLACE FUNCTION calculate_complexity_score(
    p_field_count INT,
    p_unmapped_count INT,
    p_avg_confidence DECIMAL
)
RETURNS DECIMAL AS $$
DECLARE
    v_score DECIMAL;
BEGIN
    -- Complexity = (unmapped_ratio * 0.4) + ((1 - confidence) * 0.4) + (field_count_factor * 0.2)
    v_score := (p_unmapped_count::DECIMAL / GREATEST(p_field_count, 1) * 0.4)
             + ((1 - p_avg_confidence) * 0.4)
             + (LEAST(p_field_count / 50.0, 1) * 0.2);
    
    RETURN LEAST(GREATEST(v_score, 0), 1);
END;
$$ LANGUAGE plpgsql;


-- Auto-assign based on complexity and role capacity
CREATE OR REPLACE FUNCTION auto_assign_review(p_queue_item_id UUID)
RETURNS UUID AS $$
DECLARE
    v_complexity DECIMAL;
    v_priority TEXT;
    v_assigned_to UUID;
    v_role TEXT;
BEGIN
    -- Get queue item complexity
    SELECT complexity_score, priority INTO v_complexity, v_priority
    FROM hitl_normalization_queue
    WHERE id = p_queue_item_id;
    
    -- Find available reviewer with appropriate permissions
    SELECT u.id, p.role_name INTO v_assigned_to, v_role
    FROM auth.users u
    JOIN hitl_role_permissions p ON p.role_name = u.role
    WHERE 
        -- Complexity match
        (v_complexity < 0.33 AND p.can_review_low_complexity) OR
        (v_complexity >= 0.33 AND v_complexity < 0.67 AND p.can_review_medium_complexity) OR
        (v_complexity >= 0.67 AND p.can_review_high_complexity)
        
        -- Not at capacity
        AND (
            SELECT COUNT(*) 
            FROM hitl_normalization_queue q
            WHERE q.assigned_to = u.id AND q.status IN ('assigned', 'in_progress')
        ) < p.max_concurrent_assignments
        
        -- Auto-assign priority matches
        AND (p.auto_assign_priority IS NULL OR v_priority = ANY(p.auto_assign_priority))
    
    ORDER BY RANDOM()  -- Round-robin (can improve with load balancing)
    LIMIT 1;
    
    IF v_assigned_to IS NOT NULL THEN
        UPDATE hitl_normalization_queue
        SET 
            assigned_to = v_assigned_to,
            assigned_role = v_role,
            assigned_at = NOW(),
            status = 'assigned',
            time_to_assignment_ms = EXTRACT(EPOCH FROM (NOW() - created_at)) * 1000
        WHERE id = p_queue_item_id;
        
        -- Log action
        INSERT INTO hitl_review_actions (queue_item_id, action_type, actor_id, actor_role)
        VALUES (p_queue_item_id, 'assign', v_assigned_to, v_role);
    END IF;
    
    RETURN v_assigned_to;
END;
$$ LANGUAGE plpgsql;


-- Mask PII fields
CREATE OR REPLACE FUNCTION mask_pii(p_data JSONB, p_pii_fields TEXT[])
RETURNS JSONB AS $$
DECLARE
    v_masked JSONB;
    v_field TEXT;
BEGIN
    v_masked := p_data;
    
    FOREACH v_field IN ARRAY p_pii_fields LOOP
        IF v_masked ? v_field THEN
            v_masked := jsonb_set(v_masked, ARRAY[v_field], '"***MASKED***"'::jsonb);
        END IF;
    END LOOP;
    
    RETURN v_masked;
END;
$$ LANGUAGE plpgsql;


-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Auto-set SLA deadline on insert
CREATE OR REPLACE FUNCTION set_sla_deadline()
RETURNS TRIGGER AS $$
BEGIN
    NEW.sla_deadline := calculate_sla_deadline(NEW.priority);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_set_sla_deadline
BEFORE INSERT ON hitl_normalization_queue
FOR EACH ROW
EXECUTE FUNCTION set_sla_deadline();


-- Auto-calculate complexity score on insert
CREATE OR REPLACE FUNCTION set_complexity_score()
RETURNS TRIGGER AS $$
DECLARE
    v_avg_confidence DECIMAL;
BEGIN
    -- Extract average confidence from confidence_scores JSON
    SELECT AVG((value->>'confidence')::DECIMAL)
    INTO v_avg_confidence
    FROM jsonb_each(NEW.confidence_scores);
    
    NEW.complexity_score := calculate_complexity_score(
        NEW.field_count,
        NEW.unmapped_field_count,
        COALESCE(v_avg_confidence, 0.5)
    );
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_set_complexity_score
BEFORE INSERT ON hitl_normalization_queue
FOR EACH ROW
EXECUTE FUNCTION set_complexity_score();


-- Check SLA breach
CREATE OR REPLACE FUNCTION check_sla_breach()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status NOT IN ('resolved', 'rejected') AND NOW() > NEW.sla_deadline THEN
        NEW.sla_breached := TRUE;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_check_sla_breach
BEFORE UPDATE ON hitl_normalization_queue
FOR EACH ROW
EXECUTE FUNCTION check_sla_breach();


-- ============================================================================
-- VIEWS
-- ============================================================================

-- Pending reviews by priority
CREATE OR REPLACE VIEW v_pending_reviews AS
SELECT 
    q.*,
    NOW() - q.created_at AS age,
    q.sla_deadline - NOW() AS time_until_sla_breach,
    u.email AS assigned_to_email
FROM hitl_normalization_queue q
LEFT JOIN auth.users u ON u.id = q.assigned_to
WHERE q.status IN ('pending', 'assigned', 'in_progress')
ORDER BY 
    CASE q.priority
        WHEN 'critical' THEN 1
        WHEN 'high' THEN 2
        WHEN 'medium' THEN 3
        WHEN 'low' THEN 4
    END,
    q.created_at ASC;


-- Reviewer workload
CREATE OR REPLACE VIEW v_reviewer_workload AS
SELECT 
    u.id AS user_id,
    u.email,
    p.role_name,
    COUNT(*) FILTER (WHERE q.status = 'assigned') AS assigned_count,
    COUNT(*) FILTER (WHERE q.status = 'in_progress') AS in_progress_count,
    COUNT(*) FILTER (WHERE q.status = 'resolved') AS resolved_count,
    AVG(q.time_to_resolution_ms) FILTER (WHERE q.status = 'resolved') AS avg_resolution_time_ms,
    p.max_concurrent_assignments,
    p.max_concurrent_assignments - COUNT(*) FILTER (WHERE q.status IN ('assigned', 'in_progress')) AS available_capacity
FROM auth.users u
JOIN hitl_role_permissions p ON p.role_name = u.role
LEFT JOIN hitl_normalization_queue q ON q.assigned_to = u.id
GROUP BY u.id, u.email, p.role_name, p.max_concurrent_assignments;


-- SLA performance metrics
CREATE OR REPLACE VIEW v_sla_metrics AS
SELECT 
    priority,
    COUNT(*) AS total_items,
    COUNT(*) FILTER (WHERE status = 'resolved') AS resolved_items,
    COUNT(*) FILTER (WHERE sla_breached) AS sla_breaches,
    ROUND(COUNT(*) FILTER (WHERE sla_breached)::DECIMAL / NULLIF(COUNT(*), 0) * 100, 2) AS sla_breach_rate,
    AVG(time_to_resolution_ms) FILTER (WHERE status = 'resolved') AS avg_resolution_time_ms,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY time_to_resolution_ms) FILTER (WHERE status = 'resolved') AS median_resolution_time_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY time_to_resolution_ms) FILTER (WHERE status = 'resolved') AS p95_resolution_time_ms
FROM hitl_normalization_queue
GROUP BY priority;


COMMENT ON TABLE hitl_normalization_queue IS 'Unified queue for human review of low-confidence normalization decisions';
COMMENT ON COLUMN hitl_normalization_queue.complexity_score IS 'Auto-calculated 0-1 score for routing (0.33=low, 0.67=high)';
COMMENT ON COLUMN hitl_normalization_queue.masked_data IS 'Data with PII fields masked for initial review';
COMMENT ON COLUMN hitl_normalization_queue.pii_access_log IS 'Audit trail of who accessed unmasked PII';

