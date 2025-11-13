"""
Simulation Integration Tools for CrewAI Agents
Connects agents to simulation generators (DemandForecast, Inventory, Pricing, Campaign)
"""
from crewai.tools import tool
from tools.redis_streams_tools import RedisStreamsClient, fetch_cloudevent
import json
from typing import Optional

@tool("fetch_demand_forecast_signal")
def fetch_demand_forecast_signal(sku: Optional[str] = None, retailer: Optional[str] = None) -> dict:
    """
    Fetch latest demand forecast signal from DemandForecastGenerator.
    Integrates with simulation server's demand.forecast.updated events.
    
    Args:
        sku: Optional SKU filter
        retailer: Optional retailer filter
    
    Returns:
        Latest demand forecast with horizon, units, quality metrics
    """
    r = RedisStreamsClient().get_client()
    
    # Read latest from demand forecast stream
    messages = r.xrevrange('stream:simulation:demand:forecast', count=10)
    
    for msg_id, fields in messages:
        decoded = {k.decode(): v.decode() for k, v in fields.items()}
        event_id = decoded.get('event_id')
        
        if event_id:
            # Try RedisJSON first, fallback to regular GET
            try:
                event = r.json().get(f"event:{event_id}")
            except Exception:
                raw = r.get(f"event:{event_id}")
                event = json.loads(raw.decode() if isinstance(raw, bytes) else raw) if raw else None
            if event and event.get('type') == 'demand.forecast.updated':
                data = event['data']
                # Filter if needed
                if sku and data.get('sku') != sku:
                    continue
                # Treat missing/blank/common values as wildcard (no filtering)
                if retailer not in (None, "", "all", "global") and data.get('retailer') != retailer:
                    continue
                
                return {
                    'sku': data.get('sku'),
                    'retailer': data.get('retailer'),
                    'horizon_days': data.get('horizon_days'),
                    'forecast_units': data.get('forecast_units'),
                    'quality': data.get('quality'),
                    'model_type': data.get('model_type'),
                    'version': data.get('version')
                }
    
    return {'error': 'No demand forecast signals found'}


@tool("fetch_inventory_position")
def fetch_inventory_position(sku: Optional[str] = None, location: Optional[str] = None) -> dict:
    """
    Fetch current inventory position from InventoryEventGenerator.
    
    Args:
        sku: Optional SKU filter
        location: Optional location filter
    
    Returns:
        Inventory levels (on_hand, in_transit, safety_stock)
    """
    r = RedisStreamsClient().get_client()
    
    messages = r.xrevrange('stream:simulation:inventory:position', count=10)
    
    for msg_id, fields in messages:
        decoded = {k.decode(): v.decode() for k, v in fields.items()}
        event_id = decoded.get('event_id')
        
        if event_id:
            try:
                event = r.json().get(f"event:{event_id}")
            except Exception:
                raw = r.get(f"event:{event_id}")
                event = json.loads(raw.decode() if isinstance(raw, bytes) else raw) if raw else None
            if event:
                data = event['data']
                # Normalize filters: treat None/"" as wildcard
                norm_sku = (sku or '').strip()
                norm_loc = (location or '').strip()
                if norm_sku and data.get('sku') != norm_sku:
                    continue
                if norm_loc and norm_loc.lower() not in ("all", "global") and data.get('location') != norm_loc:
                    continue
                
                return {
                    'sku': data.get('sku'),
                    'location': data.get('location'),
                    'on_hand': data.get('on_hand', 0),
                    'in_transit': data.get('in_transit', 0),
                    'safety_stock': data.get('safety_stock', 0),
                    'available': data.get('available', 0)
                }
    
    return {'error': 'No inventory position found'}


@tool("fetch_pricing_promo_data")
def fetch_pricing_promo_data(sku: Optional[str] = None) -> dict:
    """
    Fetch pricing and promo data from PricingPromoGenerator.
    
    Args:
        sku: Optional SKU filter
    
    Returns:
        Current price, promo status, elasticity estimates
    """
    r = RedisStreamsClient().get_client()
    
    messages = r.xrevrange('stream:simulation:pricing:updates', count=10)
    
    for msg_id, fields in messages:
        decoded = {k.decode(): v.decode() for k, v in fields.items()}
        event_id = decoded.get('event_id')
        
        if event_id:
            try:
                event = r.json().get(f"event:{event_id}")
            except Exception:
                raw = r.get(f"event:{event_id}")
                event = json.loads(raw.decode() if isinstance(raw, bytes) else raw) if raw else None
            if event:
                data = event['data']
                norm_sku = (sku or '').strip()
                if norm_sku and data.get('sku') != norm_sku:
                    continue
                
                return {
                    'sku': data.get('sku'),
                    'current_price': data.get('price'),
                    'promo_active': data.get('promo_active', False),
                    'promo_discount_pct': data.get('discount_pct', 0),
                    'elasticity_estimate': data.get('elasticity', -1.2)
                }
    
    return {'error': 'No pricing data found'}


