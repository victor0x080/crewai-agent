-- Migration 014: Partner-Specific Configuration
-- 
-- Creates abstraction layer for per-RMN and per-manufacturer policies:
-- - Field mapping overrides
-- - Validation rules
-- - Quality thresholds
-- - Custom transformations
-- - PII policies
-- - Rate limits
-- - SLA requirements

-- ============================================================================
-- PARTNER PROFILES
-- ============================================================================

CREATE TABLE IF NOT EXISTS partner_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Partner identification
    partner_type TEXT NOT NULL,  -- 'rmn', 'manufacturer', 'retailer'
    partner_id TEXT NOT NULL,  -- 'amazon_ads', 'walmart_connect', 'nike', 'cocacola', etc.
    partner_name TEXT NOT NULL,
    
    -- Contact and metadata
    contact_email TEXT,
    account_manager_id UUID,
    tier TEXT,  -- 'enterprise', 'premium', 'standard'
    
    -- Status
    status TEXT DEFAULT 'active',  -- 'active', 'suspended', 'inactive'
    onboarded_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Configuration
    config JSONB DEFAULT '{}'::jsonb,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT valid_partner_type CHECK (partner_type IN ('rmn', 'manufacturer', 'retailer')),
    CONSTRAINT valid_status CHECK (status IN ('active', 'suspended', 'inactive')),
    CONSTRAINT unique_partner UNIQUE (partner_type, partner_id)
);

CREATE INDEX idx_partner_profiles_type ON partner_profiles(partner_type);
CREATE INDEX idx_partner_profiles_id ON partner_profiles(partner_id);
CREATE INDEX idx_partner_profiles_status ON partner_profiles(status);


-- ============================================================================
-- FIELD MAPPING OVERRIDES
-- ============================================================================

CREATE TABLE IF NOT EXISTS partner_field_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    partner_profile_id UUID NOT NULL REFERENCES partner_profiles(id) ON DELETE CASCADE,
    
    -- Source field (partner-specific)
    source_field TEXT NOT NULL,
    source_field_pattern TEXT,  -- Regex pattern if needed
    
    -- Target CDM field
    target_field TEXT NOT NULL,
    target_table TEXT NOT NULL,
    
    -- Transformation
    transformation_type TEXT DEFAULT 'direct',  -- 'direct', 'formula', 'lookup', 'llm'
    transformation_config JSONB,  -- Type-specific config
    
    -- Override behavior
    override_priority INT DEFAULT 100,  -- Higher = takes precedence
    override_reason TEXT,
    
    -- Validation
    requires_validation BOOLEAN DEFAULT TRUE,
    custom_validation_rules JSONB,
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    effective_from TIMESTAMPTZ DEFAULT NOW(),
    effective_until TIMESTAMPTZ,
    
    created_by UUID,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT valid_transformation CHECK (transformation_type IN ('direct', 'formula', 'lookup', 'llm', 'custom'))
);

CREATE INDEX idx_partner_mappings_profile ON partner_field_mappings(partner_profile_id);
CREATE INDEX idx_partner_mappings_source ON partner_field_mappings(source_field);
CREATE INDEX idx_partner_mappings_target ON partner_field_mappings(target_field);
CREATE INDEX idx_partner_mappings_active ON partner_field_mappings(is_active) WHERE is_active = TRUE;


-- ============================================================================
-- VALIDATION RULES
-- ============================================================================

