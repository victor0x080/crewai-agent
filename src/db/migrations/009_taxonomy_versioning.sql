-- ============================================================================
-- Taxonomy Versioning & Tracking
-- Manages product/campaign/audience taxonomy evolution with full version history
-- Enables cross-version mapping for backward compatibility
-- ============================================================================

-- Taxonomy versions
CREATE TABLE IF NOT EXISTS taxonomy_versions (
  version_id SERIAL PRIMARY KEY,
  taxonomy_type TEXT NOT NULL,  -- 'product_category', 'campaign_tactic', 'audience_lifecycle', 'promo_type', 'kpi'
  version_number TEXT NOT NULL,  -- 'v1.0', 'v1.1', 'v2.0' (semantic versioning)
  effective_date DATE NOT NULL,
  end_date DATE,  -- NULL if current version
  is_current BOOLEAN DEFAULT FALSE,
  created_by TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  change_summary TEXT,
  change_notes JSONB,  -- Detailed changelog
  approval_status TEXT DEFAULT 'draft',  -- draft, review, approved, deprecated
  approved_by TEXT,
  approved_at TIMESTAMPTZ,
  metadata JSONB,
  UNIQUE(taxonomy_type, version_number)
);

CREATE INDEX idx_taxonomy_versions_type_current ON taxonomy_versions(taxonomy_type, is_current);
CREATE INDEX idx_taxonomy_versions_effective ON taxonomy_versions(effective_date);

-- Taxonomy nodes (versioned hierarchies)
CREATE TABLE IF NOT EXISTS taxonomy_nodes (
  node_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  version_id INT NOT NULL REFERENCES taxonomy_versions(version_id) ON DELETE CASCADE,
  node_uri TEXT NOT NULL,  -- Unique URI for this concept
  node_label TEXT NOT NULL,
  node_definition TEXT,
  parent_uri TEXT,  -- Parent in hierarchy
  node_level INT,  -- Depth in hierarchy (0 = root)
  sort_order INT,
  attributes JSONB,  -- Additional attributes (e.g., { "color": "blue", "icon": "tag" })
  is_leaf BOOLEAN DEFAULT TRUE,  -- Has no children
  is_deprecated BOOLEAN DEFAULT FALSE,
  deprecated_reason TEXT,
  metadata JSONB,
  UNIQUE(version_id, node_uri)
);

CREATE INDEX idx_taxonomy_nodes_version ON taxonomy_nodes(version_id);
CREATE INDEX idx_taxonomy_nodes_parent ON taxonomy_nodes(version_id, parent_uri);
CREATE INDEX idx_taxonomy_nodes_uri ON taxonomy_nodes(node_uri);
CREATE INDEX idx_taxonomy_nodes_label ON taxonomy_nodes(node_label);

-- Taxonomy change log (tracks evolution)
CREATE TABLE IF NOT EXISTS taxonomy_changes (
  change_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  from_version_id INT REFERENCES taxonomy_versions(version_id),
  to_version_id INT NOT NULL REFERENCES taxonomy_versions(version_id),
  change_type TEXT NOT NULL,  -- 'add', 'modify', 'rename', 'move', 'split', 'merge', 'deprecate'
  affected_nodes JSONB NOT NULL,  -- Array of {uri, label, parent_uri}
  change_details JSONB,  -- Type-specific details
  impact_assessment TEXT,  -- How many records affected
  migration_required BOOLEAN DEFAULT FALSE,
  migration_script TEXT,
  changed_at TIMESTAMPTZ DEFAULT NOW(),
  changed_by TEXT,
  metadata JSONB
);

CREATE INDEX idx_taxonomy_changes_version ON taxonomy_changes(to_version_id);
CREATE INDEX idx_taxonomy_changes_type ON taxonomy_changes(change_type);

-- Cross-version mappings (enables backward compatibility)
CREATE TABLE IF NOT EXISTS taxonomy_mappings (
  mapping_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  from_version_id INT NOT NULL REFERENCES taxonomy_versions(version_id),
  to_version_id INT NOT NULL REFERENCES taxonomy_versions(version_id),
  from_uri TEXT NOT NULL,
  to_uris TEXT[] NOT NULL,  -- Can be 1→1, 1→many (split), or many→1 (merge)
  mapping_type TEXT NOT NULL,  -- 'exact', 'broader', 'narrower', 'related', 'split', 'merge'
  confidence FLOAT DEFAULT 1.0,
  mapping_logic TEXT,  -- How the mapping was determined
  is_automatic BOOLEAN DEFAULT TRUE,
  created_by TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  validated BOOLEAN DEFAULT FALSE,
  validated_by TEXT,
  validated_at TIMESTAMPTZ,
  metadata JSONB,
  UNIQUE(from_version_id, to_version_id, from_uri)
);

