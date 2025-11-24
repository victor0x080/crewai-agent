# Data Examples for Migration Schemas

This document provides concrete examples of what data will be stored in each table from the migration files.

---

## 011_canonical_data_model.sql

### Dimension Tables

#### `dim_product` - Product Catalog
**Purpose:** Stores product information with SCD Type 2 (slowly changing dimensions)

**Example Data:**
```json
{
  "product_key": 1001,
  "product_id": "B08XYZ1234",
  "product_id_type": "ASIN",
  "product_title": "Coca-Cola Zero Sugar 12-Pack 12oz Cans",
  "brand": "Coca-Cola",
  "manufacturer": "The Coca-Cola Company",
  "category_uri": "ex:Category/Beverages",
  "subcategory_uri": "ex:Category/SoftDrinks/Cola",
  "pack_size": 12,
  "pack_unit": "cans",
  "unit_price": 6.99,
  "attributes": {
    "flavor": "zero sugar",
    "package_type": "can",
    "size_oz": 12,
    "sugar_content": "0g"
  },
  "valid_from": "2024-01-01",
  "valid_to": null,
  "is_current": true,
  "data_source": "amazon_catalog",
  "created_at": "2024-01-01T10:00:00Z",
  "updated_at": "2024-01-01T10:00:00Z"
}
```

#### `dim_campaign` - Marketing Campaigns
**Purpose:** Stores campaign metadata from various RMN platforms

**Example Data:**
```json
{
  "campaign_key": 2001,
  "campaign_id": "camp_12345",
  "campaign_name": "Summer Refresh - Coca-Cola Zero",
  "rmn_source": "amazon_ads",
  "tactic_uri": "ex:Tactic/SponsoredProduct",
  "ad_format": "search",
  "objective": "conversion",
  "targeting_type": "keyword",
  "funnel_stage": "purchase",
  "daily_budget": 500.00,
  "start_date": "2024-06-01",
  "end_date": "2024-08-31",
  "status": "active",
  "attributes": {
    "bid_strategy": "target_acos",
    "target_acos": 25.0
  },
  "valid_from": "2024-06-01",
  "valid_to": null,
  "is_current": true,
  "data_source": "amazon_ads_api",
  "created_at": "2024-06-01T08:00:00Z",
  "updated_at": "2024-06-01T08:00:00Z"
}
```

#### `dim_audience` - Audience Segments
**Purpose:** Stores audience segment definitions from RMN platforms

**Example Data:**
```json
{
  "audience_key": 3001,
  "audience_id": "aud_health_conscious",
  "audience_name": "Health-Conscious Shoppers",
  "rmn_source": "walmart_connect",
  "lifecycle_stage": "active",
  "value_tier": "high",
  "tenure_days": 365,
  "recency_days": 7,
  "frequency_visits": 12,
  "attributes": {
    "demographics": {
      "age_range": "25-45",
      "income": "high"
    },
    "behaviors": ["organic_shopping", "low_sugar_preference"]
  },
  "valid_from": "2024-01-01",
  "valid_to": null,
  "is_current": true,
  "data_source": "walmart_connect_api",
  "created_at": "2024-01-01T10:00:00Z",
  "updated_at": "2024-01-01T10:00:00Z"
}
```

#### `dim_store` - Store Locations
**Purpose:** Stores physical and online store information

**Example Data:**
```json
{
  "store_key": 4001,
  "store_id": "WMT-1234",
  "store_name": "Walmart Supercenter #1234",
  "retailer": "Walmart",
  "store_format": "superstore",
  "address": "123 Main St",
  "city": "Atlanta",
  "state": "GA",
  "zip_code": "30309",
  "country": "US",
  "geo_lat": 33.7490,
  "geo_lon": -84.3880,
  "open_date": "2010-05-15",
  "close_date": null,
  "is_active": true,
  "attributes": {
    "square_feet": 180000,
    "has_pharmacy": true,
    "has_grocery": true
  },
  "created_at": "2024-01-01T10:00:00Z",
  "updated_at": "2024-01-01T10:00:00Z"
}
```

#### `dim_time` - Time Dimension
**Purpose:** Pre-populated calendar dimension for time-based analysis

**Example Data:**
```json
{
  "time_key": 20240615,
  "date_actual": "2024-06-15",
  "day_of_week": 6,
  "day_name": "Saturday",
  "week_of_year": 24,
  "month": 6,
  "month_name": "June",
  "quarter": 2,
  "year": 2024,
  "is_weekend": true,
  "is_holiday": false,
  "holiday_name": null,
  "fiscal_year": 2024,
  "fiscal_quarter": 2,
  "fiscal_period": 6
}
```

