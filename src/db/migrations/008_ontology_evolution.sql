-- ============================================================================
-- Ontology Evolution & Continuous Learning
-- Enables agents to propose new concepts, track concept lifecycle, and manage
-- ontology changes over time
-- ============================================================================

-- Concept proposals from agents
CREATE TABLE IF NOT EXISTS ontology_concept_proposals (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  proposed_concept_uri TEXT NOT NULL,
  pref_label TEXT NOT NULL,
  alt_labels TEXT[],
  definition TEXT,
  broader_uri TEXT,  -- Parent concept
  source TEXT NOT NULL,  -- 'agent_discovery', 'human_request', 'auto_extraction'
  source_agent_id TEXT,  -- Which agent proposed it
  confidence FLOAT,  -- Agent's confidence in this concept
  examples JSONB,  -- Example fields/values that triggered proposal
  justification TEXT,  -- Why this concept is needed
  status TEXT DEFAULT 'pending',  -- pending, approved, rejected, merged
  proposed_by TEXT,
  proposed_at TIMESTAMPTZ DEFAULT NOW(),
  reviewed_by TEXT,
  reviewed_at TIMESTAMPTZ,
  rejection_reason TEXT,
  merged_into_uri TEXT,  -- If merged with existing concept
  metadata JSONB
);

CREATE INDEX idx_ontology_proposals_status ON ontology_concept_proposals(status);
CREATE INDEX idx_ontology_proposals_source ON ontology_concept_proposals(source, source_agent_id);
CREATE INDEX idx_ontology_proposals_broader ON ontology_concept_proposals(broader_uri);

-- Ontology change history
CREATE TABLE IF NOT EXISTS ontology_change_log (
  change_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  change_type TEXT NOT NULL,  -- 'concept_added', 'concept_modified', 'concept_deprecated', 'relationship_added', 'relationship_removed'
  concept_uri TEXT NOT NULL,
  old_value JSONB,  -- Previous state
  new_value JSONB,  -- New state
  changed_by TEXT NOT NULL,
  changed_at TIMESTAMPTZ DEFAULT NOW(),
  change_reason TEXT,
  affected_agents TEXT[],  -- Which agents were notified/updated
  migration_script TEXT,  -- Optional SQL for data migration
  metadata JSONB
);

CREATE INDEX idx_ontology_changes_concept ON ontology_change_log(concept_uri);
CREATE INDEX idx_ontology_changes_date ON ontology_change_log(changed_at);
CREATE INDEX idx_ontology_changes_type ON ontology_change_log(change_type);

-- Mapping cache for successful transformations
CREATE TABLE IF NOT EXISTS normalization_mapping_cache (
  cache_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  source_field TEXT NOT NULL,
  source_value TEXT,
  source_pattern TEXT,  -- Regex pattern if applicable
  target_field TEXT NOT NULL,
  target_value TEXT,
  transformation_type TEXT,  -- 'direct', 'enum_mapping', 'formula', 'ml_prediction', 'llm_extraction'
  confidence FLOAT NOT NULL,
  agent_id TEXT NOT NULL,
  ontology_concept_uri TEXT,
  usage_count INT DEFAULT 1,
  success_rate FLOAT DEFAULT 1.0,  -- Track accuracy over time
  last_used_at TIMESTAMPTZ DEFAULT NOW(),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  expires_at TIMESTAMPTZ,  -- Optional TTL
  metadata JSONB
);

CREATE INDEX idx_mapping_cache_source ON normalization_mapping_cache(source_field, source_pattern);
CREATE INDEX idx_mapping_cache_agent ON normalization_mapping_cache(agent_id);
CREATE INDEX idx_mapping_cache_usage ON normalization_mapping_cache(usage_count DESC, success_rate DESC);

-- Function to get mapping from cache
CREATE OR REPLACE FUNCTION get_cached_mapping(
  p_source_field TEXT,
  p_source_value TEXT DEFAULT NULL,
  p_min_confidence FLOAT DEFAULT 0.70
)
RETURNS TABLE (
  target_field TEXT,
  target_value TEXT,
  transformation_type TEXT,
  confidence FLOAT,
  ontology_concept_uri TEXT
) AS $$
BEGIN
  RETURN QUERY
  SELECT 
    m.target_field,
    m.target_value,
    m.transformation_type,
    m.confidence,
    m.ontology_concept_uri
  FROM normalization_mapping_cache m
  WHERE m.source_field = p_source_field
    AND (p_source_value IS NULL OR m.source_value = p_source_value OR p_source_value ~ m.source_pattern)
    AND m.confidence >= p_min_confidence
    AND (m.expires_at IS NULL OR m.expires_at > NOW())
  ORDER BY m.confidence DESC, m.usage_count DESC, m.success_rate DESC
  LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- Function to update cache usage