CREATE INDEX idx_taxonomy_mappings_from ON taxonomy_mappings(from_version_id, from_uri);
CREATE INDEX idx_taxonomy_mappings_to ON taxonomy_mappings(to_version_id);

-- Function to get current version
CREATE OR REPLACE FUNCTION get_current_taxonomy_version(p_taxonomy_type TEXT)
RETURNS INT AS $$
DECLARE
  v_version_id INT;
BEGIN
  SELECT version_id INTO v_version_id
  FROM taxonomy_versions
  WHERE taxonomy_type = p_taxonomy_type
    AND is_current = TRUE
  LIMIT 1;
  
  RETURN v_version_id;
END;
$$ LANGUAGE plpgsql;

-- Function to map concept across versions
CREATE OR REPLACE FUNCTION map_taxonomy_concept(
  p_from_uri TEXT,
  p_from_version TEXT,
  p_to_version TEXT DEFAULT NULL,  -- NULL = map to current
  p_taxonomy_type TEXT DEFAULT 'product_category'
)
RETURNS TABLE (
  to_uri TEXT,
  mapping_type TEXT,
  confidence FLOAT
) AS $$
DECLARE
  v_from_version_id INT;
  v_to_version_id INT;
BEGIN
  -- Get version IDs
  SELECT version_id INTO v_from_version_id
  FROM taxonomy_versions
  WHERE taxonomy_type = p_taxonomy_type
    AND version_number = p_from_version;
  
  IF p_to_version IS NULL THEN
    v_to_version_id := get_current_taxonomy_version(p_taxonomy_type);
  ELSE
    SELECT version_id INTO v_to_version_id
    FROM taxonomy_versions
    WHERE taxonomy_type = p_taxonomy_type
      AND version_number = p_to_version;
  END IF;
  
  -- If same version, return original
  IF v_from_version_id = v_to_version_id THEN
    RETURN QUERY SELECT p_from_uri, 'exact'::TEXT, 1.0::FLOAT;
    RETURN;
  END IF;
  
  -- Find direct mapping
  RETURN QUERY
  SELECT 
    UNNEST(m.to_uris) as to_uri,
    m.mapping_type,
    m.confidence
  FROM taxonomy_mappings m
  WHERE m.from_version_id = v_from_version_id
    AND m.to_version_id = v_to_version_id
    AND m.from_uri = p_from_uri
  ORDER BY m.confidence DESC;
  
  -- If no mapping found, try chained mapping (multi-hop)
  -- This would require recursive CTE for multi-version jumps
END;
$$ LANGUAGE plpgsql;

-- Function to get taxonomy hierarchy
CREATE OR REPLACE FUNCTION get_taxonomy_hierarchy(
  p_taxonomy_type TEXT,
  p_version TEXT DEFAULT NULL,  -- NULL = current version
  p_root_uri TEXT DEFAULT NULL  -- NULL = full hierarchy
)
RETURNS TABLE (
  node_uri TEXT,
  node_label TEXT,
  parent_uri TEXT,
  node_level INT,
  full_path TEXT
) AS $$
DECLARE
  v_version_id INT;