#### `dim_kpi` - KPI Definitions
**Purpose:** Stores KPI definitions for attribution and measurement

**Example Data:**
```json
{
  "kpi_key": 5001,
  "kpi_id": "kpi_roas",
  "kpi_name": "Return on Ad Spend (ROAS)",
  "kpi_family": "efficiency",
  "formula": "revenue_amount / spend_amount",
  "unit": "ratio",
  "attribution_window_days": 14,
  "attribution_model": "last_click",
  "is_incremental": false,
  "baseline_definition": null,
  "ontology_uri": "ex:KPI/ROAS",
  "created_at": "2024-01-01T10:00:00Z",
  "updated_at": "2024-01-01T10:00:00Z"
}
```

#### `dim_manufacturer` - Manufacturer Information
**Purpose:** Stores manufacturer/CPG company information

**Example Data:**
```json
{
  "manufacturer_key": 6001,
  "manufacturer_id": "coca_cola",
  "manufacturer_name": "The Coca-Cola Company",
  "parent_company": null,
  "country": "US",
  "tier": "tier1",
  "attributes": {
    "industry": "beverages",
    "founded_year": 1892
  },
  "created_at": "2024-01-01T10:00:00Z",
  "updated_at": "2024-01-01T10:00:00Z"
}
```

#### `dim_retailer` - Retailer Information
**Purpose:** Stores retailer/platform information

**Example Data:**
```json
{
  "retailer_key": 7001,
  "retailer_id": "walmart",
  "retailer_name": "Walmart Inc.",
  "retailer_type": "mass",
  "rmn_platform": "walmart_connect",
  "country": "US",
  "attributes": {
    "market_cap": "400B",
    "store_count": 4700
  },
  "created_at": "2024-01-01T10:00:00Z",
  "updated_at": "2024-01-01T10:00:00Z"
}
```

### Fact Tables

#### `fact_media_performance` - Media Performance Metrics
**Purpose:** Daily aggregated media performance metrics (impressions, clicks, spend, revenue)

**Example Data:**
```json
{
  "media_performance_id": 10001,
  "time_key": 20240615,
  "campaign_key": 2001,
  "product_key": 1001,
  "audience_key": 3001,
  "retailer_key": 7001,
  "manufacturer_key": 6001,
  "impressions_count": 125000,
  "clicks_count": 2500,
  "conversions_count": 125,
  "spend_amount": 1250.00,
  "revenue_amount": 3125.00,
  "orders_count": 125,
  "units_sold": 1500,
  "data_source": "amazon_ads_api",
  "normalization_run_id": "550e8400-e29b-41d4-a716-446655440000",
  "confidence_score": 0.95,
  "normalized_at": "2024-06-16T02:00:00Z",
  "created_at": "2024-06-16T02:00:00Z"
}
```

**Derived Metrics (computed on query):**
- CTR = 2500 / 125000 = 2.0%
- CPM = (1250 / 125000) * 1000 = $10.00
- CPC = 1250 / 2500 = $0.50
- ROAS = 3125 / 1250 = 2.5x
- Conversion Rate = 125 / 2500 = 5.0%

#### `fact_pos_performance` - Point-of-Sale Performance
**Purpose:** Daily aggregated POS metrics (units sold, revenue, margin, promotions)

**Example Data:**
```json
{
  "pos_performance_id": 20001,
  "time_key": 20240615,
  "store_key": 4001,
  "product_key": 1001,
  "manufacturer_key": 6001,
  "retailer_key": 7001,
  "units_sold": 450,
  "revenue_amount": 3145.50,
  "cost_amount": 2025.00,
  "margin_amount": 1120.50,
  "discount_amount": 450.00,
  "transactions_count": 380,
  "has_promotion": true,
  "promo_type": "TPR",
  "promo_discount_pct": 12.5,
  "has_display": true,
  "display_type": "end_cap",
  "data_source": "walmart_pos_api",
  "normalization_run_id": "550e8400-e29b-41d4-a716-446655440001",
  "confidence_score": 0.98,
  "normalized_at": "2024-06-16T03:00:00Z",
  "created_at": "2024-06-16T03:00:00Z"
}
```

#### `fact_attribution` - Attribution Results
**Purpose:** Incremental attribution results from MMM, test/control, geo-lift studies

