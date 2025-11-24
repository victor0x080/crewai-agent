"""
Manufacturer RMN Datacube Tools for CrewAI Agents
==================================================
Provides tools for querying the Manufacturer RMN datacube via Cube.dev REST API.

All agents that need access to RMN metrics (campaign performance, audience segments,
search terms, promotions, incrementality) should use these tools.

Based on Manufacturer RMN schema cubes:
- ManufacturerRmnPerformance (main fact cube)
- Campaign, AudienceSegment, SearchTerm, Promotion (dimensions)
- CampaignPacing, IncrementalityTest (operational cubes)
"""

import os
import requests
from typing import List, Dict, Any, Optional, Literal
from crewai.tools import tool
import json

CUBE_API_URL = os.getenv('CUBE_API_URL', 'http://localhost:4000')
CUBE_API_SECRET = os.getenv('CUBEJS_API_SECRET', 'secret')

def _query_cube(query: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Execute a Cube.dev query and return results."""
    try:
        response = requests.post(
            f'{CUBE_API_URL}/cubejs-api/v1/load',
            headers={
                'Authorization': CUBE_API_SECRET,
                'Content-Type': 'application/json'
            },
            json={'query': query},
            timeout=30
        )
        response.raise_for_status()
        return response.json().get('data', [])
    except Exception as e:
        raise Exception(f"Datacube query failed: {str(e)}")


@tool("query_rmn_datacube")
def query_rmn_datacube(
    measures: List[str],
    time_granularity: Literal['day', 'week', 'month'] = 'week',
    date_range: str = 'last 12 weeks',
    manufacturer_id: Optional[str] = None,
    campaign_id: Optional[str] = None,
    audience_segment_id: Optional[str] = None,
    search_term_id: Optional[str] = None,
    promotion_id: Optional[str] = None,
    dimensions: Optional[List[str]] = None,
    limit: int = 1000
) -> str:
    """
    Query the Manufacturer RMN datacube for campaign performance metrics.
    
    Args:
        measures: List of measures to retrieve (e.g., ['impressions', 'clicks', 'spend', 'attributedSales', 'roas'])
        time_granularity: Time aggregation level (day, week, month)
        date_range: Date range to query (e.g., 'last 12 weeks', '2025-01-01')
        manufacturer_id: Filter by specific manufacturer ID
        campaign_id: Filter by specific campaign ID
        audience_segment_id: Filter by specific audience segment ID
        search_term_id: Filter by specific search term ID
        promotion_id: Filter by specific promotion ID
        dimensions: Optional list of dimensions to include (e.g., ['Campaign.campaignName', 'AudienceSegment.segmentName'])
        limit: Maximum number of rows to return
    
    Returns:
        JSON string with query results
    
    Example:
        query_rmn_datacube(
            measures=['impressions', 'clicks', 'spend', 'roas'],
            time_granularity='week',
            manufacturer_id='MANUF-001'
        )
    """
    cube = 'ManufacturerRmnPerformance'
    
    # Build query
    query = {
        'measures': [f'{cube}.{m}' for m in measures],
        'dimensions': dimensions or [],
        'timeDimensions': [{
            'dimension': 'DateDim.date',  # ManufacturerRmnPerformance joins to DateDim via time_id
            'granularity': time_granularity,
            'dateRange': date_range
        }],
        'filters': [],
        'limit': limit
    }
    
    # Add filters
    if manufacturer_id:
        query['filters'].append({
            'member': f'{cube}.manufacturerId',
            'operator': 'equals',
            'values': [manufacturer_id]
        })
        query['dimensions'].append(f'{cube}.manufacturerId')
    
    if campaign_id:
        query['filters'].append({
            'member': f'{cube}.campaignId',
            'operator': 'equals',
            'values': [campaign_id]
        })
        query['dimensions'].append(f'{cube}.campaignId')
    
    if audience_segment_id:
        query['filters'].append({
            'member': f'{cube}.audienceSegmentId',
            'operator': 'equals',
            'values': [audience_segment_id]
        })
        query['dimensions'].append(f'{cube}.audienceSegmentId')
    
    if search_term_id:
        query['filters'].append({
            'member': f'{cube}.searchTermId',
            'operator': 'equals',
            'values': [search_term_id]
        })
        query['dimensions'].append(f'{cube}.searchTermId')
    
    if promotion_id:
        query['filters'].append({
            'member': f'{cube}.promotionId',
            'operator': 'equals',
            'values': [promotion_id]
        })
        query['dimensions'].append(f'{cube}.promotionId')
    
    # Execute query
    results = _query_cube(query)
    return json.dumps(results, indent=2)


@tool("get_rmn_performance_metrics")
def get_rmn_performance_metrics(
    time_granularity: Literal['day', 'week', 'month'] = 'week',
    date_range: str = 'last 12 weeks',
    manufacturer_id: Optional[str] = None,
    campaign_id: Optional[str] = None
) -> str:
    """
    Get RMN campaign performance metrics: impressions, clicks, spend, attributed sales, ROAS.
    
    Returns aggregated RMN performance data including impressions, clicks, spend,
    attributed sales, units sold, and calculated ROAS.
    """
    return query_rmn_datacube(
        measures=['impressions', 'clicks', 'spend', 'attributedSales', 'unitsSold', 'roas'],
        time_granularity=time_granularity,
        date_range=date_range,
        manufacturer_id=manufacturer_id,
        campaign_id=campaign_id
    )


@tool("get_incrementality_metrics")
def get_incrementality_metrics(
    time_granularity: Literal['day', 'week', 'month'] = 'week',
    date_range: str = 'last 12 weeks',
    campaign_id: Optional[str] = None
) -> str:
    """
    Get incrementality test metrics: incremental units, base units, incremental ROAS.
    
    Returns incrementality measurement data including incremental units (test vs control),
    base units (baseline without media), and incremental ROAS.
    """
    return query_rmn_datacube(
        measures=['incrementalUnits', 'baseUnits', 'incrementalRoas', 'attributedSales', 'spend'],
        time_granularity=time_granularity,
        date_range=date_range,
        campaign_id=campaign_id
    )


@tool("get_audience_performance")
def get_audience_performance(
    time_granularity: Literal['day', 'week', 'month'] = 'week',
    date_range: str = 'last 12 weeks',
    manufacturer_id: Optional[str] = None,
    audience_segment_id: Optional[str] = None
) -> str:
    """
    Get audience segment performance metrics.
    
    Returns performance data by audience segment including impressions, clicks,
    spend, attributed sales, and ROAS for audience targeting analysis.
    """
    return query_rmn_datacube(
        measures=['impressions', 'clicks', 'spend', 'attributedSales', 'roas', 'unitsSold'],
        time_granularity=time_granularity,
        date_range=date_range,
        manufacturer_id=manufacturer_id,
        audience_segment_id=audience_segment_id,
        dimensions=['AudienceSegment.segmentName', 'AudienceSegment.segmentType']
    )


@tool("get_search_term_performance")
def get_search_term_performance(
    time_granularity: Literal['day', 'week', 'month'] = 'week',
    date_range: str = 'last 12 weeks',
    campaign_id: Optional[str] = None,
    search_term_id: Optional[str] = None
) -> str:
    """
    Get search term/keyword performance metrics.
    
    Returns search term performance data including impressions, clicks, spend,
    attributed sales, and ROAS for keyword optimization.
    """
    return query_rmn_datacube(
        measures=['impressions', 'clicks', 'spend', 'attributedSales', 'roas'],
        time_granularity=time_granularity,
        date_range=date_range,
        campaign_id=campaign_id,
        search_term_id=search_term_id,
        dimensions=['SearchTerm.keywordText', 'SearchTerm.matchType', 'SearchTerm.keywordCategory']
    )


@tool("get_promotion_attribution")
def get_promotion_attribution(
    time_granularity: Literal['day', 'week', 'month'] = 'week',
    date_range: str = 'last 12 weeks',
    campaign_id: Optional[str] = None,
    promotion_id: Optional[str] = None
) -> str:
    """
    Get promotion-attributed sales metrics.
    
    Returns promotion performance data including promotion-attributed sales,
    halo sales (related product lift), and media vs promotion attribution split.
    """
    return query_rmn_datacube(
        measures=['promotionAttributedSales', 'haloSales', 'attributedSales', 'spend'],
        time_granularity=time_granularity,
        date_range=date_range,
        campaign_id=campaign_id,
        promotion_id=promotion_id,
        dimensions=['Promotion.promotionName', 'Promotion.promotionType']
    )


@tool("get_campaign_portfolio_insights")
def get_campaign_portfolio_insights(
    date_range: str = 'last 12 weeks',
    manufacturer_id: Optional[str] = None
) -> str:
    """
    Get comprehensive campaign portfolio metrics across all dimensions.
    
    Returns a unified view combining performance metrics across campaigns,
    audience segments, search terms, and promotions.
    
    Includes derived KPIs like ROAS, ACOS, incremental ROAS, and halo effects.
    """
    return query_rmn_datacube(
        measures=[
            'impressions', 'clicks', 'spend',
            'attributedSales', 'unitsSold',
            'roas', 'acos', 'incrementalRoas',
            'haloSales', 'promotionAttributedSales'
        ],
        time_granularity='week',
        date_range=date_range,
        manufacturer_id=manufacturer_id,
        dimensions=[
            'Campaign.campaignName',
            'Campaign.objective',
            'Campaign.channelId'
        ]
    )


@tool("detect_rmn_anomalies")
def detect_rmn_anomalies(
    date_range: str = 'last 4 weeks',
    manufacturer_id: Optional[str] = None
) -> str:
    """
    Detect anomalies in RMN campaign performance: low ROAS, high ACOS, negative incrementality.
    
    Returns campaigns with:
    - ROAS < 2.0 (poor efficiency)
    - ACOS > 50% (high cost per sale)
    - Negative incremental units (media not driving lift)
    - Click-through rate < 0.5% (low engagement)
    
    Use this to proactively identify underperforming campaigns requiring optimization.
    """
    results = query_rmn_datacube(
        measures=['impressions', 'clicks', 'spend', 'attributedSales', 'roas', 'acos', 'incrementalUnits'],
        time_granularity='week',
        date_range=date_range,
        manufacturer_id=manufacturer_id,
        dimensions=['Campaign.campaignName', 'Campaign.campaignId']
    )
    
    # Parse and filter for anomalies
    data = json.loads(results)
    anomalies = []
    for row in data:
        roas = row.get('ManufacturerRmnPerformance.roas', 999)
        acos = row.get('ManufacturerRmnPerformance.acos', 0)
        incremental_units = row.get('ManufacturerRmnPerformance.incrementalUnits', 0)
        clicks = row.get('ManufacturerRmnPerformance.clicks', 0)
        impressions = row.get('ManufacturerRmnPerformance.impressions', 1)
        ctr = (clicks / impressions * 100) if impressions > 0 else 0
        
        if (roas < 2.0) or (acos > 50) or (incremental_units < 0) or (ctr < 0.5):
            anomalies.append({
                **row,
                'anomaly_reasons': [
                    'Low ROAS' if roas < 2.0 else None,
                    'High ACOS' if acos > 50 else None,
                    'Negative incrementality' if incremental_units < 0 else None,
                    'Low CTR' if ctr < 0.5 else None
                ]
            })
    
    return json.dumps({
        'anomaly_count': len(anomalies),
        'anomalies': anomalies
    }, indent=2)


# Export all tools for easy import
DATACUBE_TOOLS = [
    query_rmn_datacube,
    get_rmn_performance_metrics,
    get_incrementality_metrics,
    get_audience_performance,
    get_search_term_performance,
    get_promotion_attribution,
    get_campaign_portfolio_insights,
    detect_rmn_anomalies
]

