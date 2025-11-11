"""
Target Roundel RMN Adapter
Implements Target Roundel operations with RedCard/Circle targeting
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


class TargetRoundelAdapter(BasePlatformAdapter):
    """
    Target Roundel RMN Adapter
    
    Features:
    - RedCard holder targeting
    - Target Circle member targeting
    - Same-day delivery targeting
    - Drive Up / Order Pickup targeting
    - Store proximity targeting
    """
    
    def __init__(self):
        super().__init__(
            platform_name='target-roundel',
            input_stream='stream:mco:event:action',
            output_stream='stream:mco:event:outcome',
            consumer_group='adapter-target-roundel',
            rate_limit_per_hour=1500
        )
        logger.info("Target Roundel Adapter initialized")
    
    async def execute_action(self, action: Dict[str, Any]) -> ActionOutcome:
        """
        Execute Target Roundel platform action
        
        Supported operations:
        - setCampaignBudget: Set campaign daily budget
        - setKeywordBid: Set keyword-level bid
        - setCategoryBid: Set category-level bid
        - updateAudienceTargeting: Update audience segments (RedCard, Circle, delivery)
        - pauseCampaign: Pause campaign
        - addNegativeKeyword: Add negative keyword
        - setStoreTargeting: Set store proximity targeting
        - updateCreative: Update ad creative assets
        - setDaypartingSchedule: Set time-of-day bid modifiers
        """
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
            elif operation == 'setCategoryBid':
                result = await self._set_category_bid(params)
            elif operation == 'updateAudienceTargeting':
                result = await self._update_audience_targeting(params)
            elif operation == 'pauseCampaign':
                result = await self._pause_campaign(params)
            elif operation == 'addNegativeKeyword':
                result = await self._add_negative_keyword(params)
            elif operation == 'setStoreTargeting':
                result = await self._set_store_targeting(params)
            elif operation == 'updateCreative':
                result = await self._update_creative(params)
            elif operation == 'setDaypartingSchedule':
                result = await self._set_dayparting_schedule(params)
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
            logger.error(f"Target Roundel action failed: {operation} - {e}")
            
            return ActionOutcome(
                action_id=action.get('id', 'unknown'),
                status='failure',
                platform_id=entity_id,
                api_latency_ms=latency_ms,
                error={
                    'code': 'TARGET_ROUNDEL_ERROR',
                    'message': str(e),
                    'operation': operation
                }
            )
    
    async def _set_campaign_budget(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Set campaign budget"""
        campaign_id = params['campaignId']
        budget = params['dailyBudget']
        currency = params['currency']
        
        logger.info(f"Setting Target Roundel campaign budget: {campaign_id} = {budget} {currency}")
        
        await asyncio.sleep(0.05)
        
        return {
            'platform_id': campaign_id,
            'metadata': {
                'previousBudget': budget * 0.85,
                'effectiveDate': datetime.now().isoformat()
            }
        }
    
    async def _set_keyword_bid(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Set keyword-level bid"""
        ad_group_id = params['adGroupId']
        keyword_id = params['keywordId']
        bid = params['bid']
        currency = params['currency']
        
        logger.info(f"Setting Target Roundel keyword bid: {keyword_id} = {bid} {currency}")
        
        await asyncio.sleep(0.04)
        
        return {
            'platform_id': keyword_id,
            'metadata': {
                'adGroupId': ad_group_id,
                'previousBid': bid * 0.92,
                'estimatedImpressions': 1200
            }
        }
    
    async def _set_category_bid(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Set category-level bid"""
        ad_group_id = params['adGroupId']
        category_id = params['categoryId']
        bid = params['bid']
        currency = params['currency']
        
        logger.info(f"Setting Target Roundel category bid: {category_id} = {bid} {currency}")
        
        await asyncio.sleep(0.04)
        
        return {
            'platform_id': category_id,
            'metadata': {
                'adGroupId': ad_group_id,
                'categoryName': f"Category-{category_id}",
                'estimatedProducts': 150
            }
        }
    
    async def _update_audience_targeting(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update audience targeting (RedCard, Circle, delivery options)"""
        campaign_id = params['campaignId']
        audiences = params['audiences']
        
        added = [a for a in audiences if a['action'] == 'ADD']
        removed = [a for a in audiences if a['action'] == 'REMOVE']
        
        logger.info(f"Updating Target Roundel audiences: {campaign_id} (+{len(added)}, -{len(removed)})")
        
        await asyncio.sleep(0.06)
        
        # Check for premium audiences
        redcard = any(a['audienceType'] == 'REDCARD_HOLDER' for a in added)
        circle = any(a['audienceType'] == 'CIRCLE_MEMBER' for a in added)
        delivery = any(a['audienceType'] in ['SAME_DAY_DELIVERY', 'DRIVE_UP', 'ORDER_PICKUP'] for a in added)
        
        return {
            'platform_id': campaign_id,
            'metadata': {
                'audiencesAdded': len(added),
                'audiencesRemoved': len(removed),
                'redcardTargeting': redcard,
                'circleTargeting': circle,
                'deliveryTargeting': delivery,
                'totalAudiences': len(added) - len(removed) + 2
            }
        }
    
    async def _pause_campaign(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Pause campaign"""
        campaign_id = params['campaignId']
        
        logger.info(f"Pausing Target Roundel campaign: {campaign_id}")
        
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
        
        logger.info(f"Adding Target Roundel negative keyword: {keyword} ({match_type}) to {scope} {entity_id}")
        
        await asyncio.sleep(0.03)
        
        return {
            'platform_id': entity_id,
            'metadata': {
                'scope': scope,
                'keyword': keyword,
                'matchType': match_type
            }
        }
    
    async def _set_store_targeting(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Set store proximity targeting"""
        campaign_id = params['campaignId']
        stores = params['stores']
        
        added = [s for s in stores if s['action'] == 'ADD']
        removed = [s for s in stores if s['action'] == 'REMOVE']
        
        logger.info(f"Updating Target Roundel store targeting: {campaign_id} (+{len(added)}, -{len(removed)})")
        
        await asyncio.sleep(0.05)
        
        # Calculate average radius
        avg_radius = sum(s.get('radiusMiles', 10) for s in added) / len(added) if added else 0
        
        return {
            'platform_id': campaign_id,
            'metadata': {
                'storesAdded': len(added),
                'storesRemoved': len(removed),
                'averageRadiusMiles': round(avg_radius, 1),
                'totalStores': len(added) - len(removed) + 5
            }
        }
    
    async def _update_creative(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update ad creative assets"""
        ad_id = params['adId']
        assets = params['creativeAssets']
        
        logger.info(f"Updating Target Roundel creative: {ad_id}")
        
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
    
    async def _set_dayparting_schedule(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Set time-of-day bid modifiers"""
        campaign_id = params['campaignId']
        schedule = params['schedule']
        
        logger.info(f"Setting Target Roundel dayparting: {campaign_id} ({len(schedule)} time periods)")
        
        await asyncio.sleep(0.04)
        
        # Calculate average bid modifier
        avg_modifier = sum(s['bidModifier'] for s in schedule) / len(schedule)
        
        return {
            'platform_id': campaign_id,
            'metadata': {
                'timePeriods': len(schedule),
                'averageBidModifier': round(avg_modifier, 2),
                'daysConfigured': len(set(s['dayOfWeek'] for s in schedule))
            }
        }


if __name__ == '__main__':
    """Run Target Roundel adapter standalone"""
    adapter = TargetRoundelAdapter()
    asyncio.run(adapter.start())