**Example Data:**
```json
{
  "attribution_id": 30001,
  "time_key": 20240615,
  "campaign_key": 2001,
  "product_key": 1001,
  "store_key": 4001,
  "kpi_key": 5001,
  "manufacturer_key": 6001,
  "retailer_key": 7001,
  "baseline_value": 2500.00,
  "actual_value": 3125.00,
  "incremental_value": 625.00,
  "lift_pct": 25.0,
  "attribution_method": "test_control",
  "confidence_level": 0.95,
  "confidence_interval_lower": 500.00,
  "confidence_interval_upper": 750.00,
  "data_source": "attribution_engine",
  "normalization_run_id": "550e8400-e29b-41d4-a716-446655440002",
  "normalized_at": "2024-06-16T04:00:00Z",
  "created_at": "2024-06-16T04:00:00Z"
}
```

---

## 008_ontology_evolution.sql

### `ontology_concept_proposals` - Agent-Proposed Concepts
**Purpose:** Agents propose new ontology concepts when they encounter unknown terms

**Example Data:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440010",
  "proposed_concept_uri": "ex:ProductCategory/PlantBased",
  "pref_label": "Plant-Based Products",
  "alt_labels": ["vegan", "plant-based", "dairy-free"],
  "definition": "Products made from plant sources instead of animal sources",
  "broader_uri": "ex:ProductCategory/Food",
  "source": "agent_discovery",
  "source_agent_id": "product-taxonomy-agent",
  "confidence": 0.85,
  "examples": {
    "fields": ["product_title", "category"],
    "values": ["Oat Milk", "Almond Butter", "Vegan Cheese"]
  },
  "justification": "Encountered 150+ products with 'plant-based' or 'vegan' labels that don't map to existing categories",
  "status": "pending",
  "proposed_by": "product-taxonomy-agent",
  "proposed_at": "2024-06-15T10:00:00Z",
  "reviewed_by": null,
  "reviewed_at": null,
  "rejection_reason": null,
  "merged_into_uri": null,
  "metadata": {
    "frequency": 150,
    "contexts": ["amazon_ads", "walmart_connect"]
  }
}
```

### `ontology_change_log` - Ontology Change History
**Purpose:** Tracks all changes to the ontology (additions, modifications, deprecations)

**Example Data:**
```json
{
  "change_id": "550e8400-e29b-41d4-a716-446655440011",
  "change_type": "concept_added",
  "concept_uri": "ex:ProductCategory/PlantBased",
  "old_value": null,
  "new_value": {
    "pref_label": "Plant-Based Products",
    "definition": "Products made from plant sources",
    "broader_uri": "ex:ProductCategory/Food"
  },
  "changed_by": "admin@example.com",
  "changed_at": "2024-06-15T14:00:00Z",
  "change_reason": "Approved agent proposal - high frequency of usage",
  "affected_agents": ["product-taxonomy-agent", "normalization-agent"],
  "migration_script": null,
  "metadata": {
    "proposal_id": "550e8400-e29b-41d4-a716-446655440010"
  }
}
```

### `normalization_mapping_cache` - Successful Mapping Cache
**Purpose:** Caches successful field mappings to speed up future normalizations

**Example Data:**
```json
{
  "cache_id": "550e8400-e29b-41d4-a716-446655440012",
  "source_field": "campaign_type",
  "source_value": "SP",
  "source_pattern": null,
  "target_field": "tactic_uri",
  "target_value": "ex:Tactic/SponsoredProduct",
  "transformation_type": "enum_mapping",
  "confidence": 0.98,
  "agent_id": "campaign-tactic-agent",
  "ontology_concept_uri": "ex:Tactic/SponsoredProduct",
  "usage_count": 1250,
  "success_rate": 0.99,
  "last_used_at": "2024-06-15T12:00:00Z",
  "created_at": "2024-01-15T10:00:00Z",
  "expires_at": null,
  "metadata": {
    "source_system": "amazon_ads",
    "validation_passed": true
  }
}
```

---

## 009_taxonomy_versioning.sql

### `taxonomy_versions` - Taxonomy Version Tracking
**Purpose:** Tracks different versions of taxonomies (product categories, campaign tactics, etc.)

**Example Data:**
```json
{
  "version_id": 1,
  "taxonomy_type": "product_category",
  "version_number": "v2.0",
  "effective_date": "2024-06-01",
  "end_date": null,
  "is_current": true,
  "created_by": "taxonomy_team",
  "created_at": "2024-05-15T10:00:00Z",
  "change_summary": "Added plant-based category, split beverages into subcategories",
  "change_notes": {
    "added": ["ex:ProductCategory/PlantBased"],
    "modified": ["ex:ProductCategory/Beverages"],
    "deprecated": []
  },
  "approval_status": "approved",
  "approved_by": "admin@example.com",
  "approved_at": "2024-05-20T14:00:00Z",
  "metadata": {
    "node_count": 450,
    "hierarchy_depth": 4
  }
}
```

### `taxonomy_nodes` - Taxonomy Hierarchy Nodes
**Purpose:** Individual nodes in the taxonomy hierarchy

**Example Data:**
```json
{
  "node_id": "550e8400-e29b-41d4-a716-446655440020",
  "version_id": 1,
  "node_uri": "ex:ProductCategory/PlantBased",
  "node_label": "Plant-Based Products",
  "node_definition": "Products made from plant sources",
  "parent_uri": "ex:ProductCategory/Food",
  "node_level": 2,
  "sort_order": 15,
  "attributes": {
    "color": "green",
    "icon": "leaf",
    "trending": true
  },
  "is_leaf": false,
  "is_deprecated": false,
  "deprecated_reason": null,
  "metadata": {
    "product_count": 150
  }
}
```

### `taxonomy_mappings` - Cross-Version Mappings
**Purpose:** Maps nodes between taxonomy versions for backward compatibility

**Example Data:**
```json
{
  "mapping_id": "550e8400-e29b-41d4-a716-446655440021",
  "from_version_id": 1,
  "to_version_id": 2,
  "from_uri": "ex:ProductCategory/Beverages",
  "to_uris": ["ex:ProductCategory/Beverages/Carbonated", "ex:ProductCategory/Beverages/NonCarbonated"],
  "mapping_type": "split",
  "confidence": 1.0,
  "mapping_logic": "Automated split based on carbonation attribute",
  "created_at": "2024-06-01T10:00:00Z",
  "created_by": "taxonomy_team",
  "metadata": {
    "affected_products": 500
  }
}
```

---

## 012_hitl_normalization_queue.sql

### `hitl_normalization_queue` - Human Review Queue
**Purpose:** Queue for low-confidence normalization decisions requiring human review

**Example Data:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440030",
  "source_event_id": "amazon_ads_event_12345",
  "source": "amazon_ads",
  "raw_data": {
    "campaign_id": "camp_xyz",
    "campaign_name": "Summer Sale 2024",
    "campaign_type": "SPX",  // Unknown type
    "budget": "$5000",
    "start_date": "2024-06-01",
    "custom_attributes": {
      "promo_code": "SUMMER2024",
      "target_audience": "high_value_customers"
    }
  },
  "normalization_run_id": "550e8400-e29b-41d4-a716-446655440031",
  "schema_discovery_output": {
    "detected_fields": ["campaign_id", "campaign_name", "campaign_type", "budget"],
    "confidence": 0.75
  },
  "partial_normalizations": {
    "campaign_id": {
      "value": "camp_xyz",
      "confidence": 0.95
    },
    "campaign_name": {
      "value": "Summer Sale 2024",
      "confidence": 0.90
    }
  },
  "failed_fields": {
    "campaign_type": {
      "reason": "Unknown value 'SPX' not in taxonomy",
      "confidence": 0.30
    }
  },
  "review_reason": "low_confidence",
  "confidence_scores": {
    "overall": 0.60,
    "campaign_type": 0.30,
    "budget": 0.85
  },
  "validation_errors": {
    "budget": "Format mismatch: expected numeric, got string with $"
  },
  "anomalies": {
    "campaign_type": "Value 'SPX' not seen before in this source"
  },
  "complexity_score": 0.65,
  "field_count": 5,
  "unmapped_field_count": 2,
  "requires_domain_expertise": true,
  "contains_pii": false,
  "pii_fields": [],
  "masked_data": null,
  "pii_access_log": [],
  "priority": "high",
  "assigned_to": "user_123",
  "assigned_role": "data_analyst",
  "assigned_at": "2024-06-15T10:30:00Z",
  "status": "in_progress",
  "resolution": {
    "campaign_type": "ex:Tactic/SponsoredBrand",
    "budget": 5000.00
  },
  "resolution_notes": "SPX maps to Sponsored Brand. Budget parsed from string.",
  "resolved_by": "user_123",
  "resolved_at": "2024-06-15T11:00:00Z",
  "created_at": "2024-06-15T10:00:00Z",
  "sla_deadline": "2024-06-15T14:00:00Z",
  "sla_breached": false,
  "time_to_assignment_ms": 1800000,
  "time_to_resolution_ms": 3600000,
  "feedback_quality": "good",
  "used_for_training": true,
  "training_label_id": "550e8400-e29b-41d4-a716-446655440032",
  "metadata": {
    "review_duration_minutes": 30,
    "revision_count": 1
  }
}
```

