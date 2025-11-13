"""
Albertsons Media Collective RMN Adapter
Multi-banner reach (Safeway, Vons, Jewel-Osco, etc.)
"""
import asyncio
import logging
from typing import Dict, Any
from datetime import datetime
import sys
sys.path.append('..')
from adapters.base_platform_adapter import BasePlatformAdapter, ActionOutcome

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AlbertsonsMediaAdapter(BasePlatformAdapter):
    """Albertsons Media Collective RMN Adapter - Multi-banner reach"""
    
    def __init__(self):
        super().__init__(
            platform_name='albertsons-media',
            input_stream='stream:mco:event:action',
            output_stream='stream:mco:event:outcome',
            consumer_group='adapter-albertsons-media',
            rate_limit_per_hour=1600
        )
        logger.info("Albertsons Media Collective Adapter initialized")
    
    async def execute_action(self, action: Dict[str, Any]) -> ActionOutcome:
        operation = action.get('operation')
        params = action.get('params', {})
        target = action.get('target', {})
        entity_id = target.get('entityId', 'unknown')
        start_time = datetime.now()
        
        try:
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
            elif operation == 'setBannerTargeting':
                result = await self._set_banner_targeting(params)
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
            logger.error(f"Albertsons action failed: {operation} - {e}")
            return ActionOutcome(
                action_id=action.get('id', 'unknown'),
                status='failure',
                platform_id=entity_id,
                api_latency_ms=latency_ms,
                error={'code': 'ALBERTSONS_ERROR', 'message': str(e), 'operation': operation}
            )
    
    async def _set_campaign_budget(self, params: Dict[str, Any]) -> Dict[str, Any]:
        campaign_id = params['campaignId']
        budget = params['dailyBudget']
        logger.info(f"Setting Albertsons campaign budget: {campaign_id} = {budget}")
        await asyncio.sleep(0.05)
        return {'platform_id': campaign_id, 'metadata': {'previousBudget': budget * 0.86}}
    
    async def _set_keyword_bid(self, params: Dict[str, Any]) -> Dict[str, Any]:
        keyword_id = params['keywordId']
        bid = params['bid']
        logger.info(f"Setting Albertsons keyword bid: {keyword_id} = {bid}")
        await asyncio.sleep(0.04)
        return {'platform_id': keyword_id, 'metadata': {'adGroupId': params['adGroupId']}}
    
    async def _set_product_bid(self, params: Dict[str, Any]) -> Dict[str, Any]:
        product_id = params['productId']
        bid = params['bid']
        logger.info(f"Setting Albertsons product bid: {product_id} = {bid}")
        await asyncio.sleep(0.04)
        return {'platform_id': product_id, 'metadata': {'productCategory': 'GROCERY'}}
    
    async def _update_audience_targeting(self, params: Dict[str, Any]) -> Dict[str, Any]:
        campaign_id = params['campaignId']
        audiences = params['audiences']
        logger.info(f"Updating Albertsons audiences: {campaign_id} ({len(audiences)} segments)")
        await asyncio.sleep(0.06)
        return {'platform_id': campaign_id, 'metadata': {'totalAudiences': len(audiences)}}
    
    async def _pause_campaign(self, params: Dict[str, Any]) -> Dict[str, Any]:
        campaign_id = params['campaignId']
        logger.info(f"Pausing Albertsons campaign: {campaign_id}")
        await asyncio.sleep(0.03)
        return {'platform_id': campaign_id, 'metadata': {'newStatus': 'PAUSED'}}
    
    async def _add_negative_keyword(self, params: Dict[str, Any]) -> Dict[str, Any]:
        entity_id = params['id']
        keyword = params['keyword']
        logger.info(f"Adding Albertsons negative keyword: {keyword}")
        await asyncio.sleep(0.03)
        return {'platform_id': entity_id, 'metadata': {'keyword': keyword}}
    
    async def _set_geotargeting(self, params: Dict[str, Any]) -> Dict[str, Any]:
        campaign_id = params['campaignId']
        locations = params['locations']
        logger.info(f"Updating Albertsons geotargeting: {campaign_id} ({len(locations)} locations)")
        await asyncio.sleep(0.05)
        return {'platform_id': campaign_id, 'metadata': {'locationsCount': len(locations)}}
    
    async def _update_creative(self, params: Dict[str, Any]) -> Dict[str, Any]:
        ad_id = params['adId']
        logger.info(f"Updating Albertsons creative: {ad_id}")
        await asyncio.sleep(0.04)
        return {'platform_id': ad_id, 'metadata': {'approvalStatus': 'PENDING_REVIEW'}}
    
    async def _set_banner_targeting(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Set multi-banner targeting (Safeway, Vons, Jewel-Osco, etc.)"""
        campaign_id = params.get('campaignId', 'unknown')
        banners = params.get('banners', [])
        logger.info(f"Setting Albertsons banner targeting: {campaign_id} ({len(banners)} banners)")
        await asyncio.sleep(0.05)
        return {
            'platform_id': campaign_id,
            'metadata': {
                'bannersCount': len(banners),
                'banners': banners[:5],  # First 5 for metadata
                'multiBannerReach': True
            }
        }


if __name__ == '__main__':
    adapter = AlbertsonsMediaAdapter()
    asyncio.run(adapter.start())