@tool("fetch_campaign_performance")
def fetch_campaign_performance(campaign_id: Optional[str] = None) -> dict:
    """
    Fetch campaign performance from CampaignEventGenerator.
    
    Args:
        campaign_id: Optional campaign ID filter
    
    Returns:
        Campaign metrics (spend, impressions, conversions, ROAS)
    """
    r = RedisStreamsClient().get_client()
    
    messages = r.xrevrange('stream:simulation:campaign:performance', count=10)
    
    for msg_id, fields in messages:
        decoded = {k.decode(): v.decode() for k, v in fields.items()}
        event_id = decoded.get('event_id')
        
        if event_id:
            try:
                event = r.json().get(f"event:{event_id}")
            except Exception:
                raw = r.get(f"event:{event_id}")
                event = json.loads(raw.decode() if isinstance(raw, bytes) else raw) if raw else None
            if event:
                data = event['data']
                norm_cid = (campaign_id or '').strip()
                if norm_cid and data.get('campaign_id') != norm_cid:
                    continue
                
                return {
                    'campaign_id': data.get('campaign_id'),
                    'spend': data.get('spend', 0),
                    'impressions': data.get('impressions', 0),
                    'clicks': data.get('clicks', 0),
                    'conversions': data.get('conversions', 0),
                    'roas': data.get('roas', 0),
                    'status': data.get('status', 'active')
                }
    
    return {'error': 'No campaign performance found'}


@tool("run_simulation_scenario")
def run_simulation_scenario(scenario_config: dict) -> dict:
    """
    Trigger a simulation scenario run.
    Used by SSA to run what-if scenarios.
    
    Args:
        scenario_config: Scenario parameters (price_change, media_spend, etc.)
    
    Returns:
        Simulation results with KPI deltas
    """
    # Simplified simulation - in production would call actual simulation engine
    import random
    
    price_change_pct = scenario_config.get('price_change_pct', 0)
    media_spend_delta = scenario_config.get('media_spend_delta', 0)
    
    # Simple elasticity model
    price_elasticity = -1.2
    media_elasticity = 0.8
    
    baseline_revenue = 100000
    baseline_units = 5000
    
    revenue_delta = (
        baseline_revenue * (price_change_pct / 100) * (1 + price_elasticity) +
        media_spend_delta * media_elasticity * 0.01
    )
    
    units_delta = baseline_units * (price_change_pct / 100) * price_elasticity
    
    return {
        'scenario_id': f"sim_{random.randint(1000, 9999)}",
        'baseline_revenue': baseline_revenue,
        'baseline_units': baseline_units,
        'revenue_delta': revenue_delta,
        'units_delta': units_delta,
        'margin_delta': revenue_delta * 0.3,
        'stockout_risk': random.uniform(0.1, 0.4),
        'confidence': 0.85
    }


@tool("compute_stockout_risk")
def compute_stockout_risk(sku: str, forecast_units: float, on_hand: int, in_transit: int, lead_time_days: int) -> dict:
    """
    Compute stockout risk for IRA agent.
    Combines forecast, inventory, and lead time.
    
    Args:
        sku: SKU identifier
        forecast_units: Forecasted demand
        on_hand: Current on-hand inventory
        in_transit: In-transit inventory
        lead_time_days: Supplier lead time
    
    Returns:
        Stockout risk probability and days until stockout
    """
    import math
    
    total_available = on_hand + in_transit
    daily_demand = forecast_units / 30  # Assume 30-day forecast
    
    if daily_demand <= 0:
        return {'stockout_risk': 0.0, 'days_until_stockout': 999}
    
    days_of_supply = total_available / daily_demand
    
    # Risk increases as days_of_supply approaches lead_time
    if days_of_supply > lead_time_days * 2:
        risk = 0.05
    elif days_of_supply > lead_time_days:
        risk = 0.2
    elif days_of_supply > lead_time_days * 0.5:
        risk = 0.5
    else:
        risk = 0.9
    
    return {
        'sku': sku,
        'stockout_risk': round(risk, 3),
        'days_until_stockout': int(days_of_supply),
        'recommended_replenishment': max(0, int(lead_time_days * daily_demand - total_available)),
        'service_level': round(1 - risk, 3)
    }
