# Datacube Integration Guide

This document describes how the Retail Datacube has been integrated into the NEW_CREWAI_AGENT system.

## Overview

The Retail Datacube provides unified access to retail metrics across multiple domains:
- **POS** (Point of Sale) - Sales, units, returns, discounts
- **Inventory** - On hand, on order, receipts
- **Marketing** - Spend, impressions, clicks, ROAS
- **Merchandising** - Facings, promos, assortment
- **Procurement** - Inbound POs, costs, lead times
- **RMN** (Retail Media Network) - Campaign, product, category, location metrics

## Integration Points

### 1. Python Tools (`agents/crewai_python/tools/datacube_tools.py`)

The datacube tools are available for all CrewAI agents:

```python
from tools.datacube_tools import (
    get_pos_metrics,
    get_inventory_metrics,
    get_marketing_metrics,
    get_cross_domain_insights,
    detect_anomalies
)

# Use in agent
agent = Agent(
    role='Retail Analyst',
    tools=[get_pos_metrics, get_cross_domain_insights, detect_anomalies]
)
```

**Available Tools:**
- `query_retail_datacube()` - Generic query tool
- `get_pos_metrics()` - Sales metrics
- `get_inventory_metrics()` - Inventory metrics
- `get_marketing_metrics()` - Marketing metrics
- `get_merchandising_metrics()` - Merchandising metrics
- `get_procurement_metrics()` - Procurement metrics
- `get_cross_domain_insights()` - All domains combined
- `detect_anomalies()` - Anomaly detection

### 2. Tool Registry Integration

The datacube tools are automatically included for agents with these capabilities:
- `semantic_data` - Includes `get_cross_domain_insights`, `query_retail_datacube`
- `forecasting` - Includes `get_pos_metrics`, `get_cross_domain_insights`
- `inventory` - Includes `get_inventory_metrics`, `get_procurement_metrics`
- `anomaly_detection` - Includes `detect_anomalies`, `get_cross_domain_insights`
- `campaign` - Includes `get_marketing_metrics`, `get_pos_metrics`
- `retail_media` - Includes `get_marketing_metrics`, `get_cross_domain_insights`

### 3. Node.js Backend Service (`src/services/datacube/RetailDatacubeService.js`)

The TypeScript service is available for Node.js backend:

```javascript
import { retailDatacube } from './services/datacube/RetailDatacubeService.js';

// Get sales data
const sales = await retailDatacube.getPOSMetrics({
  timeGranularity: 'week',
  dateRange: 'last 12 weeks',
  regionId: 5
});

// Get cross-domain insights
const insights = await retailDatacube.getCrossDomainInsights({
  storeId: 101,
  dateRange: 'last 4 weeks'
});
```

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# Datacube Configuration
CUBE_API_URL=http://localhost:4000
CUBEJS_API_SECRET=your-secret-key-here
```

**Default Values:**
- `CUBE_API_URL`: `http://localhost:4000`
- `CUBEJS_API_SECRET`: `secret` (change in production!)

### Dependencies

The following dependencies are required:

**Python (`agents/crewai_python/requirements.txt`):**
- `requests>=2.31.0` ✅ (already included)

**Node.js (`package.json`):**
- `axios>=1.6.0` ✅ (added)

## Usage Examples

### Python Agent Example

```python
from crewai import Agent
from tools.datacube_tools import get_cross_domain_insights, detect_anomalies

# Create agent with datacube tools
analyst = Agent(
    role='Retail Performance Analyst',
    goal='Analyze sales trends and identify inventory risks',
    backstory='Expert in retail analytics with 10+ years experience',
    tools=[get_cross_domain_insights, detect_anomalies],
    verbose=True
)

# Agent can now use these tools in execution
# The agent will automatically call:
# - get_cross_domain_insights(store_id=101, date_range='last 4 weeks')
# - detect_anomalies(region_id=5)
```

### Node.js Backend Example

