// ===================================================================
// Campaign Dimension Cube (Based on Canonical Schema v2.1.0)
// ===================================================================
// Enhanced campaign with hierarchy support
// ===================================================================

cube(`Campaign`, {
  sql: `SELECT * FROM dim_campaign`,
  
  joins: {
    DateDim: {
      relationship: `belongsTo`,
      sql: `${CUBE}.start_date = ${DateDim}.date`
    }
  },
  
  dimensions: {
    campaignId: { 
      sql: `campaign_id`, 
      type: `string`, 
      primaryKey: true,
      description: `Campaign identifier`
    },
    
    campaignName: { 
      sql: `campaign_name`, 
      type: `string`,
      description: `Campaign name`
    },
    
    manufacturerId: { 
      sql: `manufacturer_id`, 
      type: `string`,
      description: `Manufacturer identifier`
    },
    
    channelId: { 
      sql: `channel_id`, 
      type: `string`,
      description: `RMN channel identifier`
    },
    
    parentCampaignId: { 
      sql: `parent_campaign_id`, 
      type: `string`,
      description: `Parent campaign for hierarchy`
    },
    
    objective: { 
      sql: `objective`, 
      type: `string`,
      description: `Campaign objective (AWARENESS, CONSIDERATION, CONVERSION, etc.)`
    },
    
    startDate: { 
      sql: `start_date`, 
      type: `time`,
      description: `Campaign start date`
    },
    
    endDate: { 
      sql: `end_date`, 
      type: `time`,
      description: `Campaign end date`
    },
    
    budgetTotal: { 
      sql: `budget_total`, 
      type: `number`,
      description: `Total campaign budget`,
      format: `currency`
    },
    
    budgetCurrency: { 
      sql: `budget_currency`, 
      type: `string`,
      description: `Budget currency code`
    },
    
    campaignStatus: { 
      sql: `campaign_status`, 
      type: `string`,
      description: `Campaign status (DRAFT, SCHEDULED, ACTIVE, PAUSED, COMPLETED, CANCELLED)`
    }
  },
  
  segments: {
    activeCampaigns: {
      sql: `${CUBE}.campaign_status = 'ACTIVE'`,
      description: `Currently active campaigns`
    },
    
    completedCampaigns: {
      sql: `${CUBE}.campaign_status = 'COMPLETED'`,
      description: `Completed campaigns`
    }
  }
});

