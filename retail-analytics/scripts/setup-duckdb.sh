#!/bin/bash
# ===================================================================
# DuckDB Datacube Setup Script
# ===================================================================
# This script creates the DuckDB database and all views

set -e

echo "🦆 Setting up DuckDB Retail Analytics Datacube..."

# Navigate to duckdb directory
cd "$(dirname "$0")/../duckdb"

# Check if DuckDB is installed
if ! command -v duckdb &> /dev/null; then
    echo "❌ DuckDB not found. Please install: https://duckdb.org/docs/installation/"
    exit 1
fi

echo "✅ DuckDB found"

# Create database and run build script
echo "📊 Creating database and views..."
duckdb retail.duckdb < build.sql

echo "✅ Database created: retail.duckdb"

# Run sanity checks
echo "🔍 Running sanity checks..."
duckdb retail.duckdb <<SQL
-- Check view counts
SELECT 'dim_product' as view_name, COUNT(*) as row_count FROM dim_product
UNION ALL
SELECT 'dim_store', COUNT(*) FROM dim_store
UNION ALL
SELECT 'dim_dc', COUNT(*) FROM dim_dc
UNION ALL
SELECT 'fact_pos_daily', COUNT(*) FROM fact_pos_daily
UNION ALL
SELECT 'v_retail_weekly_store_category', COUNT(*) FROM v_retail_weekly_store_category;

-- Check date range
SELECT 
  MIN(date) as min_date, 
  MAX(date) as max_date,
  COUNT(DISTINCT date) as distinct_days
FROM fact_pos_daily;
SQL

echo "✅ Sanity checks complete"
echo ""
echo "🎉 DuckDB setup complete!"
echo "   Database: $(pwd)/retail.duckdb"
echo ""
echo "Next steps:"
echo "1. Verify data files exist in ../data/"
echo "2. Run: duckdb retail.duckdb to explore"
echo "3. Set up Cube.dev: cd ../cube && ./setup-cube.sh"

