// ===================================================================
// Cube.dev Configuration
// ===================================================================

module.exports = {
  // Context to app ID mapping for multi-tenancy
  contextToAppId: ({ securityContext }) => {
    return securityContext.tenant || 'manufacturer-rmn-app';
  },
  
  // HTTP configuration
  http: {
    cors: {
      origin: '*',
      methods: 'GET,POST,PUT,DELETE',
      allowedHeaders: 'Content-Type,Authorization'
    }
  },
  
  // Query rewrite for security and optimization
  queryRewrite: (query, { securityContext }) => {
    // Add tenant filters if needed
    if (securityContext && securityContext.manufacturerId) {
      query.filters = query.filters || [];
      query.filters.push({
        member: 'ManufacturerRmnPerformance.manufacturerId',
        operator: 'equals',
        values: [securityContext.manufacturerId]
      });
    }
    
    return query;
  },
  
  // Pre-aggregations configuration
  preAggregationsSchema: 'pre_aggregations',
  
  // Schema version (invalidate cache on change)
  schemaVersion: () => {
    return Date.now().toString();
  },
  
  // Telemetry
  telemetry: false,
  
  // Scheduled refresh worker
  scheduledRefreshTimer: 30, // seconds
  
  // Orchestrator API
  orchestratorOptions: {
    redisPoolOptions: {
      poolMin: 2,
      poolMax: 10,
      idleTimeoutSeconds: 30
    }
  }
};

