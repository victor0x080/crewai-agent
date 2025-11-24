-- ============================================================================
-- Canonical Data Model (CDM) - Trade Desk Schema
-- Star schema for normalized retail media, POS, and attribution data
-- Versioned with explicit field ownership by agents
-- ============================================================================

-- =============================================================================
-- DIMENSION TABLES
-- =============================================================================

-- Dim: Product
CREATE TABLE IF NOT EXISTS dim_product (
  product_key BIGSERIAL PRIMARY KEY,
  product_id TEXT NOT NULL,  -- Natural key (GTIN, UPC, ASIN, etc.)
  product_id_type TEXT NOT NULL,  -- 'GTIN-14', 'UPC-12', 'ASIN', 'SKU'
  product_title TEXT,
  brand TEXT,
  manufacturer TEXT,
  category_uri TEXT,  -- Links to taxonomy
  subcategory_uri TEXT,
  pack_size NUMERIC,
  pack_unit TEXT,
  unit_price NUMERIC,
  attributes JSONB,  -- Additional product attributes
  valid_from DATE NOT NULL,
  valid_to DATE,
  is_current BOOLEAN DEFAULT TRUE,
  data_source TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(product_id, product_id_type, valid_from)
);

CREATE INDEX idx_dim_product_id ON dim_product(product_id, product_id_type) WHERE is_current = TRUE;
CREATE INDEX idx_dim_product_category ON dim_product(category_uri);
CREATE INDEX idx_dim_product_brand ON dim_product(brand);

-- Dim: Campaign
CREATE TABLE IF NOT EXISTS dim_campaign (
  campaign_key BIGSERIAL PRIMARY KEY,
  campaign_id TEXT NOT NULL,
  campaign_name TEXT,
  rmn_source TEXT NOT NULL,  -- 'amazon_ads', 'walmart_connect', etc.
  tactic_uri TEXT,  -- Links to tactic taxonomy: ex:SponsoredProduct
  ad_format TEXT,  -- 'search', 'display', 'video', 'ctv'
  objective TEXT,  -- 'awareness', 'consideration', 'conversion'
  targeting_type TEXT,
  funnel_stage TEXT,
  daily_budget NUMERIC,
  start_date DATE,
  end_date DATE,
  status TEXT,
  attributes JSONB,
  valid_from DATE NOT NULL,
  valid_to DATE,
  is_current BOOLEAN DEFAULT TRUE,
  data_source TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(campaign_id, rmn_source, valid_from)
);

CREATE INDEX idx_dim_campaign_id ON dim_campaign(campaign_id, rmn_source) WHERE is_current = TRUE;
CREATE INDEX idx_dim_campaign_tactic ON dim_campaign(tactic_uri);
CREATE INDEX idx_dim_campaign_rmn ON dim_campaign(rmn_source);

-- Dim: Audience
CREATE TABLE IF NOT EXISTS dim_audience (
  audience_key BIGSERIAL PRIMARY KEY,
  audience_id TEXT NOT NULL,
  audience_name TEXT,
  rmn_source TEXT NOT NULL,
  lifecycle_stage TEXT,  -- 'prospect', 'new', 'active', 'lapsed', 'churned'
  value_tier TEXT,  -- 'high', 'medium', 'low'
  tenure_days INT,
  recency_days INT,
  frequency_visits INT,
  attributes JSONB,  -- Demographics, behaviors
  valid_from DATE NOT NULL,
  valid_to DATE,
  is_current BOOLEAN DEFAULT TRUE,
  data_source TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(audience_id, rmn_source, valid_from)
);

CREATE INDEX idx_dim_audience_id ON dim_audience(audience_id, rmn_source) WHERE is_current = TRUE;
CREATE INDEX idx_dim_audience_lifecycle ON dim_audience(lifecycle_stage);

