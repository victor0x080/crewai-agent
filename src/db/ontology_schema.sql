-- ============================================================================
-- Ontology Schema for Supabase
-- Creates tables for SKOS ontology, mappings, constraints, shapes, and agent profiles
-- ============================================================================

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- Ontology Concepts (SKOS)
-- ============================================================================
CREATE TABLE IF NOT EXISTS ontology_concepts (
  concept_uri VARCHAR(500) PRIMARY KEY,
  scheme_uri VARCHAR(500) NOT NULL,
  pref_label VARCHAR(255) NOT NULL,
  alt_labels TEXT[], -- synonyms (SKOS altLabel)
  definition TEXT,
  broader_uri VARCHAR(500) REFERENCES ontology_concepts(concept_uri),
  narrower_uris TEXT[],
  related_uris TEXT[],
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_ontology_concepts_scheme ON ontology_concepts(scheme_uri);
CREATE INDEX IF NOT EXISTS idx_ontology_concepts_pref_label ON ontology_concepts(pref_label);
CREATE INDEX IF NOT EXISTS idx_ontology_concepts_broader ON ontology_concepts(broader_uri);

-- ============================================================================
-- Ontology Mappings (Enum/Unit/ID Translations)
-- ============================================================================
CREATE TABLE IF NOT EXISTS ontology_mappings (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  concept_uri VARCHAR(500) REFERENCES ontology_concepts(concept_uri),
  source_field VARCHAR(255) NOT NULL,
  source_value VARCHAR(255) NOT NULL,
  target_value VARCHAR(255) NOT NULL,
  mapping_type VARCHAR(50), -- 'enum', 'unit', 'id'
  confidence FLOAT DEFAULT 1.0,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE(source_field, source_value, concept_uri)
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_ontology_mappings_concept ON ontology_mappings(concept_uri);
CREATE INDEX IF NOT EXISTS idx_ontology_mappings_source ON ontology_mappings(source_field, source_value);

-- ============================================================================
-- Ontology Constraints (Policies)
-- ============================================================================
CREATE TABLE IF NOT EXISTS ontology_constraints (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  concept_uri VARCHAR(500) REFERENCES ontology_concepts(concept_uri),
  constraint_type VARCHAR(100) NOT NULL, -- 'minMarginPct', 'floorPrice', 'maxDiscount', etc.
  constraint_value JSONB NOT NULL, -- Flexible value storage
  applies_to VARCHAR(500), -- Optional: specific entity or context
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_ontology_constraints_concept ON ontology_constraints(concept_uri);
CREATE INDEX IF NOT EXISTS idx_ontology_constraints_type ON ontology_constraints(constraint_type);

-- ============================================================================
-- Ontology Shapes (SHACL Validation)
-- ============================================================================
CREATE TABLE IF NOT EXISTS ontology_shapes (
  shape_uri VARCHAR(500) PRIMARY KEY,
  target_class VARCHAR(500) NOT NULL,
  shape_definition JSONB NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_ontology_shapes_target ON ontology_shapes(target_class);

-- ============================================================================
-- Agent Ontology Profiles
-- ============================================================================
CREATE TABLE IF NOT EXISTS agent_ontology_profiles (
  agent_id VARCHAR(255) PRIMARY KEY,
  interests_concepts_must TEXT[], -- Required concepts
  interests_concepts_any TEXT[], -- Optional concepts
  interests_entities JSONB, -- {type: 'ex:Product', where: {category_in: [...]}}
  input_schema_uri VARCHAR(500),
  output_schema_uri VARCHAR(500),
  constraints_from TEXT[], -- Concept URIs to fetch policies from
  shacl_shape_uri VARCHAR(500),
  tools TEXT[], -- Ontology operations this agent uses
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_agent_profiles_interests_must ON agent_ontology_profiles USING GIN(interests_concepts_must);
CREATE INDEX IF NOT EXISTS idx_agent_profiles_interests_any ON agent_ontology_profiles USING GIN(interests_concepts_any);

-- ============================================================================
-- Helper Functions
-- ============================================================================

-- Function to resolve a concept term to URI
CREATE OR REPLACE FUNCTION resolve_concept(term TEXT)
RETURNS VARCHAR(500) AS $$
  SELECT concept_uri
  FROM ontology_concepts
  WHERE pref_label ILIKE '%' || term || '%'
     OR term = ANY(alt_labels)
  ORDER BY CASE WHEN pref_label ILIKE term THEN 1 ELSE 2 END
  LIMIT 1;
$$ LANGUAGE SQL STABLE;

-- Function to expand concepts via SKOS relations
-- Simplified version that handles broader and narrower relations
CREATE OR REPLACE FUNCTION expand_concepts(
  concept_uris TEXT[],
  relations TEXT[] DEFAULT ARRAY['broader', 'narrower', 'related']
)
RETURNS TEXT[] AS $$
  WITH expanded AS (
    -- Start with initial concepts
    SELECT concept_uri::TEXT
    FROM ontology_concepts
    WHERE concept_uri = ANY(concept_uris)
    
    UNION
    
    -- Add broader concepts
    SELECT oc.broader_uri::TEXT
    FROM ontology_concepts oc
    WHERE oc.concept_uri = ANY(concept_uris)
      AND 'broader' = ANY(relations)
      AND oc.broader_uri IS NOT NULL
    
    UNION
    
    -- Add narrower concepts
    SELECT narrower_uri::TEXT
    FROM ontology_concepts oc
    CROSS JOIN LATERAL unnest(oc.narrower_uris) AS narrower_uri
    WHERE oc.concept_uri = ANY(concept_uris)
      AND 'narrower' = ANY(relations)
      AND oc.narrower_uris IS NOT NULL
      AND array_length(oc.narrower_uris, 1) > 0
  )
  SELECT ARRAY_AGG(DISTINCT concept_uri)
  FROM expanded
  WHERE concept_uri IS NOT NULL;
$$ LANGUAGE SQL STABLE;

-- Function to find agents interested in concepts
CREATE OR REPLACE FUNCTION find_interested_agents(concept_uris TEXT[])
RETURNS TABLE (
  agent_id VARCHAR(255),
  match_type VARCHAR(50),
  matched_concepts TEXT[]
) AS $$
BEGIN
  RETURN QUERY
  WITH matched_agents AS (
    -- Agents with must concepts (ALL must concepts must be in input concepts)
    SELECT 
      aop.agent_id,
      'must'::VARCHAR(50) AS match_type,
      ARRAY_AGG(DISTINCT must_concept) FILTER (WHERE must_concept = ANY(concept_uris)) AS matched_concepts
    FROM agent_ontology_profiles aop
    CROSS JOIN LATERAL unnest(aop.interests_concepts_must) AS must_concept
    WHERE aop.interests_concepts_must IS NOT NULL 
      AND array_length(aop.interests_concepts_must, 1) > 0
    GROUP BY aop.agent_id, aop.interests_concepts_must
    HAVING COUNT(DISTINCT must_concept) FILTER (WHERE must_concept = ANY(concept_uris)) = array_length(aop.interests_concepts_must, 1)
    
    UNION
    
    -- Agents with any concepts (at least one matches)
    SELECT DISTINCT
      aop.agent_id,
      'any'::VARCHAR(50) AS match_type,
      ARRAY_AGG(DISTINCT any_concept) FILTER (WHERE any_concept = ANY(concept_uris)) AS matched_concepts
    FROM agent_ontology_profiles aop
    CROSS JOIN LATERAL unnest(aop.interests_concepts_any) AS any_concept
    WHERE aop.interests_concepts_any IS NOT NULL 
      AND array_length(aop.interests_concepts_any, 1) > 0
      AND any_concept = ANY(concept_uris)
    GROUP BY aop.agent_id
  )
  SELECT 
    ma.agent_id,
    ma.match_type,
    ma.matched_concepts
  FROM matched_agents ma
  WHERE ma.matched_concepts IS NOT NULL
    AND array_length(ma.matched_concepts, 1) > 0
  ORDER BY 
    CASE WHEN ma.match_type = 'must' THEN 1 ELSE 2 END,
    array_length(ma.matched_concepts, 1) DESC;
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================================================
-- Comments
-- ============================================================================

COMMENT ON TABLE ontology_concepts IS 'SKOS ontology concepts with labels, definitions, and hierarchical relationships';
COMMENT ON TABLE ontology_mappings IS 'Enum/unit/ID translations between different systems';
COMMENT ON TABLE ontology_constraints IS 'Business policy constraints (e.g., minMarginPct, floorPrice)';
COMMENT ON TABLE ontology_shapes IS 'SHACL validation shapes for data quality';
COMMENT ON TABLE agent_ontology_profiles IS 'Agent capability profiles for semantic discovery';