---

## 014_partner_configuration.sql

### `partner_profiles` - Partner/Client Profiles
**Purpose:** Stores configuration for each RMN platform, manufacturer, or retailer

**Example Data:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440040",
  "partner_type": "rmn",
  "partner_id": "amazon_ads",
  "partner_name": "Amazon Advertising",
  "contact_email": "api-support@amazon.com",
  "account_manager_id": "user_456",
  "tier": "enterprise",
  "status": "active",
  "onboarded_at": "2024-01-15T10:00:00Z",
  "config": {
    "api_rate_limit": 1000,
    "api_timeout_seconds": 30,
    "default_timezone": "UTC",
    "supported_attribution_models": ["last_click", "first_click"],
    "custom_fields": ["campaign_type", "ad_group_type"]
  },
  "created_at": "2024-01-15T10:00:00Z",
  "updated_at": "2024-06-01T10:00:00Z"
}
```

### `partner_field_mappings` - Custom Field Mappings
**Purpose:** Partner-specific field mapping overrides

**Example Data:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440041",
  "partner_profile_id": "550e8400-e29b-41d4-a716-446655440040",
  "source_field": "campaign_type",
  "source_field_pattern": null,
  "target_field": "tactic_uri",
  "target_table": "dim_campaign",
  "transformation_type": "lookup",
  "transformation_config": {
    "lookup_table": {
      "SP": "ex:Tactic/SponsoredProduct",
      "SB": "ex:Tactic/SponsoredBrand",
      "SD": "ex:Tactic/SponsoredDisplay",
      "SPX": "ex:Tactic/SponsoredBrand"
    }
  },
  "override_priority": 200,
  "override_reason": "Amazon-specific campaign type codes",
  "requires_validation": true,
  "custom_validation_rules": {
    "allowed_values": ["SP", "SB", "SD", "SPX"]
  },
  "is_active": true,
  "effective_from": "2024-01-15T10:00:00Z",
  "effective_until": null,
  "created_by": "user_456",
  "created_at": "2024-01-15T10:00:00Z"
}
```

