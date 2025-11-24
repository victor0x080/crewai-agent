-- ===================================================================
-- Manufacturer RMN Datacube - DuckDB Build Script
-- ===================================================================
-- This script creates all views for the Manufacturer RMN datacube
-- based on the canonical manufacturer-rmn-model schema v2.1.0
-- ===================================================================

PRAGMA threads=8;

-- Optional: Uncomment if reading from S3/GCS
-- INSTALL httpfs; LOAD httpfs;
-- SET s3_access_key_id='YOUR_KEY'; 
-- SET s3_secret_access_key='YOUR_SECRET'; 
-- SET s3_region='us-east-1';

-- ===================================================================
-- DIMENSION VIEWS
-- ===================================================================

-- Manufacturer Dimension
CREATE OR REPLACE VIEW dim_manufacturer AS
SELECT
  manufacturer_id,
  manufacturer_name,
  manufacturer_code,
  region,
  status,
  valid_from,
  valid_to,
  is_current
FROM read_parquet('../data/manufacturer/*.parquet')
WHERE is_current = true;

-- Channel/RMN Dimension
CREATE OR REPLACE VIEW dim_channel_rmn AS
SELECT
  channel_id,
  channel_name,
  channel_type,
  external_platform,
  platform_version,
  platform_status,
  attribution_default_window_days,
  attribution_default_model
FROM read_parquet('../data/channel_rmn/*.parquet')
WHERE is_current = true;

-- Campaign Dimension
CREATE OR REPLACE VIEW dim_campaign AS
SELECT
  campaign_id,
  manufacturer_id,
  channel_id,
  campaign_name,
  parent_campaign_id,
  objective,
  start_date::DATE as start_date,
  end_date::DATE as end_date,
  budget_total,
  budget_currency,
  campaign_status
FROM read_parquet('../data/campaign/*.parquet');

-- Ad Group Dimension
CREATE OR REPLACE VIEW dim_ad_group AS
SELECT
  ad_group_id,
  campaign_id,
  ad_group_name,
  placement_type,
  targeting_criteria,
  bid_strategy,
  daily_budget,
  ad_group_status
FROM read_parquet('../data/ad_group/*.parquet');

-- NEW: Audience Segment Dimension
CREATE OR REPLACE VIEW dim_audience_segment AS
SELECT
  audience_segment_id,
  manufacturer_id,
  channel_id,
  segment_name,
  platform_segment_id,
  segment_type,
  segment_category,
  parent_segment_id,
  size_estimate,
  cpm_modifier,
  match_rate,
  segment_status
FROM read_parquet('../data/audience_segment/*.parquet')
WHERE is_current = true;

-- NEW: Search Term Dimension
CREATE OR REPLACE VIEW dim_search_term AS
SELECT
  search_term_id,
  ad_group_id,
  keyword_text,
  keyword_text_normalized,
  match_type,
  bid_amount,
  quality_score,
  search_volume_estimate,
  keyword_category,
  is_negative_keyword,
  keyword_status
FROM read_parquet('../data/search_term/*.parquet')
WHERE is_current = true;

-- NEW: Promotion Dimension
CREATE OR REPLACE VIEW dim_promotion AS
SELECT
  promotion_id,
  manufacturer_id,
  sku_id_canonical,
  channel_id,
  geography_id,
  promotion_name,
  promotion_type,
  discount_amount,
  discount_percentage,
  minimum_purchase_quantity,
  valid_from::DATE as valid_from,
  valid_to::DATE as valid_to,
  redemption_channel,
  total_budget,
  promotion_status,
  coordinated_campaign_id
FROM read_parquet('../data/promotion/*.parquet');

-- Date Dimension (for time-based queries)
CREATE OR REPLACE VIEW dim_date AS
SELECT
  date::DATE, 
  week_start::DATE, 
  month_start::DATE,
  quarter_start::DATE, 
  year::INTEGER,
  fiscal_week::VARCHAR, 
  fiscal_period::VARCHAR
FROM read_parquet('../data/dim_date/*.parquet');

-- ===================================================================
-- FACT VIEWS
-- ===================================================================

-- Main RMN Performance Fact Table
CREATE OR REPLACE VIEW rmn_performance_fact AS
SELECT
  fact_id,
  manufacturer_id,
  sku_id_canonical,
  canonical_customer_id,
  geography_id,
  store_id,
  channel_id,
  campaign_id,
  ad_group_id,
  creative_id,
  audience_segment_id,
  search_term_id,
  promotion_id,
  time_id,
  aggregation_level,
  impressions,
  clicks,
  spend,
  spend_currency,
  attributed_sales,
  click_attributed_sales,
  view_attributed_sales,
  units_sold,
  incremental_units,
  base_units,
  gross_margin,
  roas,
  acos,
  halo_sales,
  promotion_attributed_sales
FROM read_parquet('../data/rmn_performance_fact/*.parquet');

-- ===================================================================
-- NEW ENTITY VIEWS
-- ===================================================================

-- Campaign Pacing
CREATE OR REPLACE VIEW campaign_pacing AS
SELECT
  pacing_id,
  campaign_id,
  snapshot_date::DATE as snapshot_date,
  budget_allocated,
  budget_spent_to_date,
  days_elapsed,
  days_remaining,
  expected_spend_to_date,
  spend_variance,
  spend_variance_percentage,
  projected_end_spend,
  projected_budget_exhaustion_date::DATE as projected_budget_exhaustion_date,
  pacing_status,
  recommended_daily_budget
FROM read_parquet('../data/campaign_pacing/*.parquet');

-- Incrementality Test
CREATE OR REPLACE VIEW incrementality_test AS
SELECT
  test_id,
  manufacturer_id,
  campaign_id,
  channel_id,
  test_name,
  test_type,
  test_hypothesis,
  test_markets,
  control_markets,
  start_date::DATE as start_date,
  end_date::DATE as end_date,
  pre_period_start::DATE as pre_period_start,
  pre_period_end::DATE as pre_period_end,
  test_status,
  statistical_power,
  minimum_detectable_effect,
  results,
  invalidation_reason
FROM read_parquet('../data/incrementality_test/*.parquet');

-- Platform Invoice
CREATE OR REPLACE VIEW platform_invoice AS
SELECT
  invoice_id,
  manufacturer_id,
  channel_id,
  platform_invoice_number,
  billing_period_start::DATE as billing_period_start,
  billing_period_end::DATE as billing_period_end,
  invoice_date::DATE as invoice_date,
  due_date::DATE as due_date,
  invoiced_amount,
  invoiced_currency,
  reported_spend,
  variance,
  variance_percentage,
  reconciliation_status,
  payment_status
FROM read_parquet('../data/platform_invoice/*.parquet');

-- Product Relationship (for halo effects)
CREATE OR REPLACE VIEW product_relationship AS
SELECT
  relationship_id,
  primary_sku_id,
  related_sku_id,
  relationship_type,
  halo_sales_coefficient,
  cross_elasticity,
  relationship_strength
FROM read_parquet('../data/product_relationship/*.parquet')
WHERE is_current = true;
