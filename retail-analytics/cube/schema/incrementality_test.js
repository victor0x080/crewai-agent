// ===================================================================
// Incrementality Test Cube (Based on Canonical Schema v2.1.0)
// ===================================================================
// Test/control framework for measuring true incrementality of media campaigns
// ===================================================================

cube(`IncrementalityTest`, {
  sql: `SELECT * FROM incrementality_test`,
  
  joins: {
    Campaign: {
      relationship: `belongsTo`,
      sql: `${CUBE}.campaign_id = ${Campaign}.campaign_id`
    },
    DateDim: {
      relationship: `belongsTo`,
      sql: `${CUBE}.start_date = ${DateDim}.date`
    }
  },
  
  dimensions: {
    testId: { 
      sql: `test_id`, 
      type: `string`, 
      primaryKey: true,
      description: `Unique identifier for incrementality test`
    },
    
    testName: { 
      sql: `test_name`, 
      type: `string`,
      description: `Name of the incrementality test`
    },
    
    testType: { 
      sql: `test_type`, 
      type: `string`,
      description: `Methodology (GEO_HOLDOUT, AUDIENCE_HOLDOUT, TIME_SERIES, etc.)`
    },
    
    testHypothesis: { 
      sql: `test_hypothesis`, 
      type: `string`,
      description: `What is being tested (e.g., 'RMN drives 15% incremental sales')`
    },
    
    testStatus: { 
      sql: `test_status`, 
      type: `string`,
      description: `Test status (PLANNED, IN_FLIGHT, COMPLETED, INVALIDATED, CANCELLED)`
    },
    
    startDate: { 
      sql: `start_date`, 
      type: `time`,
      description: `Test start date`
    },
    
    endDate: { 
      sql: `end_date`, 
      type: `time`,
      description: `Test end date`
    },
    
    statisticalPower: { 
      sql: `statistical_power`, 
      type: `number`,
      description: `Statistical power of test design (0-1)`,
      format: `percent`
    },
    
    minimumDetectableEffect: { 
      sql: `minimum_detectable_effect`, 
      type: `number`,
      description: `Smallest lift% test can detect reliably`,
      format: `percent`
    }
  },
  
  // Note: Results are stored in JSONB field, may need special handling
  // For now, we'll just expose the test metadata
});

