/**
 * RMN Data Normalizer
 * 
 * Normalizes data from multiple Retail Media Networks (RMNs) into a common schema.
 * Handles field mapping, metric standardization, and ontology concept mapping.
 * 
 * Supported RMNs:
 * - Amazon Advertising
 * - Walmart Connect
 * - Instacart Ads
 * - Target Roundel (future)
 * - Kroger Precision Marketing (future)
 */

// Note: Import OntologyService if available
let OntologyService;
try {
  const ontologyModule = require('../ontology/OntologyService');
  OntologyService = ontologyModule.OntologyService || ontologyModule.default;
} catch (e) {
  console.warn('OntologyService not available, using stub');
  OntologyService = class {
    async resolve() { return null; }
    async expand() { return []; }
  };
}

class RMNDataNormalizer {
  constructor() {
    this.ontology = new OntologyService();
  }

  /**
   * Normalize campaign from any RMN
   */
  async normalizeCampaign(rmn, rawCampaign) {
    console.log(`[RMNNormalizer] Normalizing ${rmn} campaign: ${rawCampaign.campaignId || rawCampaign.id}`);

    let normalized;

    switch (rmn) {
      case 'amazon_ads':
        normalized = this.normalizeAmazonCampaign(rawCampaign);
        break;
      case 'walmart_connect':
        normalized = this.normalizeWalmartCampaign(rawCampaign);
        break;
      case 'instacart_ads':
        normalized = this.normalizeInstacartCampaign(rawCampaign);
        break;
      default:
        throw new Error(`Unsupported RMN: ${rmn}`);
    }

    // Enrich with ontology concepts
    normalized.metadata.ontologyConcepts = await this.extractOntologyConcepts(normalized);

    return normalized;
  }

  /**
   * Normalize metrics from any RMN
   */
  async normalizeMetrics(rmn, rawMetrics) {
    let normalized;

    switch (rmn) {
      case 'amazon_ads':
        normalized = this.normalizeAmazonMetrics(rawMetrics);
        break;
      case 'walmart_connect':
        normalized = this.normalizeWalmartMetrics(rawMetrics);
        break;
      case 'instacart_ads':
        normalized = this.normalizeInstacartMetrics(rawMetrics);
        break;
      default:
        throw new Error(`Unsupported RMN: ${rmn}`);
    }

    // Calculate data quality score
    normalized.metadata.dataQuality = this.assessDataQuality(normalized);

    return normalized;
  }

  /**
   * Map product ID across RMNs
   */
  async mapProductId(rmn, rmnProductId) {
    // This would typically query a product catalog or identity resolution service
    // For now, return a stub
    return {
      normalizedId: `product_${rmnProductId}`,
      rmn,
      rmnProductId,
      name: 'Product Name',
      brand: 'Brand Name',
      category: 'Category'
    };
  }

  // ========== Amazon Ads Normalization ==========

  normalizeAmazonCampaign(raw) {
    return {
      campaignId: `amazon_${raw.campaignId}`,
      rmn: 'amazon_ads',
      rmnCampaignId: raw.campaignId,
      name: raw.name,
      status: this.mapStatus('amazon_ads', raw.state),
      budget: {
        amount: raw.dailyBudget || 0,
        currency: 'USD',
        type: 'DAILY'
      },
      startDate: raw.startDate,
      endDate: raw.endDate,
      targeting: {
        products: [], // Would extract from ad groups
        keywords: [],
        categories: [],
        locations: [],
        audiences: []
      },
      metadata: {
        originalData: raw,
        normalizedAt: new Date().toISOString(),
        ontologyConcepts: []
      }
    };
  }

  normalizeAmazonMetrics(raw) {
    return {
      campaignId: `amazon_${raw.campaignId}`,
      rmn: 'amazon_ads',
      date: raw.date,
      impressions: raw.impressions,
      clicks: raw.clicks,
      spend: raw.spend,
      sales: raw.sales,
      orders: raw.orders,
      roas: raw.roas,
      acos: raw.acos,
      ctr: raw.ctr,
      cpc: raw.cpc,
      cvr: raw.cvr,
      cpm: raw.impressions > 0 ? (raw.spend / raw.impressions) * 1000 : 0,
      extended: {
        attributionWindow: 14 // Amazon uses 14-day attribution
      },
      metadata: {
        originalData: raw,
        normalizedAt: new Date().toISOString(),
        dataQuality: {
          completeness: 1.0,
          accuracy: 1.0,
          issues: []
        }
      }
    };
  }

  // ========== Walmart Connect Normalization ==========

  normalizeWalmartCampaign(raw) {
    return {
      campaignId: `walmart_${raw.campaignId}`,
      rmn: 'walmart_connect',
      rmnCampaignId: raw.campaignId,
      name: raw.name,
      status: this.mapStatus('walmart_connect', raw.status),
      budget: {
        amount: raw.budget?.amount || 0,
        currency: raw.budget?.currency || 'USD',
        type: raw.budget?.type || 'DAILY'
      },
      startDate: raw.startDate,
      endDate: raw.endDate,
      targeting: {
        products: raw.targeting?.products || [],
        keywords: raw.targeting?.keywords || [],
        categories: raw.targeting?.categories || [],
        locations: raw.targeting?.locations || [],
        audiences: []
      },
      metadata: {
        originalData: raw,
        normalizedAt: new Date().toISOString(),
        ontologyConcepts: []
      }
    };
  }

