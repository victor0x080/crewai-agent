# Data Normalization Mechanism - Copy Summary

**Date:** December 2024  
**Source:** `IMS-data-normalization`  
**Destination:** `NEW_CREWAI_AGENT`

---

## Overview

This document summarizes the data normalization mechanism copied from `IMS-data-normalization` to `NEW_CREWAI_AGENT`. The normalization mechanism is a hierarchical multi-agent system that normalizes heterogeneous data from RMNs, manufacturers, and POS systems into a canonical trade desk data model.

---

## Files Copied

### 1. **Python Crew Files**

#### `agents/crewai_python/crews/normalization/DataNormalizationCrew.py`
- **Description:** Main data normalization crew with 10 agents (1 manager + 9 specialists)
- **Key Features:**
  - Hierarchical process with manager delegation
  - 9 specialized worker agents:
    1. Schema Discovery Agent
    2. Metrics & Time Normalization Agent
    3. Product Taxonomy Agent
    4. Campaign Tactic Agent
    5. POS & Promotion Agent
    6. Audience Segment Agent
    7. KPI & Attribution Agent
    8. QA Governance Agent
    9. Orchestrator Agent
  - Redis Streams integration
  - Ontology-aware routing
  - SHACL validation

#### `agents/crewai_python/crews/normalization/contracts.py`
- **Description:** Pydantic models for agent I/O contracts
- **Key Features:**
  - Input/output schemas for each agent
  - Confidence levels and decision statuses
  - Field decision models
  - Error handling structures

### 2. **Tools**

#### `agents/crewai_python/tools/normalization_tools.py`
- **Description:** Reusable normalization tools for agents
- **Key Tools:**
  - `detect_field_type`: Detect semantic type of fields
  - `infer_column_mapping`: Map source columns to CDM fields
  - `normalize_metric`: Normalize metric values with validation
  - `normalize_datetime`: Normalize dates to UTC
  - `normalize_product_id`: Normalize product IDs (ASIN, UPC, etc.)
  - `classify_campaign_tactic`: Classify campaign tactics
  - `extract_promo_attributes`: Extract promotional attributes
  - `parse_audience_definition`: Parse audience segments
  - `extract_kpi_formula`: Extract KPI formulas
  - `validate_data_quality`: Perform data quality checks

### 3. **JavaScript Services**

#### `src/services/data-ingestion/RMNDataNormalizer.js`
- **Description:** RMN data normalizer service (converted from TypeScript)
- **Key Features:**
  - Normalizes campaigns and metrics from multiple RMNs
  - Supported RMNs: Amazon Ads, Walmart Connect, Instacart Ads
  - Status mapping across RMNs
  - Data quality assessment
  - Ontology concept extraction

### 4. **Database Migrations**

#### `src/db/migrations/011_canonical_data_model.sql`
- **Description:** Canonical Data Model (CDM) schema
- **Key Tables:**
  - **Dimensions:** `dim_product`, `dim_campaign`, `dim_audience`, `dim_store`, `dim_time`, `dim_kpi`, `dim_manufacturer`, `dim_retailer`
  - **Facts:** `fact_media_performance`, `fact_pos_performance`, `fact_attribution`
  - **Metadata:** `cdm_field_ownership`, `cdm_schema_versions`, `cdm_schema_changes`, `cdm_cross_table_constraints`
- **Key Features:**
  - Star schema design
  - Field ownership tracking (which agent owns each field)
  - Schema versioning
  - Cross-table constraints
  - Enriched views

#### `src/db/migrations/012_hitl_normalization_queue.sql`
- **Description:** Human-in-the-Loop (HITL) normalization queue
- **Key Tables:**
  - `hitl_normalization_queue`: Review queue for low-confidence decisions
  - `hitl_review_actions`: Action log for reviews
  - `hitl_role_permissions`: RBAC policies
  - `hitl_sla_config`: SLA configuration
- **Key Features:**
  - Complexity scoring and routing
  - PII masking/unmasking with audit trail
  - Auto-assignment based on complexity and role
  - SLA tracking and breach detection
  - Feedback loops to ML training

---

## Architecture

### Data Flow

```
Raw Data Ingestion
    ↓
stream:ingestion:raw-data (Redis Stream)
    ↓
Data Normalization Crew (Listens & Processes)
    ├── Schema Discovery Agent
    ├── Metrics & Time Agent
    ├── Product Taxonomy Agent
    ├── Campaign Tactic Agent
    ├── POS & Promotion Agent
    ├── Audience Segment Agent
    ├── KPI & Attribution Agent
    ├── QA Governance Agent
    └── Orchestrator Agent
    ↓
Normalized Data Published
    ↓
stream:normalized:canonical-data (Redis Stream)
    OR
stream:dlq (Dead Letter Queue for low-confidence)
```

### Agent Responsibilities

| **Agent** | **Responsibility** | **Confidence Target** |
|----------|-------------------|---------------------|
| Schema Discovery | Map raw columns → CDM fields | 70%+ |
| Metrics & Time | Normalize metrics, dates, timezones | 85%+ |
| Product Taxonomy | Normalize product IDs, categories | 75%+ |
| Campaign Tactic | Classify campaign tactics | 70%+ |
| POS & Promotion | Normalize POS transactions, promos | 75%+ |
| Audience Segment | Normalize audience segments | 65%+ |
| KPI & Attribution | Normalize KPI definitions | 60%+ |
| QA Governance | Cross-validate, detect anomalies | 90%+ |
| Orchestrator | Merge outputs, determine sequence | 80%+ |

