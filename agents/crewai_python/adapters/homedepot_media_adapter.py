"""
Home Depot Media Network RMN Adapter
Home improvement with Pro Xtra B2B targeting
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


class HomeDepotMediaAdapter(BasePlatformAdapter):
    """Home Depot Media Network RMN Adapter - Home improvement, Pro Xtra B2B"""
    
    def __init__(self):
        super().__init__(
            platform_name='homedepot-media',
            input_stream='stream:mco:event:action',
            output_stream='stream:mco:event:outcome',
            consumer_group='adapter-homedepot-media',
            rate_limit_per_hour=1200
        )
        logger.info("Home Depot Media Network Adapter initialized")
    
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
            elif operation == 'setProXtraTargeting':
                result = await self._set_proxtra_targeting(params)
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
            logger.error(f"Home Depot action failed: {operation} - {e}")
            return ActionOutcome(
                action_id=action.get('id', 'unknown'),
                status='failure',
                platform_id=entity_id,
                api_latency_ms=latency_ms,
                error={'code': 'HOMEDEPOT_ERROR', 'message': str(e), 'operation': operation}
            )
    
    async def _set_campaign_budget(self, params: Dict[str, Any]) -> Dict[str, Any]:
        campaign_id = params['campaignId']
        budget = params['dailyBudget']
        logger.info(f"Setting Home Depot campaign budget: {campaign_id} = {budget}")
        await asyncio.sleep(0.05)
        return {'platform_id': campaign_id, 'metadata': {'previousBudget': budget * 0.89}}
    
    async def _set_keyword_bid(self, params: Dict[str, Any]) -> Dict[str, Any]:
        keyword_id = params['keywordId']
        bid = params['bid']
        logger.info(f"Setting Home Depot keyword bid: {keyword_id} = {bid}")
        await asyncio.sleep(0.04)
        return {'platform_id': keyword_id, 'metadata': {'adGroupId': params['adGroupId']}}
    
    async def _set_product_bid(self, params: Dict[str, Any]) -> Dict[str, Any]:
        product_id = params['productId']
        bid = params['bid']
        logger.info(f"Setting Home Depot product bid: {product_id} = {bid}")
        await asyncio.sleep(0.04)
        return {'platform_id': product_id, 'metadata': {'productCategory': 'HOME_IMPROVEMENT'}}
    
    async def _update_audience_targeting(self, params: Dict[str, Any]) -> Dict[str, Any]:
        campaign_id = params['campaignId']
        audiences = params['audiences']
        logger.info(f"Updating Home Depot audiences: {campaign_id} ({len(audiences)} segments)")
        await asyncio.sleep(0.06)
        has_proxtra = any('PRO_XTRA' in a.get('audienceType', '') for a in audiences)
        return {'platform_id': campaign_id, 'metadata': {'hasProXtra': has_proxtra, 'totalAudiences': len(audiences)}}
    
    async def _pause_campaign(self, params: Dict[str, Any]) -> Dict[str, Any]:
        campaign_id = params['campaignId']
        logger.info(f"Pausing Home Depot campaign: {campaign_id}")
        await asyncio.sleep(0.03)
        return {'platform_id': campaign_id, 'metadata': {'newStatus': 'PAUSED'}}
    
    async def _add_negative_keyword(self, params: Dict[str, Any]) -> Dict[str, Any]:
        entity_id = params['id']
        keyword = params['keyword']
        logger.info(f"Adding Home Depot negative keyword: {keyword}")
        await asyncio.sleep(0.03)
        return {'platform_id': entity_id, 'metadata': {'keyword': keyword}}
    
    async def _set_geotargeting(self, params: Dict[str, Any]) -> Dict[str, Any]:
        campaign_id = params['campaignId']
        locations = params['locations']
        logger.info(f"Updating Home Depot geotargeting: {campaign_id} ({len(locations)} locations)")
        await asyncio.sleep(0.05)
        return {'platform_id': campaign_id, 'metadata': {'locationsCount': len(locations)}}
    
    async def _update_creative(self, params: Dict[str, Any]) -> Dict[str, Any]:
        ad_id = params['adId']
        logger.info(f"Updating Home Depot creative: {ad_id}")
        await asyncio.sleep(0.04)
        return {'platform_id': ad_id, 'metadata': {'approvalStatus': 'PENDING_REVIEW', 'vertical': 'HOME_IMPROVEMENT'}}
    
    async def _set_proxtra_targeting(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Set Pro Xtra B2B targeting (contractors, professionals)"""
        campaign_id = params.get('campaignId', 'unknown')
        pro_segment = params.get('proSegment', 'GENERAL_PRO')
        logger.info(f"Setting Home Depot Pro Xtra targeting: {campaign_id} - {pro_segment}")
        await asyncio.sleep(0.04)
        return {
            'platform_id': campaign_id,
            'metadata': {
                'proSegment': pro_segment,
                'vertical': 'HOME_IMPROVEMENT',
                'b2bTargeting': True
            }
        }


if __name__ == '__main__':
    adapter = HomeDepotMediaAdapter()
    asyncio.run(adapter.start())