-- Dim: Store
CREATE TABLE IF NOT EXISTS dim_store (
  store_key BIGSERIAL PRIMARY KEY,
  store_id TEXT NOT NULL,
  store_name TEXT,
  retailer TEXT NOT NULL,
  store_format TEXT,  -- 'superstore', 'neighborhood', 'ecommerce'
  address TEXT,
  city TEXT,
  state TEXT,
  zip_code TEXT,
  country TEXT DEFAULT 'US',
  geo_lat NUMERIC,
  geo_lon NUMERIC,
  open_date DATE,
  close_date DATE,
  is_active BOOLEAN DEFAULT TRUE,
  attributes JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(store_id, retailer)
);

CREATE INDEX idx_dim_store_id ON dim_store(store_id, retailer);
CREATE INDEX idx_dim_store_location ON dim_store(state, city);

-- Dim: Time (pre-populated)
CREATE TABLE IF NOT EXISTS dim_time (
  time_key INT PRIMARY KEY,  -- YYYYMMDD format
  date_actual DATE NOT NULL UNIQUE,
  day_of_week INT,
  day_name TEXT,
  week_of_year INT,
  month INT,
  month_name TEXT,
  quarter INT,
  year INT,
  is_weekend BOOLEAN,
  is_holiday BOOLEAN,
  holiday_name TEXT,
  fiscal_year INT,
  fiscal_quarter INT,
  fiscal_period INT
);

CREATE INDEX idx_dim_time_date ON dim_time(date_actual);
CREATE INDEX idx_dim_time_year_month ON dim_time(year, month);

