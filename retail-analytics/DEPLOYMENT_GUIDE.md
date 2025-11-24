# Retail Analytics Datacube - Deployment Guide

## Quick Deploy (5 Minutes)

### Prerequisites

- **DuckDB** >= 0.9.0 ([Install](https://duckdb.org/docs/installation/))
- **Node.js** >= 16.0.0 ([Install](https://nodejs.org/))
- **Parquet data files** in `retail-analytics/data/` or S3

### Step-by-Step Deployment

#### 1. Deploy DuckDB Database (2 min)

```bash
cd retail-analytics/scripts
chmod +x setup-duckdb.sh setup-cube.sh
./setup-duckdb.sh
```

**Expected Output:**
```
🦆 Setting up DuckDB Retail Analytics Datacube...
✅ DuckDB found
📊 Creating database and views...
✅ Database created: retail.duckdb
🔍 Running sanity checks...
✅ Sanity checks complete
```

#### 2. Deploy Cube.dev API (2 min)

```bash
./setup-cube.sh
```

**Expected Output:**
```
📦 Setting up Cube.dev...
✅ Node.js found: v18.x.x
✅ DuckDB database found
📥 Installing dependencies...
✅ Dependencies installed
✅ All schema files present
```

#### 3. Configure Environment (30 sec)

```bash
cd ../cube
cp .env.example .env.local
nano .env.local  # Set CUBEJS_API_SECRET
```

#### 4. Start Cube.dev Server (10 sec)

```bash
npm run dev
```

**Expected Output:**
```
🚀 Cube.js server is listening on http://localhost:4000
```

#### 5. Verify Deployment (30 sec)

Open browser: **http://localhost:4000**

Run test query in Playground:
```json
{
  "measures": ["RetailWeeklyStoreCategory.unitsSold"],
  "timeDimensions": [{
    "dimension": "RetailWeeklyStoreCategory.week",
    "granularity": "week",
    "dateRange": "last 4 weeks"
  }]
}
```

---

## Production Deployment

### Architecture Options

#### Option A: Single-Server Deployment

```
┌─────────────────┐
│   Application   │
│     Server      │
├─────────────────┤
│   Cube.dev API  │ :4000
│   DuckDB File   │
└─────────────────┘
```

**Best for:** < 10M rows/day, < 100 concurrent agents

**Setup:**
- Deploy both DuckDB and Cube.dev on same server
- Use local DuckDB file
- Pre-aggregations in DuckDB

#### Option B: Distributed Deployment

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Cube.dev API │────▶│   DuckDB     │────▶│  S3 Parquet  │
│  (Cluster)   │     │  (MotherDuck │     │    Files     │
└──────────────┘     │  or Server)  │     └──────────────┘
                     └──────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │  Postgres    │
                     │ Pre-aggs DB  │
                     └──────────────┘
```

**Best for:** > 10M rows/day, > 100 concurrent agents, multi-region

**Setup:**
- DuckDB reads from S3 (httpfs extension)
- Cube.dev cluster with Redis queue
- Pre-aggregations in PostgreSQL
- Load balancer for Cube.dev API

---

## Configuration Details

### DuckDB Configuration

**For Local Files:**
```sql
-- duckdb/build.sql
CREATE VIEW fact_pos_daily AS
SELECT * FROM read_parquet('../data/fact_pos_daily/*.parquet');
```

**For S3:**
```sql
INSTALL httpfs; LOAD httpfs;
SET s3_access_key_id='YOUR_KEY';
SET s3_secret_access_key='YOUR_SECRET';
SET s3_region='us-east-1';

CREATE VIEW fact_pos_daily AS
SELECT * FROM read_parquet('s3://your-bucket/fact_pos_daily/*.parquet');
```

**For MotherDuck (Cloud DuckDB):**
```bash
# .env.local
CUBEJS_DB_DUCKDB_DB='md:retail_analytics?motherduck_token=YOUR_TOKEN'
```

### Cube.dev Configuration

**Basic (.env.local):**
```bash
CUBEJS_DB_TYPE=duckdb
CUBEJS_DB_DUCKDB_DB=../duckdb/retail.duckdb
CUBEJS_API_SECRET=your-secret-key-change-me
CUBEJS_DEV_MODE=false
```

**Production (.env.local):**
```bash
# Database
CUBEJS_DB_TYPE=duckdb
CUBEJS_DB_DUCKDB_DB=../duckdb/retail.duckdb

# Security
CUBEJS_API_SECRET=your-production-secret-key-256-bits
CUBEJS_DEV_MODE=false

# Redis for queue/cache
CUBEJS_REDIS_URL=redis://localhost:6379

# Pre-aggregations in external DB
CUBEJS_EXT_DB_TYPE=postgres
CUBEJS_EXT_DB_HOST=postgres.example.com
CUBEJS_EXT_DB_PORT=5432
CUBEJS_EXT_DB_NAME=cube_pre_aggs
CUBEJS_EXT_DB_USER=cube
CUBEJS_EXT_DB_PASS=secure_password

# Performance
CUBEJS_CONCURRENCY=8
CUBEJS_SCHEDULED_REFRESH_TIMER=30

# Logging
CUBEJS_LOG_LEVEL=warn
```

---

## Integration with Quest Agent Forge

### TypeScript Integration

**Add to server.ts:**
```typescript
import { retailDatacube } from './services/datacube/RetailDatacubeService';

// Initialize datacube service
const datacube = new RetailDatacubeService(
  process.env.CUBE_API_URL || 'http://localhost:4000',
  process.env.CUBEJS_API_SECRET
);

// Make available to agents
app.locals.datacube = datacube;
```

**Use in agents:**
```typescript
const insights = await retailDatacube.getCrossDomainInsights({
  storeId: 101,
  dateRange: 'last 4 weeks'
});
```

### Python Integration

**Update agent tools:**
```python
from tools.datacube_tools import DATACUBE_TOOLS

agent = Agent(
    role='Retail Analyst',
    goal='Analyze performance',
    tools=[...DATACUBE_TOOLS, ...other_tools]
)
```

**Environment variables:**
```bash
# Add to .env
export CUBE_API_URL=http://localhost:4000
export CUBEJS_API_SECRET=your-secret-key
```

---

## Monitoring & Maintenance

### Health Checks

**DuckDB:**
```bash
duckdb retail.duckdb < sanity_checks.sql
```

**Cube.dev:**
```bash
curl http://localhost:4000/readyz
curl http://localhost:4000/livez
```

### Refresh Schedule

**Pre-Aggregations:**
- Weekly rollups: Refresh daily at 2am
- Daily views: Refresh every 6 hours
- Hot paths: Refresh every 1 hour

**Data Updates:**
```bash
# Incremental data load
duckdb retail.duckdb <<SQL
-- Refresh views to pick up new parquet files
-- DuckDB auto-detects new files in glob patterns
SELECT COUNT(*) FROM fact_pos_daily;  -- This triggers refresh
SQL
```

### Performance Tuning

**1. Materialize Heavy Views:**
```sql
CREATE TABLE mat_retail_weekly AS
SELECT * FROM v_retail_weekly_store_category;

-- Update Cube schema
-- sql: `SELECT * FROM mat_retail_weekly`
```

**2. Partition Parquet Files:**
```
data/fact_pos_daily/
  ├── date=2025-01-01/region=1/*.parquet
  ├── date=2025-01-02/region=1/*.parquet
```

**3. Enable Pre-Aggregations:**
```javascript
// Already configured in cube schemas
preAggregations: {
  main: {
    type: 'rollup',
    measureReferences: [...],
    timeDimensionReference: date,
    granularity: 'week'
  }
}
```

---

## Troubleshooting

### Issue: "Cannot read parquet files"

**Solution:**
```bash
# Check file permissions
ls -la retail-analytics/data/fact_pos_daily/

# Test in DuckDB
duckdb retail.duckdb
> SELECT COUNT(*) FROM read_parquet('../data/fact_pos_daily/*.parquet');
```

### Issue: "Cube.dev connection refused"

**Solution:**
```bash
# Check if server is running
curl http://localhost:4000/readyz

# Check logs
cd retail-analytics/cube
npm run dev

# Verify .env.local
cat .env.local
```

### Issue: "Slow query performance"

**Solution:**
```bash
# Check if pre-aggregations are building
curl http://localhost:4000/cubejs-api/v1/pre-aggregations \
  -H "Authorization: your-secret"

# Force pre-aggregation build
curl http://localhost:4000/cubejs-api/v1/pre-aggregations/jobs \
  -H "Authorization: your-secret" \
  -d '{"action": "post", "selector": {}}'
```

### Issue: "Coherence check fails"

**Solution:**
```bash
# Run full sanity checks
cd retail-analytics/duckdb
duckdb retail.duckdb < sanity_checks.sql

# Check bridge table shares sum to 1.0
duckdb retail.duckdb <<SQL
SELECT dc_id, SUM(service_share) as total_share
FROM bridge_dc_store_service
GROUP BY dc_id
HAVING ABS(SUM(service_share) - 1.0) > 0.01;
SQL
```

---

## Scaling Guidelines

| Metric | Single-Server | Distributed |
|--------|---------------|-------------|
| **Data Volume** | < 1GB/day | > 1GB/day |
| **Query Load** | < 100 qps | > 100 qps |
| **Concurrent Agents** | < 50 | > 50 |
| **Freshness SLA** | 1 hour | < 5 min |
| **Pre-agg Storage** | Local DuckDB | PostgreSQL |
| **Data Source** | Local files | S3/GCS |

---

## Security Checklist

- [ ] Change default `CUBEJS_API_SECRET`
- [ ] Disable `CUBEJS_DEV_MODE` in production
- [ ] Enable HTTPS/TLS for API
- [ ] Restrict network access (firewall rules)
- [ ] Use IAM roles for S3 (no hardcoded keys)
- [ ] Enable Cube.dev JWT authentication
- [ ] Audit log all queries
- [ ] Set up monitoring alerts

---

## Backup & Recovery

**Backup DuckDB Database:**
```bash
# Full backup
cp retail.duckdb retail.duckdb.backup

# Or export to parquet
duckdb retail.duckdb <<SQL
COPY (SELECT * FROM v_retail_weekly_store_category) 
TO 'backup/weekly_rollup.parquet' (FORMAT PARQUET);
SQL
```

**Restore:**
```bash
cp retail.duckdb.backup retail.duckdb
# Or rebuild from source parquet files
./scripts/setup-duckdb.sh
```

---

## Success Metrics

After deployment, verify:

✅ **Availability:** API responds with < 100ms latency  
✅ **Coherence:** Store allocations sum to DC totals (< 0.1% variance)  
✅ **Coverage:** All stores have POS + inventory data  
✅ **Performance:** Pre-aggregated queries return in < 1 second  
✅ **Freshness:** Data updated within SLA (daily or hourly)  
✅ **Agent Integration:** CrewAI agents can query successfully  

---

## Next Steps

1. **Load Production Data:** Replace sample parquet files
2. **Configure Refresh:** Set up scheduled pre-aggregation builds
3. **Integrate Agents:** Add datacube tools to existing agents
4. **Monitor Usage:** Track query patterns and optimize hot paths
5. **Add Custom Metrics:** Extend Cube schemas with business-specific KPIs

---

For support, refer to:
- README.md (usage guide)
- duckdb/build.sql (view definitions)
- cube/schema/*.js (metric definitions)
- scripts/sanity_checks.sql (validation queries)