---

## Key Features

### 1. **Ontology Integration**
- Uses ontology service for concept resolution
- Semantic routing based on ontology concepts
- SHACL validation for policy enforcement

### 2. **Continuous Learning**
- Mapping cache for successful transformations
- Ontology evolution (new concepts discovered)
- ML training from human corrections
- Taxonomy versioning and tracking

### 3. **Human-in-the-Loop**
- Low-confidence cases (< 60%) sent to HITL queue
- Complexity-based routing
- RBAC for reviewer assignment
- PII masking with audit trail
- SLA tracking

### 4. **Data Quality**
- Two-stage validation (JSON Schema + SHACL)
- Cross-field consistency checks
- Anomaly detection
- Data quality scoring

---

## Integration Points

### 1. **CrewAI Manager Service**
- Requires `CrewAIManagerService` for Redis Streams consumption
- Manager config: `data-normalization-manager`
- Route stream: `stream:ingestion:raw-data`

### 2. **Ontology Service**
- Uses `OntologyService` for concept resolution
- Uses `SHACLValidator` for semantic validation
- Uses `ConstraintEnforcer` for business policy enforcement

### 3. **Database**
- Requires PostgreSQL/Supabase
- Run migrations: `011_canonical_data_model.sql` and `012_hitl_normalization_queue.sql`
- Tables must exist before crew can write normalized data

### 4. **Redis Streams**
- Consumes from: `stream:ingestion:raw-data`
- Publishes to: `stream:normalized:canonical-data` or `stream:dlq`
- Consumer group: `normalization`

---

## Next Steps

### 1. **Dependencies**
- Ensure `CrewAIManagerService` is available in Python path
- Install required Python packages: `crewai`, `pydantic`, `redis`, `dateutil`
- Ensure ontology tools are available: `ontology_tools.py`, `shacl_tools.py`

### 2. **Database Setup**
- Run migration `011_canonical_data_model.sql` to create CDM schema
- Run migration `012_hitl_normalization_queue.sql` to create HITL queue
- Populate `dim_time` table with date dimension data

### 3. **Redis Streams Setup**
```bash
redis-cli XGROUP CREATE stream:ingestion:raw-data normalization $ MKSTREAM
redis-cli XGROUP CREATE stream:normalized:canonical-data consumers $ MKSTREAM
redis-cli XGROUP CREATE stream:dlq consumers $ MKSTREAM
```

### 4. **Register Crew**
```bash
curl -X POST http://localhost:3000/api/managers/register \
  -H "Content-Type: application/json" \
  -d '{
    "manager_id": "data-normalization-manager",
    "crew_id": "data-normalization-crew",
    "route_stream": "stream:ingestion:raw-data",
    "produces_streams": ["stream:normalized:canonical-data", "stream:dlq"],
    "capabilities": ["normalization", "schema_mapping", "data_quality"]
  }'
```

### 5. **Start Crew**
```bash
python agents/crewai_python/crews/normalization/DataNormalizationCrew.py
```

---

## Testing

### Test with Sample Data
```bash
# Publish test data to ingestion stream
redis-cli XADD stream:ingestion:raw-data '*' \
  event_id 'test-001' \
  source 'amazon_ads' \
  data '{"campaignId":"CAMP_123","impr":125000,"clicks":3750,"spend":1250.50}'

# Monitor normalized output
redis-cli XREAD COUNT 10 STREAMS stream:normalized:canonical-data 0
```

---

## Documentation References

- **Original Documentation:** `IMS-data-normalization/docs/DATA_NORMALIZATION_CREW_COMPLETE.md`
- **Implementation Summary:** `IMS-data-normalization/docs/DATA_NORMALIZATION_IMPLEMENTATION_SUMMARY.md`

---

## Notes

1. **CrewAIManagerService Dependency:** The crew requires `CrewAIManagerService` to be available. If not found, it will use stubs for testing.

2. **Ontology Tools:** The crew imports `ontology_tools` and `shacl_tools`. Ensure these are available in the Python path.

3. **TypeScript to JavaScript:** `RMNDataNormalizer.ts` was converted to `RMNDataNormalizer.js` with CommonJS exports.

4. **Database Compatibility:** Migrations are PostgreSQL-specific. Adjust for other databases if needed.

5. **Redis Streams:** Ensure Redis is running and streams are created before starting the crew.

---

## Summary

✅ **Copied Files:**
- DataNormalizationCrew.py (main crew)
- contracts.py (agent I/O contracts)
- normalization_tools.py (reusable tools)
- RMNDataNormalizer.js (RMN normalizer service)
- 011_canonical_data_model.sql (CDM schema)
- 012_hitl_normalization_queue.sql (HITL queue)

✅ **Key Features:**
- 10-agent hierarchical system
- Ontology-aware routing
- Continuous learning
- Human-in-the-loop
- Data quality validation

✅ **Ready for:**
- Integration with existing infrastructure
- Testing with sample data
- Production deployment

