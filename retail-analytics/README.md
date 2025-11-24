# Retail Analytics Datacube

**Complete multi-domain retail analytics system with DuckDB + Cube.dev for agent execution.**

## 📊 Overview

This datacube provides **coherent, unified retail metrics** across 5 core domains:

1. **POS (Point of Sale)** - Sales, units, returns, discounts
2. **Inventory** - On hand, on order, receipts (DC → Store allocation)
3. **Marketing** - Spend, impressions, clicks, ROAS (Catchment → Store allocation)
4. **Merchandising** - Facings, promotions, assortment
5. **Procurement** - Inbound POs, costs, lead times (DC → Store allocation)

### Key Features

✅ **Coherent Allocations** - DC and catchment metrics correctly allocated to stores  
✅ **Weekly Rollups** - Pre-aggregated store×category metrics for fast queries  
✅ **Cross-Domain KPIs** - ROAS, weeks of supply, stockout risk, inventory turnover  
✅ **Agent-Ready API** - REST/GraphQL endpoints + Python/TypeScript SDKs  
✅ **Pre-Aggregations** - Cube.dev rollups for sub-second query performance  
✅ **Anomaly Detection** - Built-in segments for stockout risk, overstock, low ROAS  

---

## 🗂️ Project Structure

```
retail-analytics/
├── data/                          # Parquet data files (or S3 URIs)
│   ├── dim_product/*.parquet
│   ├── dim_store/*.parquet
│   ├── dim_dc/*.parquet
│   ├── dim_channel/*.parquet
│   ├── dim_supplier/*.parquet
│   ├── dim_date/*.parquet
│   ├── bridge_dc_store_service/*.parquet
│   ├── bridge_store_catchment/*.parquet
│   ├── fact_pos_daily/*.parquet
│   ├── fact_inventory_daily_dc/*.parquet
│   ├── fact_marketing_daily/*.parquet
│   ├── fact_merch_daily/*.parquet
│   └── fact_procurement_*.parquet
│
├── duckdb/
│   ├── retail.duckdb             # DuckDB database (created)
│   └── build.sql                 # All views and allocations
│
├── cube/
│   ├── schema/                   # Cube.dev schema definitions
│   │   ├── retail_pos.js
│   │   ├── retail_inventory.js
│   │   ├── retail_marketing.js
│   │   ├── retail_merch.js
│   │   ├── retail_procurement.js
│   │   ├── retail_weekly_joined.js
│   │   ├── store.js
│   │   ├── product.js
│   │   ├── supplier.js
│   │   └── date_dim.js
│   ├── cube.js                   # Cube.dev configuration
│   ├── .env.example              # Environment template
│   └── package.json
│
└── scripts/
    ├── setup-duckdb.sh           # DuckDB deployment
    └── setup-cube.sh             # Cube.dev deployment
```

---

## 🚀 Quick Start

### 1. Setup DuckDB

```bash
cd retail-analytics/scripts
chmod +x setup-duckdb.sh
./setup-duckdb.sh
```

This creates `retail.duckdb` with all dimension, fact, and allocation views.

### 2. Setup Cube.dev

```bash
cd retail-analytics/scripts
chmod +x setup-cube.sh
./setup-cube.sh
```

This installs dependencies and configures Cube.dev to use DuckDB.

### 3. Configure Environment

```bash
cd retail-analytics/cube
cp .env.example .env.local
# Edit .env.local and set CUBEJS_API_SECRET
```

### 4. Start Cube.dev

```bash
cd retail-analytics/cube
npm run dev
```

Visit **http://localhost:4000** for the Developer Playground.

---

## 📡 API Usage

### REST API

```bash
curl http://localhost:4000/cubejs-api/v1/load \
  -H 'Authorization: your-api-secret' \
  -H 'Content-Type: application/json' \
  -d '{
    "query": {
      "measures": ["RetailWeeklyStoreCategory.unitsSold", "RetailWeeklyStoreCategory.netSales"],
      "timeDimensions": [{
        "dimension": "RetailWeeklyStoreCategory.week",
        "granularity": "week",
        "dateRange": "last 12 weeks"
      }],
      "dimensions": ["RetailWeeklyStoreCategory.categoryId"]
    }
  }'
```

### TypeScript SDK

```typescript
import { retailDatacube } from '@/services/datacube/RetailDatacubeService';

// Get POS metrics
const sales = await retailDatacube.getPOSMetrics({
  timeGranularity: 'week',
  dateRange: 'last 12 weeks',
  regionId: 5
});

// Get cross-domain insights
const insights = await retailDatacube.getCrossDomainInsights({
  storeId: 101,
  dateRange: 'last 4 weeks'
});

// Detect anomalies
const anomalies = await retailDatacube.detectAnomalies({
  regionId: 5
});
```

### Python SDK (CrewAI Agents)

