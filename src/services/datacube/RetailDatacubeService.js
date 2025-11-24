// ===================================================================
// Retail Datacube Service - Agent Integration
// ===================================================================
// Provides a high-level interface for agents to query the retail
// datacube via Cube.dev REST API
// ===================================================================

import axios from 'axios';

/**
 * Retail Datacube Service
 * 
 * Provides agents with easy access to retail metrics across all domains:
 * - POS (sales, units)
 * - Inventory (on hand, on order, receipts)
 * - Marketing (spend, impressions, clicks, ROAS)
 * - Merchandising (facings, promos, assortment)
 * - Procurement (inbound POs, costs, lead times)
 * - RMN (Retail Media Network - campaign, product, category, location grains)
 */
export class RetailDatacubeService {
  constructor(cubeApiUrl, apiToken) {
    this.cubeApiUrl = cubeApiUrl || process.env.CUBE_API_URL || 'http://localhost:4000';
    this.apiToken = apiToken || process.env.CUBEJS_API_SECRET || 'secret';
    
    this.client = axios.create({
      baseURL: `${this.cubeApiUrl}/cubejs-api/v1`,
      headers: {
        'Authorization': this.apiToken,
        'Content-Type': 'application/json'
      },
      timeout: 30000
    });
  }

  /**
   * Execute a raw Cube.dev query
   */
  async query(query) {
    try {
      const response = await this.client.post('/load', { query });
      return response.data;
    } catch (error) {
      console.error('[RetailDatacube] Query error:', error.message);
      throw new Error(`Datacube query failed: ${error.message}`);
    }
  }

  /**
   * High-level query builder for agents
   */
  async queryMetrics(options) {
    const cube = this.getCubeName(options.cube || 'weekly');
    
    // Build measures with cube prefix
    const measures = options.measures.map(m => `${cube}.${m}`);
    
    // Build dimensions
    const dimensions = (options.dimensions || []).map(d => `${cube}.${d}`);
    
    // Add common dimension filters
    if (options.storeId) {
      dimensions.push(`${cube}.storeId`);
    }
    if (options.regionId) {
      dimensions.push(`${cube}.regionId`);
    }
    if (options.categoryId) {
      dimensions.push(`${cube}.categoryId`);
    }
    if (options.skuId && cube !== 'RetailWeeklyStoreCategory') {
      dimensions.push(`${cube}.skuId`);
    }
    
    // Build time dimension
    const timeDimensions = [];
    if (options.timeGranularity) {
      const timeDim = cube === 'RetailWeeklyStoreCategory' ? 'week' : 'date';
      timeDimensions.push({
        dimension: `${cube}.${timeDim}`,
        granularity: options.timeGranularity,
        dateRange: options.dateRange || 'last 12 weeks'
      });
    }
    
    // Build filters
    const filters = [];
    if (options.storeId) {
      filters.push({
        member: `${cube}.storeId`,
        operator: 'equals',
        values: [options.storeId]
      });
    }
    if (options.regionId) {
      filters.push({
        member: `${cube}.regionId`,
        operator: 'equals',
        values: [options.regionId]
      });
    }
    if (options.categoryId) {
      filters.push({
        member: `${cube}.categoryId`,
        operator: 'equals',
        values: [options.categoryId]
      });
    }
    if (options.skuId && cube !== 'RetailWeeklyStoreCategory') {
      filters.push({
        member: `${cube}.skuId`,
        operator: 'equals',
        values: [options.skuId]
      });
    }
    
    // RMN-specific filters
    if (options.campaignId) {
      filters.push({
        member: `${cube}.campaignId`,
        operator: 'equals',
        values: [options.campaignId]
      });
    }
    if (options.retailer) {
      filters.push({
        member: `${cube}.retailer`,
        operator: 'equals',
        values: [options.retailer]
      });
    }
    if (options.campaignType) {
      filters.push({
        member: `${cube}.campaignType`,
        operator: 'equals',
        values: [options.campaignType]
      });
    }
    if (options.productSku) {
      filters.push({
        member: `${cube}.productSku`,
        operator: 'equals',
        values: [options.productSku]
      });
    }
    if (options.category) {
      filters.push({
        member: `${cube}.category`,
        operator: 'equals',
        values: [options.category]
      });
    }
    
    // Add custom filters
    if (options.filters) {
      filters.push(...options.filters.map(f => ({
        member: `${cube}.${f.field}`,
        operator: f.operator,
        values: f.values
      })));
    }
    
    const queryObj = {
      measures,
      dimensions,
      timeDimensions,
      filters: filters.length > 0 ? filters : undefined,
      limit: options.limit || 1000
    };
    
    const response = await this.query(queryObj);
    return response.data;
  }

