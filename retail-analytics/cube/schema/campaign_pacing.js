// ===================================================================
// Campaign Pacing Cube (Based on Canonical Schema v2.1.0)
// ===================================================================
// Tracks campaign budget pacing and forecasts for real-time optimization
// ===================================================================

cube(`CampaignPacing`, {
  sql: `SELECT * FROM campaign_pacing`,
  
  joins: {
    Campaign: {
      relationship: `belongsTo`,
      sql: `${CUBE}.campaign_id = ${Campaign}.campaign_id`
    },
    DateDim: {
      relationship: `belongsTo`,
      sql: `${CUBE}.snapshot_date = ${DateDim}.date`
    }
  },
  
  measures: {
    budgetAllocated: { 
      sql: `budget_allocated`, 
      type: `sum`,
      description: `Total campaign budget`,
      format: `currency`
    },
    
    budgetSpentToDate: { 
      sql: `budget_spent_to_date`, 
      type: `sum`,
      description: `Cumulative spend as of snapshot date`,
      format: `currency`
    },
    
    expectedSpendToDate: { 
      sql: `expected_spend_to_date`, 
      type: `sum`,
      description: `Pro-rated expected spend based on even pacing`,
      format: `currency`
    },
    
    spendVariance: { 
      sql: `spend_variance`, 
      type: `sum`,
      description: `Actual spend - expected spend`,
      format: `currency`
    },
    
    spendVariancePct: { 
      sql: `spend_variance_percentage`, 
      type: `avg`,
      description: `Variance as % of expected spend`,
      format: `percent`
    },
    
    projectedEndSpend: { 
      sql: `projected_end_spend`, 
      type: `sum`,
      description: `Forecasted total spend at current run rate`,
      format: `currency`
    },
    
    recommendedDailyBudget: { 
      sql: `recommended_daily_budget`, 
      type: `avg`,
      description: `Recommended daily spend to hit target`,
      format: `currency`
    },
    
    pacingAlertCount: {
      sql: `pacing_id`,
      type: `count`,
      description: `Count of pacing records with alerts triggered`
    }
  },
  
  dimensions: {
    pacingId: { 
      sql: `pacing_id`, 
      type: `string`, 
      primaryKey: true,
      description: `Unique identifier for pacing record`
    },
    
    campaignId: { 
      sql: `campaign_id`, 
      type: `string`,
      description: `Campaign identifier`
    },
    
    snapshotDate: { 
      sql: `snapshot_date`, 
      type: `time`,
      description: `Date of pacing calculation`
    },
    
    pacingStatus: { 
      sql: `pacing_status`, 
      type: `string`,
      description: `Current pacing health status (UNDER_PACING, ON_TRACK, OVER_PACING, EXHAUSTED)`
    },
    
    daysElapsed: { 
      sql: `days_elapsed`, 
      type: `number`,
      description: `Days since campaign start`
    },
    
    daysRemaining: { 
      sql: `days_remaining`, 
      type: `number`,
      description: `Days until campaign end`
    },
    
    projectedBudgetExhaustionDate: { 
      sql: `projected_budget_exhaustion_date`, 
      type: `time`,
      description: `Estimated date budget will be depleted`
    }
  },
  
  segments: {
    underPacing: {
      sql: `${CUBE}.pacing_status = 'UNDER_PACING'`,
      description: `Campaigns spending slower than expected`
    },
    
    overPacing: {
      sql: `${CUBE}.pacing_status = 'OVER_PACING'`,
      description: `Campaigns spending faster than expected`
    },
    
    onTrack: {
      sql: `${CUBE}.pacing_status = 'ON_TRACK'`,
      description: `Campaigns pacing as expected`
    },
    
    exhausted: {
      sql: `${CUBE}.pacing_status = 'EXHAUSTED'`,
      description: `Campaigns that have exhausted budget`
    }
  },
  
  preAggregations: {
    byCampaign: {
      type: `rollup`,
      measureReferences: [budgetAllocated, budgetSpentToDate, spendVariance, projectedEndSpend],
      dimensionReferences: [campaignId, pacingStatus],
      timeDimensionReference: snapshotDate,
      granularity: `day`,
      refreshKey: {
        every: `1 hour`
      }
    }
  }
});