### `partner_validation_rules` - Custom Validation Rules
**Purpose:** Partner-specific data quality rules

**Example Data:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440042",
  "partner_profile_id": "550e8400-e29b-41d4-a716-446655440040",
  "rule_name": "amazon_spend_positive",
  "rule_type": "field_validation",
  "target_table": "fact_media_performance",
  "target_field": "spend_amount",
  "rule_expression": "spend_amount >= 0",
  "severity": "error",
  "error_message": "Spend amount must be non-negative",
  "is_active": true,
  "effective_from": "2024-01-15T10:00:00Z",
  "effective_until": null,
  "created_by": "user_456",
  "created_at": "2024-01-15T10:00:00Z"
}
```

---

## Summary

### Data Flow Example

1. **Raw Data Arrives** (from Amazon Ads API):
   ```json
   {
     "campaign_id": "camp_12345",
     "campaign_name": "Summer Sale",
     "campaign_type": "SP",
     "impressions": 125000,
     "clicks": 2500,
     "spend": "$1250.00"
   }
   ```

2. **Normalization Agent Processes**:
   - Uses `partner_field_mappings` to map `campaign_type: "SP"` → `tactic_uri: "ex:Tactic/SponsoredProduct"`
   - Uses `partner_validation_rules` to validate spend
   - Creates normalized record

3. **Data Stored in CDM**:
   - `dim_campaign`: Campaign dimension record
   - `fact_media_performance`: Daily metrics record

4. **If Low Confidence**:
   - Record goes to `hitl_normalization_queue` for human review

5. **If New Concept Discovered**:
   - Agent proposes to `ontology_concept_proposals`
   - After approval, added to `ontology_concepts`
   - Change logged in `ontology_change_log`

6. **If Taxonomy Changes**:
   - New version in `taxonomy_versions`
   - Nodes in `taxonomy_nodes`
   - Mappings in `taxonomy_mappings` for backward compatibility