  /**
   * Get POS metrics (sales, units)
   */
  async getPOSMetrics(options) {
    return this.queryMetrics({
      ...options,
      cube: 'pos',
      measures: options.measures || ['unitsSold', 'netSales']
    });
  }

  /**
   * Get inventory metrics (on hand, on order, receipts)
   */
  async getInventoryMetrics(options) {
    return this.queryMetrics({
      ...options,
      cube: 'inventory',
      measures: options.measures || ['onHand', 'onOrder', 'receipts']
    });
  }

  /**
   * Get marketing metrics (spend, ROAS, clicks)
   */
  async getMarketingMetrics(options) {
    return this.queryMetrics({
      ...options,
      cube: 'marketing',
      measures: options.measures || ['spend', 'impressions', 'clicks', 'roas']
    });
  }

  /**
   * Get merchandising metrics (facings, promos, assortment)
   */
  async getMerchandisingMetrics(options) {
    return this.queryMetrics({
      ...options,
      cube: 'merch',
      measures: options.measures || ['facingsAvg', 'promoRate', 'inAssortmentRate']
    });
  }

  /**
   * Get procurement metrics (inbound POs, costs, lead times)
   */
  async getProcurementMetrics(options) {
    return this.queryMetrics({
      ...options,
      cube: 'procurement',
      measures: options.measures || ['poQtyInbound', 'avgUnitCost', 'avgLeadTimeDays']
    });
  }

  /**
   * Get unified weekly metrics (all domains)
   */
  async getWeeklyMetrics(options) {
    return this.queryMetrics({
      ...options,
      cube: 'weekly',
      measures: options.measures || ['unitsSold', 'netSales', 'onHand', 'mktSpend', 'roas']
    });
  }

  /**
   * Get cross-domain insights (combines multiple domains)
   */
  async getCrossDomainInsights(options) {
    return this.queryMetrics({
      cube: 'weekly',
      measures: [
        'unitsSold', 'netSales', 
        'onHand', 'weeksOfSupply',
        'mktSpend', 'roas',
        'avgPromoDepth', 'assortmentInRate',
        'poQtyInbound', 'stockoutRisk'
      ],
      timeGranularity: 'week',
      ...options
    });
  }

  /**
   * Detect anomalies (low ROAS, stockout risk, overstock)
   */
  async detectAnomalies(options) {
    const data = await this.queryMetrics({
      cube: 'weekly',
      measures: [
        'unitsSold', 'netSales', 'weeksOfSupply',
        'roas', 'stockoutRisk', 'supplyChainHealth'
      ],
      dimensions: ['storeId', 'categoryId'],
      timeGranularity: 'week',
      ...options
    });

    return data.filter((row) => {
      return (
        (row['RetailWeeklyStoreCategory.roas'] && row['RetailWeeklyStoreCategory.roas'] < 2) ||
        (row['RetailWeeklyStoreCategory.weeksOfSupply'] && row['RetailWeeklyStoreCategory.weeksOfSupply'] < 1) ||
        (row['RetailWeeklyStoreCategory.weeksOfSupply'] && row['RetailWeeklyStoreCategory.weeksOfSupply'] > 12)
      );
    });
  }

  getCubeName(cube) {
    const cubeMap = {
      pos: 'RetailPosDaily',
      inventory: 'RetailInventoryDaily',
      marketing: 'RetailMarketingDaily',
      merch: 'RetailMerchDaily',
      procurement: 'RetailProcurementDaily',
      weekly: 'RetailWeeklyStoreCategory',
      rmn_campaign: 'RMNCampaign',
      rmn_product: 'RMNProduct',
      rmn_category: 'RMNCategory',
      rmn_location: 'RMNLocation'
    };
    return cubeMap[cube] || 'RetailWeeklyStoreCategory';
  }
}

// Singleton instance
export const retailDatacube = new RetailDatacubeService();