CREATE OR REPLACE FUNCTION record_mapping_usage(
  p_cache_id UUID,
  p_success BOOLEAN
)
RETURNS VOID AS $$
BEGIN
  UPDATE normalization_mapping_cache
  SET 
    usage_count = usage_count + 1,
    success_rate = (success_rate * usage_count + CASE WHEN p_success THEN 1.0 ELSE 0.0 END) / (usage_count + 1),
    last_used_at = NOW()
  WHERE cache_id = p_cache_id;
END;
$$ LANGUAGE plpgsql;

-- Concept usage tracking (which agents use which concepts)
CREATE TABLE IF NOT EXISTS ontology_concept_usage (
  usage_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  concept_uri TEXT NOT NULL,
  agent_id TEXT NOT NULL,
  usage_type TEXT,  -- 'resolve', 'expand', 'map_enum', 'constraint'
  usage_count INT DEFAULT 1,
  last_used_at TIMESTAMPTZ DEFAULT NOW(),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_concept_usage_unique ON ontology_concept_usage(concept_uri, agent_id, usage_type);
CREATE INDEX idx_concept_usage_concept ON ontology_concept_usage(concept_uri, usage_count DESC);

-- Function to track concept usage
CREATE OR REPLACE FUNCTION track_concept_usage(
  p_concept_uri TEXT,
  p_agent_id TEXT,
  p_usage_type TEXT DEFAULT 'resolve'
)
RETURNS VOID AS $$
BEGIN
  INSERT INTO ontology_concept_usage (concept_uri, agent_id, usage_type, usage_count, last_used_at)
  VALUES (p_concept_uri, p_agent_id, p_usage_type, 1, NOW())
  ON CONFLICT (concept_uri, agent_id, usage_type)
  DO UPDATE SET
    usage_count = ontology_concept_usage.usage_count + 1,
    last_used_at = NOW();
END;
$$ LANGUAGE plpgsql;

-- Hot concepts view (most frequently used)
CREATE OR REPLACE VIEW v_hot_ontology_concepts AS
SELECT 
  c.concept_uri,
  c.pref_label,
  c.broader_uri,
  COUNT(DISTINCT u.agent_id) as agent_count,
  SUM(u.usage_count) as total_usage,
  MAX(u.last_used_at) as last_used_at
FROM ontology_concepts c
LEFT JOIN ontology_concept_usage u ON c.concept_uri = u.concept_uri
GROUP BY c.concept_uri, c.pref_label, c.broader_uri
ORDER BY total_usage DESC NULLS LAST;

-- Pending proposals view (for curator dashboard)
CREATE OR REPLACE VIEW v_pending_concept_proposals AS
SELECT 
  p.id,
  p.proposed_concept_uri,
  p.pref_label,
  p.broader_uri,
  parent.pref_label as parent_label,
  p.source,
  p.source_agent_id,
  p.confidence,
  p.examples,
  p.justification,
  p.proposed_at,
  p.proposed_by,
  -- Check if similar concept already exists
  EXISTS(
    SELECT 1 FROM ontology_concepts c 
    WHERE c.pref_label ILIKE p.pref_label 
       OR p.pref_label = ANY(c.alt_labels)
  ) as potential_duplicate
FROM ontology_concept_proposals p
LEFT JOIN ontology_concepts parent ON p.broader_uri = parent.concept_uri
WHERE p.status = 'pending'
ORDER BY p.confidence DESC, p.proposed_at ASC;

COMMENT ON TABLE ontology_concept_proposals IS 'Proposed new ontology concepts from agents or humans for curator review';
COMMENT ON TABLE ontology_change_log IS 'Complete audit trail of all ontology modifications';
COMMENT ON TABLE normalization_mapping_cache IS 'Cache of successful field transformations for reuse and performance';
COMMENT ON TABLE ontology_concept_usage IS 'Tracks which agents use which concepts and how frequently';