BEGIN
  -- Get version
  IF p_version IS NULL THEN
    v_version_id := get_current_taxonomy_version(p_taxonomy_type);
  ELSE
    SELECT version_id INTO v_version_id
    FROM taxonomy_versions
    WHERE taxonomy_type = p_taxonomy_type
      AND version_number = p_version;
  END IF;
  
  -- Return hierarchy with paths
  RETURN QUERY
  WITH RECURSIVE hierarchy AS (
    -- Base case: root nodes
    SELECT 
      n.node_uri,
      n.node_label,
      n.parent_uri,
      n.node_level,
      n.node_label as full_path,
      0 as depth
    FROM taxonomy_nodes n
    WHERE n.version_id = v_version_id
      AND (p_root_uri IS NULL AND n.parent_uri IS NULL 
           OR p_root_uri IS NOT NULL AND n.node_uri = p_root_uri)
      AND n.is_deprecated = FALSE
    
    UNION ALL
    
    -- Recursive case: children
    SELECT 
      n.node_uri,
      n.node_label,
      n.parent_uri,
      n.node_level,
      h.full_path || ' > ' || n.node_label,
      h.depth + 1
    FROM taxonomy_nodes n
    INNER JOIN hierarchy h ON n.parent_uri = h.node_uri
    WHERE n.version_id = v_version_id
      AND n.is_deprecated = FALSE
  )
  SELECT 
    h.node_uri,
    h.node_label,
    h.parent_uri,
    h.node_level,
    h.full_path
  FROM hierarchy h
  ORDER BY h.full_path;
END;
$$ LANGUAGE plpgsql;

-- View: Current taxonomies
CREATE OR REPLACE VIEW v_current_taxonomies AS
SELECT 
  v.taxonomy_type,
  v.version_number,
  v.effective_date,
  COUNT(n.node_id) as node_count,
  COUNT(DISTINCT n.node_level) as hierarchy_depth,
  v.created_by,
  v.created_at
FROM taxonomy_versions v
LEFT JOIN taxonomy_nodes n ON v.version_id = n.version_id AND n.is_deprecated = FALSE
WHERE v.is_current = TRUE
GROUP BY v.version_id, v.taxonomy_type, v.version_number, v.effective_date, v.created_by, v.created_at;

-- View: Taxonomy evolution summary
CREATE OR REPLACE VIEW v_taxonomy_evolution AS
SELECT 
  v.taxonomy_type,
  v.version_number,
  v.effective_date,
  v.end_date,
  v.is_current,
  COUNT(DISTINCT c.change_id) as change_count,
  JSONB_AGG(DISTINCT c.change_type) as change_types,
  v.change_summary
FROM taxonomy_versions v
LEFT JOIN taxonomy_changes c ON v.version_id = c.to_version_id
GROUP BY v.version_id, v.taxonomy_type, v.version_number, v.effective_date, v.end_date, v.is_current, v.change_summary
ORDER BY v.taxonomy_type, v.effective_date DESC;

-- Trigger to maintain is_current flag
CREATE OR REPLACE FUNCTION maintain_current_version()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.is_current = TRUE THEN
    -- Set all other versions of same type to not current
    UPDATE taxonomy_versions
    SET is_current = FALSE, end_date = CURRENT_DATE
    WHERE taxonomy_type = NEW.taxonomy_type
      AND version_id != NEW.version_id
      AND is_current = TRUE;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_maintain_current_version
  BEFORE INSERT OR UPDATE ON taxonomy_versions
  FOR EACH ROW
  WHEN (NEW.is_current = TRUE)
  EXECUTE FUNCTION maintain_current_version();

-- Seed initial product category taxonomy (v1.0)
INSERT INTO taxonomy_versions (taxonomy_type, version_number, effective_date, is_current, created_by, change_summary, approval_status, approved_by, approved_at)
VALUES 
  ('product_category', 'v1.0', CURRENT_DATE, TRUE, 'system', 'Initial taxonomy version', 'approved', 'system', NOW()),
  ('campaign_tactic', 'v1.0', CURRENT_DATE, TRUE, 'system', 'Initial taxonomy version', 'approved', 'system', NOW()),
  ('audience_lifecycle', 'v1.0', CURRENT_DATE, TRUE, 'system', 'Initial taxonomy version', 'approved', 'system', NOW()),
  ('promo_type', 'v1.0', CURRENT_DATE, TRUE, 'system', 'Initial taxonomy version', 'approved', 'system', NOW()),
  ('kpi', 'v1.0', CURRENT_DATE, TRUE, 'system', 'Initial taxonomy version', 'approved', 'system', NOW())
ON CONFLICT (taxonomy_type, version_number) DO NOTHING;

COMMENT ON TABLE taxonomy_versions IS 'Versions of taxonomies with semantic versioning';
COMMENT ON TABLE taxonomy_nodes IS 'Taxonomy node definitions for each version';
COMMENT ON TABLE taxonomy_changes IS 'Log of taxonomy changes between versions';
COMMENT ON TABLE taxonomy_mappings IS 'Cross-version concept mappings for backward compatibility';