CREATE TABLE IF NOT EXISTS partner_validation_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    partner_profile_id UUID NOT NULL REFERENCES partner_profiles(id) ON DELETE CASCADE,
    
    -- Rule identification
    rule_name TEXT NOT NULL,
    rule_type TEXT NOT NULL,  -- 'field_range', 'cross_field', 'format', 'business_logic'
    
    -- Target
    applies_to_table TEXT,
    applies_to_fields TEXT[],
    
    -- Rule definition
    rule_expression TEXT NOT NULL,  -- SQL expression or JSON Logic
    rule_config JSONB,
    
    -- Severity
    severity TEXT DEFAULT 'error',  -- 'error', 'warning', 'info'
    
    -- Action on violation
    on_violation TEXT DEFAULT 'reject',  -- 'reject', 'warn', 'auto_fix', 'escalate'
    auto_fix_expression TEXT,
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT valid_rule_type CHECK (rule_type IN ('field_range', 'cross_field', 'format', 'business_logic', 'shacl')),
    CONSTRAINT valid_severity CHECK (severity IN ('error', 'warning', 'info')),
    CONSTRAINT valid_on_violation CHECK (on_violation IN ('reject', 'warn', 'auto_fix', 'escalate'))
);

CREATE INDEX idx_partner_rules_profile ON partner_validation_rules(partner_profile_id);
CREATE INDEX idx_partner_rules_table ON partner_validation_rules(applies_to_table);
CREATE INDEX idx_partner_rules_active ON partner_validation_rules(is_active) WHERE is_active = TRUE;


-- ============================================================================
-- QUALITY THRESHOLDS
-- ============================================================================

CREATE TABLE IF NOT EXISTS partner_quality_thresholds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    partner_profile_id UUID NOT NULL REFERENCES partner_profiles(id) ON DELETE CASCADE,
    
    -- Threshold type
    metric_name TEXT NOT NULL,  -- 'field_accuracy', 'overall_confidence', 'completeness', etc.
    
    -- Thresholds
    min_threshold DECIMAL(5,4),  -- Reject below this
    warn_threshold DECIMAL(5,4),  -- Warn if below this
    target_threshold DECIMAL(5,4),  -- Target/goal
    
    -- Scope
    applies_to_table TEXT,
    applies_to_agent TEXT,
    
    -- Actions
    below_min_action TEXT DEFAULT 'reject',  -- 'reject', 'escalate', 'accept_with_flag'
    below_warn_action TEXT DEFAULT 'warn',
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT valid_thresholds CHECK (
        (min_threshold IS NULL OR warn_threshold IS NULL OR min_threshold <= warn_threshold) AND
        (warn_threshold IS NULL OR target_threshold IS NULL OR warn_threshold <= target_threshold)
    )
);

CREATE INDEX idx_partner_thresholds_profile ON partner_quality_thresholds(partner_profile_id);
CREATE INDEX idx_partner_thresholds_metric ON partner_quality_thresholds(metric_name);


-- ============================================================================
-- CUSTOM TRANSFORMATIONS
-- ============================================================================

CREATE TABLE IF NOT EXISTS partner_custom_transformations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    partner_profile_id UUID NOT NULL REFERENCES partner_profiles(id) ON DELETE CASCADE,
    
    -- Transformation identification
    transformation_name TEXT NOT NULL,
    transformation_type TEXT NOT NULL,  -- 'python_function', 'sql_function', 'regex', 'lookup_table'
    
    -- Implementation
    function_code TEXT,  -- Python or SQL code
    lookup_table JSONB,  -- For lookup_table type
    regex_pattern TEXT,  -- For regex type
    
    -- Input/Output
    input_fields TEXT[],
    output_field TEXT,
    
    -- Metadata
    description TEXT,
    author_id UUID,
    version TEXT DEFAULT 'v1.0',
    
    -- Testing
    test_cases JSONB,  -- [{"input": {...}, "expected_output": ...}]
    last_tested_at TIMESTAMPTZ,
    test_passed BOOLEAN,
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT valid_transformation_type CHECK (transformation_type IN ('python_function', 'sql_function', 'regex', 'lookup_table'))
);

CREATE INDEX idx_partner_transformations_profile ON partner_custom_transformations(partner_profile_id);
CREATE INDEX idx_partner_transformations_name ON partner_custom_transformations(transformation_name);


-- ============================================================================
-- PII POLICIES
-- ============================================================================

