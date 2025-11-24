// ===================================================================
// Manufacturer RMN Performance Cube (Based on Canonical Schema v2.1.0)
// ===================================================================
// This cube is based on the rmn_performance_fact entity from the
// canonical manufacturer-rmn-model schema.
// 
// Key features:
// - Uses rmn_performance_fact (canonical schema)
// - Includes NEW fields: audience_segment_id, search_term_id, promotion_id
// - Includes NEW measures: halo_sales, promotion_attributed_sales, incremental_units
// - Links to new dimension cubes: AudienceSegment, SearchTerm, Promotion
// ===================================================================

cube(`ManufacturerRmnPerformance`, {
  sql: `SELECT * FROM rmn_performance_fact`,
  
  joins: {
    Campaign: {
      relationship: `belongsTo`,
      sql: `${CUBE}.campaign_id = ${Campaign}.campaign_id`
    },
    AudienceSegment: {
      relationship: `belongsTo`,
      sql: `${CUBE}.audience_segment_id = ${AudienceSegment}.audience_segment_id`
    },
    SearchTerm: {
      relationship: `belongsTo`,
      sql: `${CUBE}.search_term_id = ${SearchTerm}.search_term_id`
    },
    Promotion: {
      relationship: `belongsTo`,
      sql: `${CUBE}.promotion_id = ${Promotion}.promotion_id`
    },
    DateDim: {
      relationship: `belongsTo`,
      sql: `${CUBE}.time_id = ${DateDim}.date`
    }
  },
  
  measures: {
    // Core metrics (from canonical schema)
    impressions: { 
      sql: `impressions`, 
      type: `sum`,
      description: `Total ad impressions`
    },
    
    clicks: { 
      sql: `clicks`, 
      type: `sum`,
      description: `Total ad clicks`
    },
    
    spend: { 
      sql: `spend`, 
      type: `sum`,
      description: `Total ad spend`,
      format: `currency`
    },
    
    attributedSales: { 
      sql: `attributed_sales`, 
      type: `sum`,
      description: `Total attributed sales`,
      format: `currency`
    },
    
    clickAttributedSales: {
      sql: `click_attributed_sales`,
      type: `sum`,
      description: `Click-attributed sales`,
      format: `currency`
    },
    
    viewAttributedSales: {
      sql: `view_attributed_sales`,
      type: `sum`,
      description: `View-attributed sales`,
      format: `currency`
    },
    
    unitsSold: { 
      sql: `units_sold`, 
      type: `sum`,
      description: `Total units sold`
    },
    
    // NEW: Incrementality metrics (from canonical schema)
    incrementalUnits: {
      sql: `incremental_units`,
      type: `sum`,
      description: `Incremental units (test vs control)`
    },
    
    baseUnits: {
      sql: `base_units`,
      type: `sum`,
      description: `Baseline units (without media)`
    },
    
    // NEW: Halo effect (from canonical schema)
    haloSales: {
      sql: `halo_sales`,
      type: `sum`,
      description: `Sales lift on related products (halo effect)`,
      format: `currency`
    },
    
    // NEW: Promotion attribution (from canonical schema)
    promotionAttributedSales: {
      sql: `promotion_attributed_sales`,
      type: `sum`,
      description: `Sales directly tied to promotion vs media`,
      format: `currency`
    },
    
    grossMargin: {
      sql: `gross_margin`,
      type: `sum`,
      description: `Gross margin`,
      format: `currency`
    },
    
    // Calculated KPIs
    roas: {
      sql: `${attributedSales} / NULLIF(${spend}, 0)`,
      type: `number`,
      description: `Return on ad spend`,
      format: `number`
    },
    
    acos: {
      sql: `${spend} / NULLIF(${attributedSales}, 0) * 100`,
      type: `number`,
      description: `Advertising cost of sales`,
      format: `percent`
    },
    
    ctr: {
      sql: `${clicks} / NULLIF(${impressions}, 0) * 100`,
      type: `number`,
      description: `Click-through rate`,
      format: `percent`
    },
    
    // NEW: Incremental ROAS (from canonical schema)
    incrementalRoas: {
      sql: `${incrementalUnits} * ${attributedSales} / NULLIF(${spend}, 0)`,
      type: `number`,
      description: `Incremental return on ad spend (iROAS)`,
      format: `number`
    },
    
    // NEW: Incrementality lift (from canonical schema)
    incrementalityLift: {
      sql: `${incrementalUnits} / NULLIF(${baseUnits}, 0) * 100`,
      type: `number`,
      description: `Incremental lift percentage`,
      format: `percent`
    },
    
    // NEW: Halo effect ratio (from canonical schema)
    haloEffectRatio: {
      sql: `${haloSales} / NULLIF(${attributedSales}, 0) * 100`,
      type: `number`,
      description: `Halo sales as % of primary sales`,
      format: `percent`
    }
  },
  
  dimensions: {
    factId: { 
      sql: `fact_id`, 
      type: `string`, 
      primaryKey: true,
      description: `Fact record identifier`
    },
    
    manufacturerId: { 
      sql: `manufacturer_id`, 
      type: `string`,
      description: `Manufacturer identifier`
    },
    
    campaignId: { 
      sql: `campaign_id`, 
      type: `string`,
      description: `Campaign identifier`
    },
    
    channelId: { 
      sql: `channel_id`, 
      type: `string`,
      description: `RMN channel identifier`
    },
    
    // NEW: Audience segment dimension (from canonical schema)
    audienceSegmentId: { 
      sql: `audience_segment_id`, 
      type: `string`,
      description: `Audience segment identifier`
    },
    
    // NEW: Search term dimension (from canonical schema)
    searchTermId: { 
      sql: `search_term_id`, 
      type: `string`,
      description: `Search term/keyword identifier`
    },
    
    // NEW: Promotion dimension (from canonical schema)
    promotionId: { 
      sql: `promotion_id`, 
      type: `string`,
      description: `Promotion identifier (if sale during promo)`
    },
    
    aggregationLevel: { 
      sql: `aggregation_level`, 
      type: `string`,
      description: `Aggregation level (DAILY, WEEKLY, MONTHLY, CAMPAIGN, LIFETIME)`
    }
  },
  
  segments: {
    highROAS: {
      sql: `${attributedSales} / NULLIF(${spend}, 0) > 3.0`,
      description: `Campaigns with ROAS > 3.0`
    },
    
    highIncrementality: {
      sql: `${incrementalUnits} / NULLIF(${baseUnits}, 0) > 0.15`,
      description: `Campaigns with >15% incremental lift`
    },
    
    hasHaloEffect: {
      sql: `${haloSales} > 0`,
      description: `Campaigns showing halo effect on related products`
    }
  },
  
  preAggregations: {
    // Weekly performance by campaign
    byCampaignWeek: {
      type: `rollup`,
      measureReferences: [
        impressions, clicks, spend, attributedSales, 
        unitsSold, incrementalUnits, haloSales
      ],
      dimensionReferences: [campaignId, manufacturerId, channelId],
      timeDimensionReference: DateDim.date,
      granularity: `week`,
      partitionGranularity: `month`,
      refreshKey: {
        every: `1 day`
      }
    },
    
    // Daily performance for recent data
    byCampaignDay: {
      type: `rollup`,
      measureReferences: [impressions, clicks, spend, attributedSales],
      dimensionReferences: [campaignId, audienceSegmentId, searchTermId],
      timeDimensionReference: DateDim.date,
      granularity: `day`,
      partitionGranularity: `month`,
      refreshKey: {
        every: `6 hours`
      }
    }
  }
});

