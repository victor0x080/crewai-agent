// ===================================================================
// Audience Segment Dimension Cube (Based on Canonical Schema v2.1.0)
// ===================================================================
// Platform-specific audience segments for targeting and performance analysis
// ===================================================================

cube(`AudienceSegment`, {
  sql: `SELECT * FROM dim_audience_segment`,
  
  joins: {
    Campaign: {
      relationship: `hasMany`,
      sql: `${CUBE}.channel_id = ${Campaign}.channel_id`
    }
  },
  
  dimensions: {
    audienceSegmentId: { 
      sql: `audience_segment_id`, 
      type: `string`, 
      primaryKey: true,
      description: `Canonical audience segment identifier`
    },
    
    segmentName: { 
      sql: `segment_name`, 
      type: `string`,
      description: `Display name of the audience segment`
    },
    
    segmentType: { 
      sql: `segment_type`, 
      type: `string`,
      description: `Classification (FIRST_PARTY, LOOKALIKE, CONTEXTUAL, etc.)`
    },
    
    segmentCategory: { 
      sql: `segment_category`, 
      type: `string`,
      description: `Platform taxonomy category`
    },
    
    platformSegmentId: { 
      sql: `platform_segment_id`, 
      type: `string`,
      description: `Native segment ID from RMN platform`
    },
    
    sizeEstimate: { 
      sql: `size_estimate`, 
      type: `number`,
      description: `Estimated reach of segment`
    },
    
    cpmModifier: { 
      sql: `cpm_modifier`, 
      type: `number`,
      description: `Cost multiplier relative to baseline CPM`
    },
    
    matchRate: { 
      sql: `match_rate`, 
      type: `number`,
      description: `For first-party segments: % of uploaded records matched`,
      format: `percent`
    },
    
    segmentStatus: { 
      sql: `segment_status`, 
      type: `string`,
      description: `Segment status (ACTIVE, BUILDING, EXPIRED, ARCHIVED)`
    }
  }
});