-- Dim: KPI
CREATE TABLE IF NOT EXISTS dim_kpi (
  kpi_key BIGSERIAL PRIMARY KEY,
  kpi_id TEXT NOT NULL UNIQUE,
  kpi_name TEXT NOT NULL,
  kpi_family TEXT,  -- 'efficiency', 'volume', 'incrementality'
  formula TEXT,
  unit TEXT,
  attribution_window_days INT,
  attribution_model TEXT,  -- 'last_click', 'multi_touch', 'first_touch'
  is_incremental BOOLEAN DEFAULT FALSE,
  baseline_definition TEXT,
  ontology_uri TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_dim_kpi_family ON dim_kpi(kpi_family);

-- Dim: Manufacturer
CREATE TABLE IF NOT EXISTS dim_manufacturer (
  manufacturer_key BIGSERIAL PRIMARY KEY,
  manufacturer_id TEXT NOT NULL UNIQUE,
  manufacturer_name TEXT NOT NULL,
  parent_company TEXT,
  country TEXT,
  tier TEXT,  -- 'tier1', 'tier2', 'tier3'
  attributes JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Dim: Retailer
CREATE TABLE IF NOT EXISTS dim_retailer (
  retailer_key BIGSERIAL PRIMARY KEY,
  retailer_id TEXT NOT NULL UNIQUE,
  retailer_name TEXT NOT NULL,
  retailer_type TEXT,  -- 'grocery', 'mass', 'club', 'specialty'
  rmn_platform TEXT,  -- 'amazon_ads', 'walmart_connect', etc.
  country TEXT,
  attributes JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- FACT TABLES
-- =============================================================================

-- Fact: Media Performance
CREATE TABLE IF NOT EXISTS fact_media_performance (
  media_performance_id BIGSERIAL PRIMARY KEY,
  
  -- Dimensions (foreign keys)
  time_key INT NOT NULL REFERENCES dim_time(time_key),
  campaign_key BIGINT NOT NULL REFERENCES dim_campaign(campaign_key),
  product_key BIGINT REFERENCES dim_product(product_key),
  audience_key BIGINT REFERENCES dim_audience(audience_key),
  retailer_key BIGINT REFERENCES dim_retailer(retailer_key),
  manufacturer_key BIGINT REFERENCES dim_manufacturer(manufacturer_key),
  
  -- Metrics (additive)
  impressions_count BIGINT DEFAULT 0,
  clicks_count BIGINT DEFAULT 0,
  conversions_count BIGINT DEFAULT 0,
  spend_amount NUMERIC(15,2) DEFAULT 0,
  revenue_amount NUMERIC(15,2) DEFAULT 0,
  orders_count INT DEFAULT 0,
  units_sold INT DEFAULT 0,
  
  -- Derived metrics (non-additive, computed on query)
  -- ctr = clicks_count / NULLIF(impressions_count, 0)
  -- cpm = (spend_amount / NULLIF(impressions_count, 0)) * 1000
  -- cpc = spend_amount / NULLIF(clicks_count, 0)
  -- roas = revenue_amount / NULLIF(spend_amount, 0)
  -- conversion_rate = conversions_count / NULLIF(clicks_count, 0)
  
  -- Metadata
  data_source TEXT NOT NULL,
  normalization_run_id UUID,
  confidence_score NUMERIC(3,2),
  normalized_at TIMESTAMPTZ DEFAULT NOW(),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_fact_media_time ON fact_media_performance(time_key);
CREATE INDEX idx_fact_media_campaign ON fact_media_performance(campaign_key);
CREATE INDEX idx_fact_media_product ON fact_media_performance(product_key);
CREATE INDEX idx_fact_media_source ON fact_media_performance(data_source);
CREATE INDEX idx_fact_media_normalized ON fact_media_performance(normalized_at);

-- Unique index for grain: day × campaign × product × audience
-- Uses COALESCE to handle NULL values in product_key and audience_key
CREATE UNIQUE INDEX idx_fact_media_unique_grain ON fact_media_performance(
  time_key, 
  campaign_key, 
  COALESCE(product_key, -1), 
  COALESCE(audience_key, -1)
);

-- Fact: POS Performance
CREATE TABLE IF NOT EXISTS fact_pos_performance (
  pos_performance_id BIGSERIAL PRIMARY KEY,
  
  -- Dimensions
  time_key INT NOT NULL REFERENCES dim_time(time_key),
  store_key BIGINT NOT NULL REFERENCES dim_store(store_key),
  product_key BIGINT NOT NULL REFERENCES dim_product(product_key),
  manufacturer_key BIGINT REFERENCES dim_manufacturer(manufacturer_key),
  retailer_key BIGINT REFERENCES dim_retailer(retailer_key),
  
  -- Metrics
  units_sold INT DEFAULT 0,
  revenue_amount NUMERIC(15,2) DEFAULT 0,
  cost_amount NUMERIC(15,2) DEFAULT 0,
  margin_amount NUMERIC(15,2) DEFAULT 0,
  discount_amount NUMERIC(15,2) DEFAULT 0,
  transactions_count INT DEFAULT 0,
  
  -- Promotional flags
  has_promotion BOOLEAN DEFAULT FALSE,
  promo_type TEXT,  -- 'TPR', 'BOGO', 'coupon', 'display'
  promo_discount_pct NUMERIC(5,2),
  has_display BOOLEAN DEFAULT FALSE,
  display_type TEXT,  -- 'end_cap', 'in_aisle', 'pallet'
  
  -- Metadata
  data_source TEXT NOT NULL,
  normalization_run_id UUID,
  confidence_score NUMERIC(3,2),
  normalized_at TIMESTAMPTZ DEFAULT NOW(),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_fact_pos_time ON fact_pos_performance(time_key);
CREATE INDEX idx_fact_pos_store ON fact_pos_performance(store_key);
CREATE INDEX idx_fact_pos_product ON fact_pos_performance(product_key);
CREATE INDEX idx_fact_pos_promo ON fact_pos_performance(has_promotion) WHERE has_promotion = TRUE;

-- Unique index for grain: day × store × product
CREATE UNIQUE INDEX idx_fact_pos_unique_grain ON fact_pos_performance(
  time_key, 
  store_key, 
  product_key
);

-- Fact: Attribution Results
CREATE TABLE IF NOT EXISTS fact_attribution (
  attribution_id BIGSERIAL PRIMARY KEY,
  
  -- Dimensions
  time_key INT NOT NULL REFERENCES dim_time(time_key),
  campaign_key BIGINT NOT NULL REFERENCES dim_campaign(campaign_key),
  product_key BIGINT REFERENCES dim_product(product_key),
  store_key BIGINT REFERENCES dim_store(store_key),
  kpi_key BIGINT NOT NULL REFERENCES dim_kpi(kpi_key),
  manufacturer_key BIGINT REFERENCES dim_manufacturer(manufacturer_key),
  retailer_key BIGINT REFERENCES dim_retailer(retailer_key),
  
  -- Attribution metrics
  baseline_value NUMERIC(15,2),  -- Expected value without campaign
  actual_value NUMERIC(15,2),     -- Observed value
  incremental_value NUMERIC(15,2),  -- actual - baseline
  lift_pct NUMERIC(5,2),  -- (actual - baseline) / baseline * 100
  
  -- Attribution details
  attribution_method TEXT,  -- 'MMM', 'test_control', 'geo_lift', 'synthetic_control'
  confidence_level NUMERIC(3,2),  -- Statistical confidence (0.95 = 95%)
  confidence_interval_lower NUMERIC(15,2),
  confidence_interval_upper NUMERIC(15,2),
  
  -- Metadata
  data_source TEXT NOT NULL,
  normalization_run_id UUID,
  normalized_at TIMESTAMPTZ DEFAULT NOW(),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_fact_attr_time ON fact_attribution(time_key);
CREATE INDEX idx_fact_attr_campaign ON fact_attribution(campaign_key);
CREATE INDEX idx_fact_attr_kpi ON fact_attribution(kpi_key);

-- Unique index for grain: day × campaign × product × store × kpi
-- Uses COALESCE to handle NULL values in product_key and store_key
CREATE UNIQUE INDEX idx_fact_attr_unique_grain ON fact_attribution(
  time_key, 
  campaign_key, 
  COALESCE(product_key, -1), 
  COALESCE(store_key, -1), 
  kpi_key
);

-- =============================================================================
-- FIELD OWNERSHIP METADATA
-- =============================================================================

-- Maps CDM fields to owning agents
CREATE TABLE IF NOT EXISTS cdm_field_ownership (
  field_id SERIAL PRIMARY KEY,
  table_name TEXT NOT NULL,
  field_name TEXT NOT NULL,
  field_type TEXT NOT NULL,  -- 'dimension', 'metric', 'attribute'
  owner_agent_id TEXT NOT NULL,  -- Which agent is responsible for this field
  derivation_logic TEXT,  -- How this field is computed (if derived)
  dependencies TEXT[],  -- Other fields this depends on
  validation_rules JSONB,  -- Field-level validation rules
  ontology_concept_uri TEXT,  -- Link to ontology
  is_required BOOLEAN DEFAULT TRUE,
  default_value TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(table_name, field_name)
);

CREATE INDEX idx_field_ownership_agent ON cdm_field_ownership(owner_agent_id);
CREATE INDEX idx_field_ownership_table ON cdm_field_ownership(table_name);

-- Seed field ownership
INSERT INTO cdm_field_ownership (table_name, field_name, field_type, owner_agent_id, ontology_concept_uri, validation_rules) VALUES
  -- Media metrics
  ('fact_media_performance', 'impressions_count', 'metric', 'metrics-time-agent', 'ex:Impressions', '{"min": 0}'),
  ('fact_media_performance', 'clicks_count', 'metric', 'metrics-time-agent', 'ex:Clicks', '{"min": 0, "max_ratio_to_impressions": 1.0}'),
  ('fact_media_performance', 'spend_amount', 'metric', 'metrics-time-agent', 'ex:Spend', '{"min": 0}'),
  ('fact_media_performance', 'revenue_amount', 'metric', 'metrics-time-agent', 'ex:Revenue', '{"min": 0}'),
  ('fact_media_performance', 'time_key', 'dimension', 'metrics-time-agent', 'ex:Time', '{"format": "YYYYMMDD"}'),
  
  -- Product dimensions
  ('dim_product', 'product_id', 'dimension', 'product-taxonomy-agent', 'ex:Product', '{"required": true}'),
  ('dim_product', 'brand', 'dimension', 'product-taxonomy-agent', 'ex:Brand', NULL),
  ('dim_product', 'category_uri', 'dimension', 'product-taxonomy-agent', 'ex:Category', NULL),
  ('fact_media_performance', 'product_key', 'dimension', 'product-taxonomy-agent', 'ex:Product', NULL),
  ('fact_pos_performance', 'product_key', 'dimension', 'product-taxonomy-agent', 'ex:Product', '{"required": true}'),
  
  -- Campaign dimensions
  ('dim_campaign', 'campaign_id', 'dimension', 'campaign-tactic-agent', 'ex:Campaign', '{"required": true}'),
  ('dim_campaign', 'tactic_uri', 'dimension', 'campaign-tactic-agent', 'ex:Tactic', NULL),
  ('dim_campaign', 'ad_format', 'dimension', 'campaign-tactic-agent', 'ex:AdFormat', NULL),
  ('fact_media_performance', 'campaign_key', 'dimension', 'campaign-tactic-agent', 'ex:Campaign', '{"required": true}'),
  
  -- POS/Promo
  ('fact_pos_performance', 'has_promotion', 'attribute', 'pos-promo-agent', 'ex:Promotion', NULL),
  ('fact_pos_performance', 'promo_type', 'attribute', 'pos-promo-agent', 'ex:PromoType', NULL),
  ('fact_pos_performance', 'units_sold', 'metric', 'pos-promo-agent', 'ex:UnitsSold', '{"min": 0}'),
  ('fact_pos_performance', 'store_key', 'dimension', 'pos-promo-agent', 'ex:Store', '{"required": true}'),
  
  -- Audience
  ('dim_audience', 'audience_id', 'dimension', 'audience-segment-agent', 'ex:Audience', '{"required": true}'),
  ('dim_audience', 'lifecycle_stage', 'attribute', 'audience-segment-agent', 'ex:LifecycleStage', NULL),
  ('fact_media_performance', 'audience_key', 'dimension', 'audience-segment-agent', 'ex:Audience', NULL),
  
  -- KPI/Attribution
  ('fact_attribution', 'kpi_key', 'dimension', 'kpi-attribution-agent', 'ex:KPI', '{"required": true}'),
  ('fact_attribution', 'incremental_value', 'metric', 'kpi-attribution-agent', 'ex:IncrementalValue', NULL),
  ('fact_attribution', 'baseline_value', 'metric', 'kpi-attribution-agent', 'ex:BaselineValue', '{"min": 0}')
ON CONFLICT (table_name, field_name) DO NOTHING;

-- =============================================================================
-- CDM VERSIONING
-- =============================================================================

CREATE TABLE IF NOT EXISTS cdm_schema_versions (
  version_id SERIAL PRIMARY KEY,
  version_number TEXT NOT NULL UNIQUE,  -- 'v1.0.0'
  effective_date DATE NOT NULL,
  end_date DATE,
  is_current BOOLEAN DEFAULT FALSE,
  change_summary TEXT,
  migration_script TEXT,  -- SQL to migrate data
  backward_compatible BOOLEAN DEFAULT TRUE,
  created_by TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  approved_at TIMESTAMPTZ
);

-- Current version
INSERT INTO cdm_schema_versions (version_number, effective_date, is_current, change_summary, created_by, approved_at)
VALUES ('v1.0.0', CURRENT_DATE, TRUE, 'Initial CDM schema for trade desk', 'system', NOW())
ON CONFLICT (version_number) DO NOTHING;

-- Schema change log
CREATE TABLE IF NOT EXISTS cdm_schema_changes (
  change_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  version_id INT REFERENCES cdm_schema_versions(version_id),
  change_type TEXT NOT NULL,  -- 'add_field', 'modify_field', 'deprecate_field', 'add_table'
  affected_tables TEXT[],
  affected_fields TEXT[],
  change_details JSONB,
  impact_assessment TEXT,
  changed_at TIMESTAMPTZ DEFAULT NOW(),
  changed_by TEXT
);

-- =============================================================================
-- CONSTRAINTS & RELATIONSHIPS
-- =============================================================================

-- Cross-table constraints (enforced via triggers or application logic)
CREATE TABLE IF NOT EXISTS cdm_cross_table_constraints (
  constraint_id SERIAL PRIMARY KEY,
  constraint_name TEXT NOT NULL UNIQUE,
  constraint_type TEXT NOT NULL,  -- 'foreign_key', 'sum_check', 'hierarchy', 'uniqueness'
  table_names TEXT[] NOT NULL,
  field_names TEXT[] NOT NULL,
  constraint_logic TEXT NOT NULL,  -- SQL expression or description
  severity TEXT DEFAULT 'error',  -- 'error', 'warning', 'info'
  owner_agent_id TEXT,  -- Typically qa-governance-agent
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed cross-table constraints
INSERT INTO cdm_cross_table_constraints (constraint_name, constraint_type, table_names, field_names, constraint_logic, owner_agent_id) VALUES
  ('clicks_le_impressions', 'sum_check', ARRAY['fact_media_performance'], ARRAY['clicks_count', 'impressions_count'], 'clicks_count <= impressions_count', 'qa-governance-agent'),
  ('spend_positive', 'sum_check', ARRAY['fact_media_performance'], ARRAY['spend_amount'], 'spend_amount >= 0', 'qa-governance-agent'),
  ('product_fk_valid', 'foreign_key', ARRAY['fact_media_performance', 'dim_product'], ARRAY['product_key'], 'All product_key values must exist in dim_product', 'qa-governance-agent'),
  ('campaign_fk_valid', 'foreign_key', ARRAY['fact_media_performance', 'dim_campaign'], ARRAY['campaign_key'], 'All campaign_key values must exist in dim_campaign', 'qa-governance-agent'),
  ('pos_margin_check', 'sum_check', ARRAY['fact_pos_performance'], ARRAY['margin_amount', 'revenue_amount', 'cost_amount'], 'margin_amount = revenue_amount - cost_amount', 'qa-governance-agent')
ON CONFLICT (constraint_name) DO NOTHING;

-- =============================================================================
-- VIEWS FOR COMMON QUERIES
-- =============================================================================

-- Media performance with derived metrics
CREATE OR REPLACE VIEW v_media_performance_enriched AS
SELECT 
  f.*,
  c.campaign_name,
  c.rmn_source,
  c.tactic_uri,
  p.product_title,
  p.brand,
  p.category_uri,
  t.date_actual,
  t.year,
  t.month,
  -- Derived metrics
  CASE WHEN f.impressions_count > 0 
    THEN ROUND((f.clicks_count::NUMERIC / f.impressions_count * 100), 2)
    ELSE 0 
  END as ctr_pct,
  CASE WHEN f.impressions_count > 0 
    THEN ROUND((f.spend_amount / f.impressions_count * 1000), 2)
    ELSE 0 
  END as cpm,
  CASE WHEN f.clicks_count > 0 
    THEN ROUND((f.spend_amount / f.clicks_count), 2)
    ELSE 0 
  END as cpc,
  CASE WHEN f.spend_amount > 0 
    THEN ROUND((f.revenue_amount / f.spend_amount), 2)
    ELSE 0 
  END as roas
FROM fact_media_performance f
JOIN dim_campaign c ON f.campaign_key = c.campaign_key
LEFT JOIN dim_product p ON f.product_key = p.product_key
JOIN dim_time t ON f.time_key = t.time_key;

-- Field ownership lookup
CREATE OR REPLACE VIEW v_field_ownership_map AS
SELECT 
  table_name,
  field_name,
  owner_agent_id,
  ontology_concept_uri,
  validation_rules
FROM cdm_field_ownership
ORDER BY table_name, field_name;

COMMENT ON TABLE dim_product IS 'Product dimension with SCD Type 2 (valid_from/valid_to)';
COMMENT ON TABLE dim_campaign IS 'Campaign dimension with taxonomy links';
COMMENT ON TABLE fact_media_performance IS 'Media performance metrics at campaign×product×audience×day grain';
COMMENT ON TABLE fact_pos_performance IS 'Point-of-sale metrics at store×product×day grain';
COMMENT ON TABLE fact_attribution IS 'Incremental attribution results by KPI';
COMMENT ON TABLE cdm_field_ownership IS 'Maps each CDM field to its owning agent';
COMMENT ON TABLE cdm_cross_table_constraints IS 'Cross-field validation rules enforced by QA agent';

