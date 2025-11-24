-- ===================================================================
-- Retail Analytics Datacube - Sanity Check Queries
-- ===================================================================
-- Run these queries to validate data coherence and coverage
-- ===================================================================

.print '🔍 Running Datacube Sanity Checks...'
.print ''

-- ===================================================================
-- 1. VIEW EXISTENCE AND ROW COUNTS
-- ===================================================================

.print '📊 View Row Counts:'
SELECT 
  'dim_product' as view_name, 
  COUNT(*) as row_count,
  'Dimension' as type
FROM dim_product
UNION ALL
SELECT 'dim_store', COUNT(*), 'Dimension' FROM dim_store
UNION ALL
SELECT 'dim_dc', COUNT(*), 'Dimension' FROM dim_dc
UNION ALL
SELECT 'dim_channel', COUNT(*), 'Dimension' FROM dim_channel
UNION ALL
SELECT 'dim_supplier', COUNT(*), 'Dimension' FROM dim_supplier
UNION ALL
SELECT 'dim_date', COUNT(*), 'Dimension' FROM dim_date
UNION ALL
SELECT 'bridge_dc_store_service', COUNT(*), 'Bridge' FROM bridge_dc_store_service
UNION ALL
SELECT 'bridge_store_catchment', COUNT(*), 'Bridge' FROM bridge_store_catchment
UNION ALL
SELECT 'fact_pos_daily', COUNT(*), 'Fact' FROM fact_pos_daily
UNION ALL
SELECT 'fact_inventory_daily_dc', COUNT(*), 'Fact' FROM fact_inventory_daily_dc
UNION ALL
SELECT 'fact_marketing_daily', COUNT(*), 'Fact' FROM fact_marketing_daily
UNION ALL
SELECT 'fact_merch_daily', COUNT(*), 'Fact' FROM fact_merch_daily
UNION ALL
SELECT 'fact_procurement_po_daily', COUNT(*), 'Fact' FROM fact_procurement_po_daily
UNION ALL
SELECT 'v_retail_daily_store_sku', COUNT(*), 'Unified View' FROM v_retail_daily_store_sku
UNION ALL
SELECT 'v_retail_weekly_store_category', COUNT(*), 'Weekly Rollup' FROM v_retail_weekly_store_category
ORDER BY type, view_name;

.print ''
.print '─────────────────────────────────────────────'
.print ''

-- ===================================================================
-- 2. DATE RANGE COVERAGE
-- ===================================================================

.print '📅 Date Range Coverage:'
SELECT 
  'fact_pos_daily' as table_name,
  MIN(date) as min_date,
  MAX(date) as max_date,
  COUNT(DISTINCT date) as distinct_days,
  DATEDIFF('day', MIN(date), MAX(date)) + 1 as expected_days,
  ROUND(COUNT(DISTINCT date)::DOUBLE / (DATEDIFF('day', MIN(date), MAX(date)) + 1) * 100, 2) || '%' as coverage
FROM fact_pos_daily
UNION ALL
SELECT 
  'fact_inventory_daily_dc',
  MIN(date), MAX(date),
  COUNT(DISTINCT date),
  DATEDIFF('day', MIN(date), MAX(date)) + 1,
  ROUND(COUNT(DISTINCT date)::DOUBLE / (DATEDIFF('day', MIN(date), MAX(date)) + 1) * 100, 2) || '%'
FROM fact_inventory_daily_dc
UNION ALL
SELECT 
  'fact_marketing_daily',
  MIN(date), MAX(date),
  COUNT(DISTINCT date),
  DATEDIFF('day', MIN(date), MAX(date)) + 1,
  ROUND(COUNT(DISTINCT date)::DOUBLE / (DATEDIFF('day', MIN(date), MAX(date)) + 1) * 100, 2) || '%'
