// ===================================================================
// Promotion Dimension Cube (Based on Canonical Schema v2.1.0)
// ===================================================================
// Tracks manufacturer promotions (coupons, discounts) to attribute 
// sales lift to media vs. promotion
// ===================================================================

cube(`Promotion`, {
  sql: `SELECT * FROM dim_promotion`,
  
  joins: {
    Campaign: {
      relationship: `belongsTo`,
      sql: `${CUBE}.coordinated_campaign_id = ${Campaign}.campaign_id`
    },
    Product: {
      relationship: `belongsTo`,
      sql: `${CUBE}.sku_id_canonical = ${Product}.sku_id`
    }
  },
  
  dimensions: {
    promotionId: { 
      sql: `promotion_id`, 
      type: `string`, 
      primaryKey: true,
      description: `Unique identifier for the promotion`
    },
    
    promotionName: { 
      sql: `promotion_name`, 
      type: `string`,
      description: `Name of the promotion`
    },
    
    promotionType: { 
      sql: `promotion_type`, 
      type: `string`,
      description: `Type of promotional mechanic (COUPON_DIGITAL, PRICE_DISCOUNT, BOGO, etc.)`
    },
    
    discountAmount: { 
      sql: `discount_amount`, 
      type: `number`,
      description: `Absolute discount value (e.g., $0.50 off)`,
      format: `currency`
    },
    
    discountPercentage: { 
      sql: `discount_percentage`, 
      type: `number`,
      description: `Percentage discount (e.g., 20%)`,
      format: `percent`
    },
    
    minimumPurchaseQuantity: { 
      sql: `minimum_purchase_quantity`, 
      type: `number`,
      description: `Min quantity to qualify (e.g., Buy 2 get $1 off)`
    },
    
    validFrom: { 
      sql: `valid_from`, 
      type: `time`,
      description: `Promotion start date/time`
    },
    
    validTo: { 
      sql: `valid_to`, 
      type: `time`,
      description: `Promotion end date/time`
    },
    
    redemptionChannel: { 
      sql: `redemption_channel`, 
      type: `string`,
      description: `Redemption channel (DIGITAL_ONLY, INSTORE_ONLY, OMNICHANNEL)`
    },
    
    totalBudget: { 
      sql: `total_budget`, 
      type: `number`,
      description: `Total promotional budget allocated`,
      format: `currency`
    },
    
    promotionStatus: { 
      sql: `promotion_status`, 
      type: `string`,
      description: `Promotion status (SCHEDULED, ACTIVE, PAUSED, COMPLETED, CANCELLED)`
    },
    
    coordinatedCampaignId: { 
      sql: `coordinated_campaign_id`, 
      type: `string`,
      description: `FK to campaign if promotion is media-coordinated`
    }
  },
  
  segments: {
    activePromotions: {
      sql: `${CUBE}.promotion_status = 'ACTIVE'`,
      description: `Currently active promotions`
    },
    
    coordinatedPromotions: {
      sql: `${CUBE}.coordinated_campaign_id IS NOT NULL`,
      description: `Promotions coordinated with media campaigns`
    }
  }
});

