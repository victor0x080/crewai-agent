#!/bin/bash
# ===================================================================
# Cube.dev Setup Script
# ===================================================================
# This script sets up Cube.dev with DuckDB backend

set -e

echo "📦 Setting up Cube.dev..."

# Navigate to cube directory
cd "$(dirname "$0")/../cube"

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js not found. Please install: https://nodejs.org/"
    exit 1
fi

echo "✅ Node.js found: $(node --version)"

# Check if DuckDB database exists
if [ ! -f "../duckdb/retail.duckdb" ]; then
    echo "❌ DuckDB database not found. Please run: ../scripts/setup-duckdb.sh"
    exit 1
fi

echo "✅ DuckDB database found"

# Install dependencies
echo "📥 Installing dependencies..."
npm install

# Create .env.local if it doesn't exist
if [ ! -f ".env.local" ]; then
    echo "📝 Creating .env.local from .env.example..."
    cp .env.example .env.local
    echo "⚠️  Please edit .env.local and set your CUBEJS_API_SECRET"
fi

echo "✅ Dependencies installed"

# Validate schema files
echo "🔍 Validating schema files..."
SCHEMA_FILES=(
    "schema/retail_pos.js"
    "schema/retail_inventory.js"
    "schema/retail_marketing.js"
    "schema/retail_merch.js"
    "schema/retail_procurement.js"
    "schema/retail_weekly_joined.js"
    "schema/store.js"
    "schema/product.js"
    "schema/supplier.js"
    "schema/date_dim.js"
)

for file in "${SCHEMA_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file missing"
        exit 1
    fi
done

echo "✅ All schema files present"
echo ""
echo "🎉 Cube.dev setup complete!"
echo ""
echo "To start Cube.dev:"
echo "  cd $(pwd)"
echo "  npm run dev"
echo ""
echo "Then visit:"
echo "  http://localhost:4000 - Developer Playground"
echo ""
echo "API endpoints:"
echo "  REST: http://localhost:4000/cubejs-api/v1"
echo "  GraphQL: http://localhost:4000/cubejs-api/graphql"
echo ""
echo "Example query:"
echo "  curl http://localhost:4000/cubejs-api/v1/load \\"
echo "    -H 'Authorization: your-api-secret' \\"
echo "    -d '{ \"query\": { \"measures\": [\"RetailPosDaily.unitsSold\"], \"timeDimensions\": [{ \"dimension\": \"RetailPosDaily.date\", \"granularity\": \"week\" }] } }'"