FROM fact_marketing_daily
UNION ALL
SELECT 
  'fact_merch_daily',
  MIN(date), MAX(date),
  COUNT(DISTINCT date),
  DATEDIFF('day', MIN(date), MAX(date)) + 1,
  ROUND(COUNT(DISTINCT date)::DOUBLE / (DATEDIFF('day', MIN(date), MAX(date)) + 1) * 100, 2) || '%'
FROM fact_merch_daily;

.print ''
.print '─────────────────────────────────────────────'
.print ''

-- ===================================================================
-- 3. COHERENCE CHECK: Inventory Allocation
-- ===================================================================

.print '🧮 Coherence Check: Inventory Allocation (DC vs Store)'
.print 'DC totals should equal sum of store allocations...'

WITH dc_totals AS (
  SELECT 
    date,
    SUM(on_hand) as dc_on_hand,
    SUM(on_order) as dc_on_order,
    SUM(receipts) as dc_receipts
  FROM fact_inventory_daily_dc
  WHERE date = (SELECT MAX(date) FROM fact_inventory_daily_dc)
  GROUP BY date
),
store_totals AS (
  SELECT
    date,
    SUM(on_hand_alloc) as store_on_hand,
    SUM(on_order_alloc) as store_on_order,
    SUM(receipts_alloc) as store_receipts
  FROM v_inventory_daily_store_alloc
  WHERE date = (SELECT MAX(date) FROM v_inventory_daily_store_alloc)
  GROUP BY date
)
SELECT
  d.date,
  d.dc_on_hand,
  s.store_on_hand,
  ABS(d.dc_on_hand - s.store_on_hand) as on_hand_diff,
  CASE WHEN ABS(d.dc_on_hand - s.store_on_hand) < 1 THEN '✅ PASS' ELSE '❌ FAIL' END as on_hand_check,
  d.dc_on_order,
  s.store_on_order,
  ABS(d.dc_on_order - s.store_on_order) as on_order_diff,
  CASE WHEN ABS(d.dc_on_order - s.store_on_order) < 1 THEN '✅ PASS' ELSE '❌ FAIL' END as on_order_check
FROM dc_totals d
JOIN store_totals s ON s.date = d.date;

.print ''
.print '─────────────────────────────────────────────'
.print ''

-- ===================================================================
-- 4. COVERAGE CHECK: Missing Allocations
-- ===================================================================

.print '🔎 Coverage Check: Stores with POS but no Inventory Allocation'
SELECT COUNT(DISTINCT p.store_id) as stores_missing_inventory
FROM v_pos_daily_conformed p
LEFT JOIN v_inventory_daily_store_alloc i
  ON i.date = p.date AND i.store_id = p.store_id AND i.sku_id = p.sku_id
WHERE i.store_id IS NULL
  AND p.date = (SELECT MAX(date) FROM v_pos_daily_conformed);

.print ''
.print '─────────────────────────────────────────────'
.print ''

-- ===================================================================
-- 5. DATA QUALITY: Null Checks
-- ===================================================================

.print '🛡️ Data Quality: Null Checks in Key Fields'
SELECT 
  'fact_pos_daily' as table_name,
  'date' as field,
  COUNT(*) FILTER (WHERE date IS NULL) as null_count,
  COUNT(*) as total_count,
  ROUND(COUNT(*) FILTER (WHERE date IS NULL)::DOUBLE / COUNT(*) * 100, 2) || '%' as null_pct
FROM fact_pos_daily
UNION ALL
SELECT 'fact_pos_daily', 'store_id', 
  COUNT(*) FILTER (WHERE store_id IS NULL),
  COUNT(*),
  ROUND(COUNT(*) FILTER (WHERE store_id IS NULL)::DOUBLE / COUNT(*) * 100, 2) || '%'
FROM fact_pos_daily
UNION ALL
SELECT 'fact_pos_daily', 'sku_id',
  COUNT(*) FILTER (WHERE sku_id IS NULL),
  COUNT(*),
  ROUND(COUNT(*) FILTER (WHERE sku_id IS NULL)::DOUBLE / COUNT(*) * 100, 2) || '%'