```python
from tools.datacube_tools import (
    get_pos_metrics,
    get_inventory_metrics,
    get_cross_domain_insights,
    detect_anomalies
)

# Use in CrewAI agent
agent = Agent(
    role='Retail Analytics Specialist',
    goal='Analyze sales and inventory trends',
    backstory='Expert in retail operations',
    tools=[
        get_pos_metrics,
        get_inventory_metrics,
        get_cross_domain_insights,
        detect_anomalies
    ]
)

# Query from tool
results = get_pos_metrics(
    time_granularity='week',
    date_range='last 12 weeks',
    region_id=5
)
```

---

## 📈 Key Views and Metrics

### Daily Views (Store×SKU Grain)

- `v_retail_daily_store_sku` - Unified daily metrics across all domains

### Weekly Views (Store×Category Grain)

- `v_retail_weekly_store_category` - Pre-aggregated weekly rollup

### Allocation Views

- `v_inventory_daily_store_alloc` - DC → Store inventory allocation
- `v_marketing_daily_store_alloc` - Catchment → Store marketing allocation
- `v_procurement_daily_store_alloc` - DC → Store PO allocation

### Key Measures

**POS:**
- `unitsSold`, `netSales`, `returnsUnits`, `discounts`, `avgUnitPrice`, `returnRate`

**Inventory:**
- `onHand`, `onOrder`, `receipts`, `daysOfSupply`, `stockoutRisk`

**Marketing:**
- `spend`, `impressions`, `clicks`, `attrOrders`, `roas`, `ctr`, `cpc`, `cpo`

**Merchandising:**
- `facingsAvg`, `promoRate`, `inAssortmentRate`, `avgPromoDepth`, `productivityPerFacing`

**Procurement:**
- `poQtyInbound`, `avgUnitCost`, `avgLeadTimeDays`, `coverageDays`, `inventoryTurnover`

**Cross-Domain:**
- `weeksOfSupply`, `roas`, `stockoutRisk`, `supplyChainHealth`

---

## 🎯 Use Cases

### 1. Weekly Performance Review

```typescript
const performance = await retailDatacube.getWeeklyMetrics({
  measures: ['unitsSold', 'netSales', 'roas', 'weeksOfSupply'],
  regionId: 5,
  dateRange: 'last 12 weeks'
});
```

### 2. Stockout Risk Analysis

```typescript
const atRisk = await retailDatacube.queryMetrics({
  cube: 'weekly',
  measures: ['unitsSold', 'onHand', 'poQtyInbound', 'stockoutRisk'],
  filters: [
    { field: 'stockoutRisk', operator: 'gt', values: [0] }
  ],
  dateRange: 'last 2 weeks'
});
```

### 3. Marketing ROAS Optimization

```typescript
const campaigns = await retailDatacube.getMarketingMetrics({
  measures: ['spend', 'attrOrders', 'roas', 'cpo'],
  dateRange: 'last 4 weeks'
});

// Find low-performing campaigns (ROAS < 2x)
const lowROAS = campaigns.filter(c => c['RetailMarketingDaily.roas'] < 2);
```

### 4. Promotional Lift Analysis

```typescript
const promoWeeks = await retailDatacube.queryMetrics({
  cube: 'weekly',
  measures: ['unitsSold', 'avgPromoDepth', 'promoLift'],
  filters: [
    { field: 'avgPromoDepth', operator: 'gt', values: [0.10] }
  ],
  dateRange: 'last 12 weeks'
});
```

### 5. Supply Chain Health

```typescript
const health = await retailDatacube.queryMetrics({
  cube: 'weekly',
  measures: ['weeksOfSupply', 'supplyChainHealth', 'avgLeadTimeDays'],
  dimensions: ['categoryId'],
  dateRange: 'last 4 weeks'
});
```

---

## 🔍 Sanity Checks

### Coherence Check: Inventory Allocation

```sql
-- Store allocations should sum to DC totals
SELECT SUM(on_hand_alloc) FROM v_inventory_daily_store_alloc WHERE date='2025-07-01';
SELECT SUM(on_hand) FROM fact_inventory_daily_dc WHERE date='2025-07-01';
-- These should match!
```

### Coverage Check: Missing Allocations

```sql
-- Any stores with POS but no inventory allocation?
SELECT DISTINCT p.store_id
FROM v_pos_daily_conformed p
LEFT JOIN v_inventory_daily_store_alloc i
  ON i.date=p.date AND i.store_id=p.store_id AND i.sku_id=p.sku_id
WHERE i.store_id IS NULL
LIMIT 20;
```

### Date Range Check

```sql
SELECT 
  MIN(date) as min_date, 
  MAX(date) as max_date,
  COUNT(DISTINCT date) as distinct_days
FROM fact_pos_daily;
```

---

## ⚡ Performance Optimization

### 1. Partition Parquet Files

```bash
# Partition by date and/or region
data/
  └── fact_pos_daily/
      ├── date=2025-01-01/
      │   └── region=1/*.parquet
      ├── date=2025-01-02/
      │   └── region=1/*.parquet
```

### 2. Materialize Heavy Views

```sql
-- Create materialized table for frequent queries
CREATE TABLE mat_retail_weekly_store_category AS
SELECT * FROM v_retail_weekly_store_category;

-- Update Cube schema to point to materialized table
-- sql: `SELECT * FROM mat_retail_weekly_store_category`
```