  normalizeWalmartMetrics(raw) {
    return {
      campaignId: `walmart_${raw.campaignId}`,
      rmn: 'walmart_connect',
      date: raw.date,
      impressions: raw.impressions,
      clicks: raw.clicks,
      spend: raw.spend,
      sales: raw.sales,
      orders: raw.orders,
      roas: raw.roas,
      acos: raw.acos,
      ctr: raw.ctr,
      cpc: raw.cpc,
      cvr: raw.cvr,
      cpm: raw.impressions > 0 ? (raw.spend / raw.impressions) * 1000 : 0,
      extended: {
        attributionWindow: 30, // Walmart uses 30-day attribution
        inStoreSales: raw.inStoreSales,
        onlineSales: raw.onlineSales
      },
      metadata: {
        originalData: raw,
        normalizedAt: new Date().toISOString(),
        dataQuality: {
          completeness: 1.0,
          accuracy: 1.0,
          issues: []
        }
      }
    };
  }

  // ========== Instacart Ads Normalization ==========

  normalizeInstacartCampaign(raw) {
    return {
      campaignId: `instacart_${raw.campaignId}`,
      rmn: 'instacart_ads',
      rmnCampaignId: raw.campaignId,
      name: raw.name,
      status: this.mapStatus('instacart_ads', raw.status),
      budget: {
        amount: raw.budget?.amount || 0,
        currency: 'USD',
        type: raw.budget?.type || 'DAILY'
      },
      startDate: raw.startDate,
      endDate: raw.endDate,
      targeting: {
        products: [],
        keywords: raw.targeting?.keywords || [],
        categories: raw.targeting?.categories || [],
        locations: raw.targeting?.locations?.zipCodes || [],
        audiences: raw.targeting?.retailers || [] // Retailers as audience segments
      },
      metadata: {
        originalData: raw,
        normalizedAt: new Date().toISOString(),
        ontologyConcepts: []
      }
    };
  }

  normalizeInstacartMetrics(raw) {
    return {
      campaignId: `instacart_${raw.campaignId}`,
      rmn: 'instacart_ads',
      date: raw.date,
      impressions: raw.impressions,
      clicks: raw.clicks,
      spend: raw.spend,
      sales: raw.sales,
      orders: raw.orders,
      roas: raw.roas,
      acos: raw.acos,
      ctr: raw.ctr,
      cpc: raw.cpc,
      cvr: raw.cvr,
      cpm: raw.impressions > 0 ? (raw.spend / raw.impressions) * 1000 : 0,
      extended: {
        attributionWindow: 7, // Instacart uses 7-day attribution
        retailerBreakdown: raw.retailerBreakdown,
        units: raw.units,
        avgOrderValue: raw.avgOrderValue
      },
      metadata: {
        originalData: raw,
        normalizedAt: new Date().toISOString(),
        dataQuality: {
          completeness: 1.0,
          accuracy: 1.0,
          issues: []
        }
      }
    };
  }

  // ========== Helper Methods ==========

  /**
   * Map RMN-specific status to normalized status
   */
  mapStatus(rmn, status) {
    const statusMap = {
      amazon_ads: {
        'enabled': 'ACTIVE',
        'paused': 'PAUSED',
        'archived': 'ARCHIVED'
      },
      walmart_connect: {
        'ACTIVE': 'ACTIVE',
        'PAUSED': 'PAUSED',
        'ARCHIVED': 'ARCHIVED'
      },
      instacart_ads: {
        'ACTIVE': 'ACTIVE',
        'PAUSED': 'PAUSED',
        'ENDED': 'ENDED'
      },
      target_roundel: {},
      kroger: {}
    };

    return statusMap[rmn]?.[status] || 'PAUSED';
  }

  /**
   * Extract ontology concepts from campaign
   */
  async extractOntologyConcepts(campaign) {
    const concepts = [];

    // Map RMN to ontology concept
    const rmnConcepts = {
      amazon_ads: 'ex:AmazonAdvertising',
      walmart_connect: 'ex:WalmartConnect',
      instacart_ads: 'ex:InstacartAds',
      target_roundel: 'ex:TargetRoundel',
      kroger: 'ex:KrogerPrecisionMarketing'
    };

    concepts.push(rmnConcepts[campaign.rmn]);
    concepts.push('ex:Campaign');
    concepts.push('ex:RetailMediaNetwork');

    return concepts;
  }

  /**
   * Assess data quality
   */
  assessDataQuality(metrics) {
    const issues = [];
    let completeness = 1.0;

    // Check for missing required fields
    if (!metrics.impressions) {
      issues.push('Missing impressions');
      completeness -= 0.1;
    }
    if (!metrics.clicks) {
      issues.push('Missing clicks');
      completeness -= 0.1;
    }
    if (!metrics.spend) {
      issues.push('Missing spend');
      completeness -= 0.2;
    }

    // Check for data anomalies
    if (metrics.clicks > metrics.impressions) {
      issues.push('Clicks exceed impressions (data anomaly)');
    }
    if (metrics.ctr > 100) {
      issues.push('CTR exceeds 100% (data anomaly)');
    }

    return {
      completeness: Math.max(0, completeness),
      accuracy: issues.length === 0 ? 1.0 : 0.9,
      issues
    };
  }
}

/**
 * Factory function
 */
function createRMNDataNormalizer() {
  return new RMNDataNormalizer();
}

module.exports = {
  RMNDataNormalizer,
  createRMNDataNormalizer
};