FROM fact_pos_daily
UNION ALL
SELECT 'fact_pos_daily', 'units_sold',
  COUNT(*) FILTER (WHERE units_sold IS NULL),
  COUNT(*),
  ROUND(COUNT(*) FILTER (WHERE units_sold IS NULL)::DOUBLE / COUNT(*) * 100, 2) || '%'
FROM fact_pos_daily
UNION ALL
SELECT 'dim_product', 'product_name',
  COUNT(*) FILTER (WHERE product_name IS NULL),
  COUNT(*),
  ROUND(COUNT(*) FILTER (WHERE product_name IS NULL)::DOUBLE / COUNT(*) * 100, 2) || '%'
FROM dim_product
UNION ALL
SELECT 'dim_store', 'store_name',
  COUNT(*) FILTER (WHERE store_name IS NULL),
  COUNT(*),
  ROUND(COUNT(*) FILTER (WHERE store_name IS NULL)::DOUBLE / COUNT(*) * 100, 2) || '%'
FROM dim_store;

.print ''
.print '─────────────────────────────────────────────'
.print ''

-- ===================================================================
-- 6. REFERENTIAL INTEGRITY: Orphaned Keys
-- ===================================================================

.print '🔗 Referential Integrity: Orphaned Keys'
.print 'Checking for fact records with missing dimension keys...'

-- POS records with missing store_id
SELECT 
  'fact_pos_daily → dim_store' as relationship,
  COUNT(DISTINCT p.store_id) as orphaned_keys
FROM fact_pos_daily p
LEFT JOIN dim_store s ON s.store_id = p.store_id
WHERE s.store_id IS NULL

UNION ALL

-- POS records with missing sku_id
SELECT 
  'fact_pos_daily → dim_product',
  COUNT(DISTINCT p.sku_id)
FROM fact_pos_daily p
LEFT JOIN dim_product dp ON dp.sku_id = p.sku_id
WHERE dp.sku_id IS NULL

UNION ALL

-- Inventory records with missing dc_id
SELECT 
  'fact_inventory_daily_dc → dim_dc',
  COUNT(DISTINCT i.dc_id)
FROM fact_inventory_daily_dc i
LEFT JOIN dim_dc dc ON dc.dc_id = i.dc_id
WHERE dc.dc_id IS NULL;

.print ''
.print '─────────────────────────────────────────────'
.print ''

-- ===================================================================
-- 7. WEEKLY ROLLUP VALIDATION
-- ===================================================================

.print '📊 Weekly Rollup: Sample Data'
SELECT 
  week_start,
  store_id,
  category_id,
  units_sold,
  net_sales,
  on_hand,
  mkt_spend,
  ROUND(roas, 2) as roas,
  ROUND(weeks_of_supply, 1) as weeks_of_supply
FROM v_retail_weekly_store_category
WHERE week_start >= (SELECT MAX(week_start) - INTERVAL '4 weeks' FROM v_retail_weekly_store_category)
ORDER BY week_start DESC, net_sales DESC
LIMIT 10;

.print ''
.print '─────────────────────────────────────────────'
.print ''

-- ===================================================================
-- 8. SUMMARY STATISTICS
-- ===================================================================

.print '📈 Summary Statistics (Latest Week)'
WITH latest_week AS (
  SELECT MAX(week_start) as week FROM v_retail_weekly_store_category
)
SELECT
  COUNT(DISTINCT store_id) as total_stores,
  COUNT(DISTINCT category_id) as total_categories,
  SUM(units_sold) as total_units,
  ROUND(SUM(net_sales), 2) as total_sales,
  ROUND(SUM(mkt_spend), 2) as total_mkt_spend,
  ROUND(SUM(net_sales) / NULLIF(SUM(mkt_spend), 0), 2) as overall_roas,
  ROUND(AVG(weeks_of_supply), 1) as avg_weeks_supply
FROM v_retail_weekly_store_category
WHERE week_start = (SELECT week FROM latest_week);

.print ''
.print '✅ Sanity checks complete!'
.print ''