CREATE TABLE IF NOT EXISTS partner_pii_policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    partner_profile_id UUID NOT NULL REFERENCES partner_profiles(id) ON DELETE CASCADE,
    
    -- PII field identification
    field_name TEXT NOT NULL,
    pii_category TEXT NOT NULL,  -- 'email', 'phone', 'name', 'address', 'ssn', 'custom'
    
    -- Handling policy
    masking_strategy TEXT DEFAULT 'full',  -- 'full', 'partial', 'hash', 'tokenize', 'none'
    retention_days INT,
    
    -- Access control
    requires_approval BOOLEAN DEFAULT TRUE,
    approved_roles TEXT[],
    max_access_count INT,
    
    -- Compliance
    compliance_requirements TEXT[],  -- ['GDPR', 'CCPA', 'HIPAA']
    data_classification TEXT,  -- 'public', 'internal', 'confidential', 'restricted'
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT valid_masking CHECK (masking_strategy IN ('full', 'partial', 'hash', 'tokenize', 'none')),
    CONSTRAINT valid_classification CHECK (data_classification IN ('public', 'internal', 'confidential', 'restricted'))
);

CREATE INDEX idx_partner_pii_profile ON partner_pii_policies(partner_profile_id);
CREATE INDEX idx_partner_pii_field ON partner_pii_policies(field_name);


-- ============================================================================
-- RATE LIMITS & SLA
-- ============================================================================

CREATE TABLE IF NOT EXISTS partner_rate_limits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    partner_profile_id UUID NOT NULL REFERENCES partner_profiles(id) ON DELETE CASCADE,
    
    -- Limit type
    limit_type TEXT NOT NULL,  -- 'ingestion_rate', 'api_calls', 'normalization_runs'
    
    -- Limits
    max_per_second INT,
    max_per_minute INT,
    max_per_hour INT,
    max_per_day INT,
    burst_capacity INT,
    
    -- SLA
    target_latency_ms INT,  -- Target processing time
    max_latency_ms INT,  -- SLA breach threshold
    
    -- Actions on limit breach
    on_limit_breach TEXT DEFAULT 'queue',  -- 'queue', 'reject', 'throttle'
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT valid_limit_type CHECK (limit_type IN ('ingestion_rate', 'api_calls', 'normalization_runs', 'storage'))
);

CREATE INDEX idx_partner_limits_profile ON partner_rate_limits(partner_profile_id);