### 3. Configure Pre-Aggregations

Pre-aggregations are already configured in Cube schemas with:
- Weekly granularity for time-series
- Store×Category grain for dimensional slicing
- Incremental refresh with 4-week update window

### 4. Use Integer Keys

All dimension keys are `INTEGER` for optimal join performance.

---

## 🧪 Testing

### Test DuckDB Views

```bash
cd retail-analytics/duckdb
duckdb retail.duckdb

-- Check view row counts
SELECT 'fact_pos_daily' as view, COUNT(*) FROM fact_pos_daily
UNION ALL
SELECT 'v_retail_weekly_store_category', COUNT(*) FROM v_retail_weekly_store_category;

-- Spot check data
SELECT * FROM v_retail_weekly_store_category LIMIT 10;
```

### Test Cube.dev API

```bash
# Start Cube.dev
cd retail-analytics/cube
npm run dev

# Test query in another terminal
curl http://localhost:4000/cubejs-api/v1/load \
  -H 'Authorization: secret' \
  -d '{"query":{"measures":["RetailPosDaily.unitsSold"],"limit":10}}'
```

---

## 🔧 Agent Integration

### TypeScript Agents

```typescript
import { retailDatacube } from '@/services/datacube/RetailDatacubeService';

// In your agent execution logic
const data = await retailDatacube.getCrossDomainInsights({
  storeId: agentContext.storeId,
  dateRange: 'last 4 weeks'
});
```

### CrewAI Python Agents

```python
from crewai import Agent
from tools.datacube_tools import DATACUBE_TOOLS

analyst_agent = Agent(
    role='Retail Performance Analyst',
    goal='Identify sales trends and inventory risks',
    backstory='Expert in retail analytics with 10+ years experience',
    tools=DATACUBE_TOOLS,
    verbose=True,
    allow_delegation=False
)
```

---

## 📚 Data Model

### Grain Hierarchy

```
Daily (Store × SKU)
    ↓
Weekly (Store × Category)
    ↓
Monthly (Region × Department)
```

### Fact Tables

- `fact_pos_daily` - Daily sales transactions
- `fact_inventory_daily_dc` - DC inventory snapshots
- `fact_marketing_daily` - Marketing spend and performance
- `fact_merch_daily` - Merchandising execution
- `fact_procurement_po_daily` - Purchase orders

### Dimension Tables

- `dim_product` - Product hierarchy (SKU → Product → Category → Department)
- `dim_store` - Store attributes (Store → Region → Catchment)
- `dim_dc` - Distribution centers
- `dim_supplier` - Supplier information
- `dim_date` - Date/calendar attributes

### Bridge Tables

- `bridge_dc_store_service` - DC to Store allocation (service_share)
- `bridge_store_catchment` - Store to Catchment allocation (catchment_share)

---

## 🌐 S3/Cloud Data

To use S3 data sources:

1. **Update DuckDB build.sql:**
```sql
INSTALL httpfs; LOAD httpfs;
SET s3_access_key_id='YOUR_KEY';
SET s3_secret_access_key='YOUR_SECRET';
SET s3_region='us-east-1';

-- Change file paths to S3 URIs
CREATE OR REPLACE VIEW fact_pos_daily AS
SELECT * FROM read_parquet('s3://your-bucket/fact_pos_daily/*.parquet');
```

2. **Update Cube.dev .env.local:**
```bash
CUBEJS_DB_DUCKDB_S3_ACCESS_KEY_ID=your_key
CUBEJS_DB_DUCKDB_S3_SECRET_ACCESS_KEY=your_secret
CUBEJS_DB_DUCKDB_S3_REGION=us-east-1
```

---

## 📖 Additional Resources

- **DuckDB Docs:** https://duckdb.org/docs/
- **Cube.dev Docs:** https://cube.dev/docs/
- **Cube.dev Data Schema:** https://cube.dev/docs/schema/fundamentals/

---

## ✅ Deployment Checklist

- [ ] Parquet data files in `data/` or S3
- [ ] DuckDB database created (`./scripts/setup-duckdb.sh`)
- [ ] Cube.dev dependencies installed (`./scripts/setup-cube.sh`)
- [ ] `.env.local` configured with API secret
- [ ] Cube.dev server running (`npm run dev`)
- [ ] API accessible at `http://localhost:4000`
- [ ] Agent SDK integrated in your codebase
- [ ] Sanity checks passing

---

## 🎉 You're Ready!

Your retail analytics datacube is now ready for agent execution. Agents can query coherent, multi-domain metrics via a unified API.

**Key Benefit:** Store-level metrics are **mathematically coherent** — store allocations always sum to DC/region totals.

For questions or issues, refer to the inline documentation in:
- `duckdb/build.sql` (view definitions)
- `cube/schema/*.js` (measure/dimension definitions)
- `src/services/datacube/RetailDatacubeService.ts` (TypeScript SDK)
- `src/agents/crewai_python/tools/datacube_tools.py` (Python SDK)

