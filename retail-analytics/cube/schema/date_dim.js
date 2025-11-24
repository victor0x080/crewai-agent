// ===================================================================
// Date Dimension Cube
// ===================================================================

cube(`DateDim`, {
  sql: `SELECT date, week_start, month_start, quarter_start, year, fiscal_week, fiscal_period FROM dim_date`,
  
  dimensions: {
    date: { 
      sql: `date`, 
      type: `time`, 
      primaryKey: true,
      description: `Calendar date`
    },
    
    weekStart: { 
      sql: `week_start`, 
      type: `time`,
      description: `Week start date`
    },
    
    monthStart: { 
      sql: `month_start`, 
      type: `time`,
      description: `Month start date`
    },
    
    quarterStart: {
      sql: `quarter_start`,
      type: `time`,
      description: `Quarter start date`
    },
    
    year: {
      sql: `year`,
      type: `number`,
      description: `Calendar year`
    },
    
    fiscalWeek: {
      sql: `fiscal_week`,
      type: `string`,
      description: `Fiscal week identifier`
    },
    
    fiscalPeriod: {
      sql: `fiscal_period`,
      type: `string`,
      description: `Fiscal period identifier`
    }
  }
});