-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Get field mapping for partner
CREATE OR REPLACE FUNCTION get_partner_field_mapping(
    p_partner_id TEXT,
    p_source_field TEXT
)
RETURNS TABLE (
    target_field TEXT,
    target_table TEXT,
    transformation_type TEXT,
    transformation_config JSONB,
    override_priority INT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        pfm.target_field,
        pfm.target_table,
        pfm.transformation_type,
        pfm.transformation_config,
        pfm.override_priority
    FROM partner_field_mappings pfm
    JOIN partner_profiles pp ON pp.id = pfm.partner_profile_id
    WHERE 
        pp.partner_id = p_partner_id
        AND pfm.is_active = TRUE
        AND (pfm.source_field = p_source_field OR p_source_field ~ pfm.source_field_pattern)
        AND (pfm.effective_until IS NULL OR pfm.effective_until > NOW())
    ORDER BY pfm.override_priority DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;


-- Get validation rules for partner
CREATE OR REPLACE FUNCTION get_partner_validation_rules(
    p_partner_id TEXT,
    p_table_name TEXT
)
RETURNS TABLE (
    rule_name TEXT,
    rule_expression TEXT,
    severity TEXT,
    on_violation TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        pvr.rule_name,
        pvr.rule_expression,
        pvr.severity,
        pvr.on_violation
    FROM partner_validation_rules pvr
    JOIN partner_profiles pp ON pp.id = pvr.partner_profile_id
    WHERE 
        pp.partner_id = p_partner_id
        AND pvr.is_active = TRUE
        AND (pvr.applies_to_table IS NULL OR pvr.applies_to_table = p_table_name);
END;
$$ LANGUAGE plpgsql;


-- Check quality thresholds
CREATE OR REPLACE FUNCTION check_partner_quality_thresholds(
    p_partner_id TEXT,
    p_metric_name TEXT,
    p_metric_value DECIMAL
)
RETURNS TABLE (
    threshold_type TEXT,
    threshold_value DECIMAL,
    action TEXT,
    breached BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        CASE 
            WHEN p_metric_value < pqt.min_threshold THEN 'min'
            WHEN p_metric_value < pqt.warn_threshold THEN 'warn'
            ELSE 'ok'
        END AS threshold_type,
        CASE 
            WHEN p_metric_value < pqt.min_threshold THEN pqt.min_threshold
            WHEN p_metric_value < pqt.warn_threshold THEN pqt.warn_threshold
            ELSE pqt.target_threshold
        END AS threshold_value,
        CASE 
            WHEN p_metric_value < pqt.min_threshold THEN pqt.below_min_action
            WHEN p_metric_value < pqt.warn_threshold THEN pqt.below_warn_action
            ELSE 'accept'
        END AS action,
        (p_metric_value < pqt.min_threshold OR p_metric_value < pqt.warn_threshold) AS breached
    FROM partner_quality_thresholds pqt
    JOIN partner_profiles pp ON pp.id = pqt.partner_profile_id
    WHERE 
        pp.partner_id = p_partner_id
        AND pqt.metric_name = p_metric_name
        AND pqt.is_active = TRUE
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;


-- ============================================================================
-- SEED DATA
-- ============================================================================

-- Amazon Ads profile
INSERT INTO partner_profiles (partner_type, partner_id, partner_name, tier, status)
VALUES ('rmn', 'amazon_ads', 'Amazon Advertising', 'enterprise', 'active')
ON CONFLICT (partner_type, partner_id) DO NOTHING;

-- Walmart Connect profile
INSERT INTO partner_profiles (partner_type, partner_id, partner_name, tier, status)
VALUES ('rmn', 'walmart_connect', 'Walmart Connect', 'enterprise', 'active')
ON CONFLICT (partner_type, partner_id) DO NOTHING;

-- Example field mapping override for Amazon
INSERT INTO partner_field_mappings (
    partner_profile_id,
    source_field,
    target_field,
    target_table,
    transformation_type,
    override_priority
)
SELECT 
    pp.id,
    'impr',
    'impressions_count',
    'fact_media_performance',
    'direct',
    200
FROM partner_profiles pp
WHERE pp.partner_id = 'amazon_ads'
ON CONFLICT DO NOTHING;

-- Example validation rule for Amazon (clicks <= impressions)
INSERT INTO partner_validation_rules (
    partner_profile_id,
    rule_name,
    rule_type,
    applies_to_table,
    rule_expression,
    severity,
    on_violation
)
SELECT 
    pp.id,
    'clicks_lte_impressions',
    'cross_field',
    'fact_media_performance',
    'clicks_count <= impressions_count',
    'error',
    'reject'
FROM partner_profiles pp
WHERE pp.partner_id = 'amazon_ads'
ON CONFLICT DO NOTHING;

-- Example quality threshold
INSERT INTO partner_quality_thresholds (
    partner_profile_id,
    metric_name,
    min_threshold,
    warn_threshold,
    target_threshold
)
SELECT 
    pp.id,
    'field_accuracy',
    0.85,
    0.90,
    0.95
FROM partner_profiles pp
WHERE pp.partner_id = 'amazon_ads'
ON CONFLICT DO NOTHING;


COMMENT ON TABLE partner_profiles IS 'Partner (RMN/manufacturer) profiles with configuration';
COMMENT ON TABLE partner_field_mappings IS 'Partner-specific field mapping overrides';
COMMENT ON TABLE partner_validation_rules IS 'Partner-specific validation rules';
COMMENT ON TABLE partner_quality_thresholds IS 'Partner-specific quality thresholds';

