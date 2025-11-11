"""
Walmart Connect RMN Adapter
Implements Walmart Connect operations with in-store + online attribution
"""
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import sys
sys.path.append('..')
from adapters.base_platform_adapter import BasePlatformAdapter, ActionOutcome

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WalmartConnectAdapter(BasePlatformAdapter):
    """
    Walmart Connect RMN Adapter
    
    Features:
    - In-store + online attribution
    - Walmart+ member targeting
    - Store pickup targeting
    - Rollback event optimization
    """
    
    def __init__(self):
        super().__init__(
            platform_name='walmart-connect',
            input_stream='stream:mco:event:action',
            output_stream='stream:mco:event:outcome',
            consumer_group='adapter-walmart-connect',
            rate_limit_per_hour=2000  # Walmart Connect has higher limits
        )
        logger.info("Walmart Connect Adapter initialized")
    
    async def execute_action(self, action: Dict[str, Any]) -> ActionOutcome:
        """
        Execute Walmart Connect platform action
        
        Supported operations:
        - setCampaignBudget: Set campaign daily/lifetime budget
        - setKeywordBid: Set keyword-level bid
        - setProductBid: Set product-level bid (Walmart Item ID)
        - updateAudienceTargeting: Update audience segments (Walmart+, in-store, online)
        - pauseCampaign: Pause campaign
        - addNegativeKeyword: Add negative keyword
        - setGeotargeting: Set store/zip/DMA/state targeting
        - updateCreative: Update ad creative assets
        - setAttributionWindow: Set click/view attribution windows
        """
        operation = action.get('operation')
        params = action.get('params', {})
        target = action.get('target', {})
        entity_id = target.get('entityId', 'unknown')
        
        start_time = datetime.now()
        
        try:
            # Route to operation handler
            if operation == 'setCampaignBudget':
                result = await self._set_campaign_budget(params)
            elif operation == 'setKeywordBid':
                result = await self._set_keyword_bid(params)
            elif operation == 'setProductBid':
                result = await self._set_product_bid(params)
            elif operation == 'updateAudienceTargeting':
                result = await self._update_audience_targeting(params)
            elif operation == 'pauseCampaign':
                result = await self._pause_campaign(params)
            elif operation == 'addNegativeKeyword':
                result = await self._add_negative_keyword(params)
            elif operation == 'setGeotargeting':
                result = await self._set_geotargeting(params)
            elif operation == 'updateCreative':
                result = await self._update_creative(params)
            elif operation == 'setAttributionWindow':
                result = await self._set_attribution_window(params)
            else:
                raise ValueError(f"Unsupported operation: {operation}")
            
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            return ActionOutcome(
                action_id=action.get('id', 'unknown'),
                status='success',
                platform_id=result.get('platform_id', entity_id),
                api_latency_ms=latency_ms,
                metadata=result.get('metadata', {})
            )
            
        except Exception as e:
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000
            logger.error(f"Walmart Connect action failed: {operation} - {e}")
            
            return ActionOutcome(
                action_id=action.get('id', 'unknown'),
                status='failure',
                platform_id=entity_id,
                api_latency_ms=latency_ms,
                error={
                    'code': 'WALMART_CONNECT_ERROR',
                    'message': str(e),
                    'operation': operation
                }
            )
    
    async def _set_campaign_budget(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Set campaign budget (daily or lifetime)"""
        campaign_id = params['campaignId']
        budget = params['dailyBudget']
        currency = params['currency']
        budget_type = params.get('budgetType', 'DAILY')
        
        logger.info(f"Setting Walmart Connect campaign budget: {campaign_id} = {budget} {currency} ({budget_type})")
        
        # Simulate Walmart Connect API call
        await asyncio.sleep(0.05)
        
        return {
            'platform_id': campaign_id,
            'metadata': {
                'budgetType': budget_type,
                'previousBudget': budget * 0.8,  # Simulated
                'effectiveDate': datetime.now().isoformat()
            }
        }
    
    async def _set_keyword_bid(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Set keyword-level bid"""
        ad_group_id = params['adGroupId']
        keyword_id = params['keywordId']
        bid = params['bid']
        currency = params['currency']
        
        logger.info(f"Setting Walmart Connect keyword bid: {keyword_id} = {bid} {currency}")
        
        await asyncio.sleep(0.04)
        
        return {
            'platform_id': keyword_id,
            'metadata': {
                'adGroupId': ad_group_id,
                'previousBid': bid * 0.9,
                'estimatedImpressions': 1500
            }
        }
    
    async def _set_product_bid(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Set product-level bid (Walmart Item ID)"""
        ad_group_id = params['adGroupId']
        product_id = params['productId']
        bid = params['bid']
        currency = params['currency']
        
        logger.info(f"Setting Walmart Connect product bid: {product_id} = {bid} {currency}")
        
        await asyncio.sleep(0.04)
        
        return {
            'platform_id': product_id,
            'metadata': {
                'adGroupId': ad_group_id,
                'itemType': 'WALMART_ITEM',
                'inStockStatus': 'IN_STOCK'
            }
        }
    
    async def _update_audience_targeting(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update audience targeting (Walmart+, in-store, online, custom)"""
        campaign_id = params['campaignId']
        audiences = params['audiences']
        
        added = [a for a in audiences if a['action'] == 'ADD']
        removed = [a for a in audiences if a['action'] == 'REMOVE']
        
        logger.info(f"Updating Walmart Connect audiences: {campaign_id} (+{len(added)}, -{len(removed)})")
        
        await asyncio.sleep(0.06)
        
        return {
            'platform_id': campaign_id,
            'metadata': {
                'audiencesAdded': len(added),
                'audiencesRemoved': len(removed),
                'totalAudiences': len(added) - len(removed) + 3,  # Simulated existing
                'walmartPlusIncluded': any(a['audienceType'] == 'WALMART_PLUS' for a in added)
            }
        }
    
    async def _pause_campaign(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Pause campaign"""
        campaign_id = params['campaignId']
        
        logger.info(f"Pausing Walmart Connect campaign: {campaign_id}")
        
        await asyncio.sleep(0.03)
        
        return {
            'platform_id': campaign_id,
            'metadata': {
                'previousStatus': 'ACTIVE',
                'newStatus': 'PAUSED',
                'pausedAt': datetime.now().isoformat()
            }
        }
    
    async def _add_negative_keyword(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Add negative keyword"""
        scope = params['scope']
        entity_id = params['id']
        keyword = params['keyword']
        match_type = params['matchType']
        
        logger.info(f"Adding Walmart Connect negative keyword: {keyword} ({match_type}) to {scope} {entity_id}")
        
        await asyncio.sleep(0.03)
        
        return {
            'platform_id': entity_id,
            'metadata': {
                'scope': scope,
                'keyword': keyword,
                'matchType': match_type,
                'estimatedImpactReduction': '5-10%'
            }
        }
    
    async def _set_geotargeting(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Set geotargeting (store, zip, DMA, state)"""
        campaign_id = params['campaignId']
        locations = params['locations']
        
        added = [loc for loc in locations if loc['action'] == 'ADD']
        removed = [loc for loc in locations if loc['action'] == 'REMOVE']
        
        logger.info(f"Updating Walmart Connect geotargeting: {campaign_id} (+{len(added)}, -{len(removed)})")
        
        await asyncio.sleep(0.05)
        
        # Count location types
        stores = [loc for loc in added if loc['locationType'] == 'STORE']
        
        return {
            'platform_id': campaign_id,
            'metadata': {
                'locationsAdded': len(added),
                'locationsRemoved': len(removed),
                'storeTargetingEnabled': len(stores) > 0,
                'totalStores': len(stores)
            }
        }
    
    async def _update_creative(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update ad creative assets"""
        ad_id = params['adId']
        assets = params['creativeAssets']
        
        logger.info(f"Updating Walmart Connect creative: {ad_id}")
        
        await asyncio.sleep(0.04)
        
        return {
            'platform_id': ad_id,
            'metadata': {
                'headline': assets.get('headline', '')[:50],
                'hasImage': 'imageUrl' in assets,
                'callToAction': assets.get('callToAction', 'SHOP_NOW'),
                'approvalStatus': 'PENDING_REVIEW'
            }
        }
    
    async def _set_attribution_window(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Set click/view attribution windows"""
        campaign_id = params['campaignId']
        click_window = params['clickWindow']
        view_window = params['viewWindow']
        
        logger.info(f"Setting Walmart Connect attribution: {campaign_id} (click: {click_window}d, view: {view_window}d)")
        
        await asyncio.sleep(0.03)
        
        return {
            'platform_id': campaign_id,
            'metadata': {
                'clickWindow': click_window,
                'viewWindow': view_window,
                'attributionModel': 'LAST_CLICK',
                'inStoreAttributionEnabled': True
            }
        }


if __name__ == '__main__':
    """Run Walmart Connect adapter standalone"""
    adapter = WalmartConnectAdapter()
    asyncio.run(adapter.start())