```javascript
import { retailDatacube } from './services/datacube/RetailDatacubeService.js';

// In your API endpoint
app.post('/api/analyze-store', async (req, res) => {
  const { storeId } = req.body;
  
  try {
    // Get comprehensive insights
    const insights = await retailDatacube.getCrossDomainInsights({
      storeId,
      dateRange: 'last 4 weeks'
    });
    
    // Detect problems
    const anomalies = await retailDatacube.detectAnomalies({
      dateRange: 'last 4 weeks'
    });
    
    res.json({
      insights,
      anomalies: anomalies.length,
      recommendations: generateRecommendations(insights, anomalies)
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});
```

## Data Source Mapping

The tool registry automatically maps data sources to datacube tools:

- `datacube` or `retail_datacube` → All datacube tools
- `pos` → `get_pos_metrics`
- `marketing` → `get_marketing_metrics`
- `merchandising` → `get_merchandising_metrics`
- `procurement` → `get_procurement_metrics`
- `cross_domain` → `get_cross_domain_insights`

## Agent Factory Integration

The agent factory automatically includes datacube tools for agents with relevant capabilities. When an agent is created with capabilities like:
- `forecasting`
- `inventory`
- `anomaly_detection`
- `campaign`
- `retail_media`

The factory will automatically add the appropriate datacube tools to the agent's tool list.

## Setup Instructions

### 1. Install Dependencies

```bash
# Python dependencies (already in requirements.txt)
cd agents/crewai_python
pip install -r requirements.txt

# Node.js dependencies
cd ../..
npm install
```

### 2. Configure Environment

```bash
# Add to .env file
CUBE_API_URL=http://localhost:4000
CUBEJS_API_SECRET=your-secret-key-here
```

### 3. Start Cube.dev Server

The datacube requires a running Cube.dev server. See the IMS-feature-retail-datacube project for setup instructions:

```bash
cd IMS-feature-retail-datacube/retail-analytics/cube
npm install
npm run dev
```

### 4. Test Integration

```python
# Test Python tools
python -c "from tools.datacube_tools import get_pos_metrics; print(get_pos_metrics(date_range='last 4 weeks'))"
```

```javascript
// Test Node.js service
import { retailDatacube } from './src/services/datacube/RetailDatacubeService.js';
const data = await retailDatacube.getPOSMetrics({ dateRange: 'last 4 weeks' });
console.log(data);
```

## Troubleshooting

### "Datacube query failed"
- Check if Cube.dev is running: `curl http://localhost:4000/cubejs-api/v1/load`
- Verify `CUBE_API_URL` and `CUBEJS_API_SECRET` in `.env`
- Check Cube.dev logs for errors

### "Connection refused"
- Start Cube.dev server: `cd retail-analytics/cube && npm run dev`
- Verify the port (default: 4000)

### "Module not found"
- Install dependencies: `npm install` and `pip install -r requirements.txt`
- Check Python path includes `agents/crewai_python/tools`

## Benefits

1. **Unified Data Access**: Single API for all retail metrics
2. **Automatic Tool Selection**: Tool registry automatically includes datacube tools for relevant capabilities
3. **Cross-Domain Insights**: Get unified metrics across POS, inventory, marketing, etc.
4. **Anomaly Detection**: Built-in detection of low ROAS, stockouts, overstock
5. **Fast Queries**: Pre-aggregated data for sub-second response times
6. **Agent-Ready**: Tools designed specifically for CrewAI agents

## Next Steps

1. **Setup Cube.dev**: Follow setup instructions in `IMS-feature-retail-datacube/retail-analytics/`
2. **Load Data**: Populate the datacube with your retail data
3. **Test Agents**: Create agents with datacube capabilities and test queries
4. **Monitor Performance**: Track query performance and optimize as needed

## Related Documentation

- **Datacube Implementation**: `IMS-feature-retail-datacube/docs/RETAIL_DATACUBE_IMPLEMENTATION.md`
- **Tool Registry**: `agents/crewai_python/factory/tool_registry.py`
- **Agent Factory**: `agents/crewai_python/factory/agent_factory.py`

