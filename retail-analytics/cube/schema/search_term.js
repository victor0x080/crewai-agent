// ===================================================================
// Search Term Dimension Cube (Based on Canonical Schema v2.1.0)
// ===================================================================
// Keyword/search term performance for onsite search campaigns
// ===================================================================

cube(`SearchTerm`, {
  sql: `SELECT * FROM dim_search_term`,
  
  joins: {
    AdGroup: {
      relationship: `belongsTo`,
      sql: `${CUBE}.ad_group_id = ${AdGroup}.ad_group_id`
    }
  },
  
  dimensions: {
    searchTermId: { 
      sql: `search_term_id`, 
      type: `string`, 
      primaryKey: true,
      description: `Unique identifier for search term`
    },
    
    keywordText: { 
      sql: `keyword_text`, 
      type: `string`,
      description: `The search keyword or query`
    },
    
    keywordTextNormalized: { 
      sql: `keyword_text_normalized`, 
      type: `string`,
      description: `Lowercase, trimmed version for deduplication`
    },
    
    matchType: { 
      sql: `match_type`, 
      type: `string`,
      description: `Keyword match type (EXACT, PHRASE, BROAD, AUTO)`
    },
    
    bidAmount: { 
      sql: `bid_amount`, 
      type: `number`,
      description: `Bid amount for this keyword`,
      format: `currency`
    },
    
    qualityScore: { 
      sql: `quality_score`, 
      type: `number`,
      description: `Platform-assigned quality score (1-10 scale typical)`
    },
    
    searchVolumeEstimate: { 
      sql: `search_volume_estimate`, 
      type: `number`,
      description: `Estimated monthly search volume`
    },
    
    keywordCategory: { 
      sql: `keyword_category`, 
      type: `string`,
      description: `Classified category (BRAND, CATEGORY, COMPETITOR, LONG_TAIL)`
    },
    
    isNegativeKeyword: { 
      sql: `is_negative_keyword`, 
      type: `boolean`,
      description: `Whether this is an excluded keyword`
    },
    
    keywordStatus: { 
      sql: `keyword_status`, 
      type: `string`,
      description: `Keyword status (ACTIVE, PAUSED, ARCHIVED)`
    }
  }
});

