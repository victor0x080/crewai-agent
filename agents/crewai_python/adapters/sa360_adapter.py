"""
SA360 (Search Ads 360) Platform Adapter
Implements all 5 SA360 operations from ActionContract
"""
import asyncio
import logging
import time
from typing import Dict, Any
from adapters.base_platform_adapter import BasePlatformAdapter, ActionOutcome

logger = logging.getLogger(__name__)


class SA360Adapter(BasePlatformAdapter):
    """
    SA360 Platform Adapter
    Operations: setCampaignBudget, setAdGroupCpc, setTargetROAS, pauseCampaign, addNegativeKeyword
    """
    
    def __init__(self):
        super().__init__(
            platform_name='sa360',
            input_stream='stream:mco:event:action',
            output_stream='stream:mco:event:outcome',
            consumer_group='adapter-sa360',
            rate_limit_per_hour=1000
        )
        
        # SA360 API client would be initialized here
        # For now, we'll simulate API calls
        logger.info("SA360 Adapter initialized")

    async def execute_action(self, action: Dict[str, Any]) -> ActionOutcome:
        """
        Execute SA360-specific action
        
        Args:
            action: Action payload with operation and params
            
        Returns:
            ActionOutcome
        """
        operation = action.get('operation')
        params = action.get('params', {})
        target = action.get('target', {})
        action_id = target.get('entityId', 'unknown')
        
        logger.info(f"Executing SA360 operation: {operation} for action {action_id}")
        
        start_time = time.time()
        
        try:
            if operation == 'setCampaignBudget':
                result = await self._set_campaign_budget(params)
            elif operation == 'setAdGroupCpc':
                result = await self._set_adgroup_cpc(params)
            elif operation == 'setTargetROAS':
                result = await self._set_target_roas(params)
            elif operation == 'pauseCampaign':
                result = await self._pause_campaign(params)
            elif operation == 'addNegativeKeyword':
                result = await self._add_negative_keyword(params)
            else:
                return ActionOutcome(
                    action_id=action_id,
                    status='failure',
                    error_message=f"Unknown operation: {operation}"
                )
            
            api_latency_ms = int((time.time() - start_time) * 1000)
            
            return ActionOutcome(
                action_id=action_id,
                status='success',
                platform_id=result.get('platform_id'),
                api_latency_ms=api_latency_ms
            )
            
        except Exception as e:
            api_latency_ms = int((time.time() - start_time) * 1000)
            logger.error(f"SA360 operation {operation} failed: {e}")
            return ActionOutcome(
                action_id=action_id,
                status='failure',
                error_message=str(e),
                api_latency_ms=api_latency_ms
            )

    async def _set_campaign_budget(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Set campaign budget
        
        Params:
            campaignId: str
            amount: number
            currency: str (ISO-4217)
        """
        campaign_id = params.get('campaignId')
        amount = params.get('amount')
        currency = params.get('currency')
        
        logger.info(f"Setting budget for campaign {campaign_id}: {amount} {currency}")
        
        # Simulate SA360 API call
        await asyncio.sleep(0.1)  # Simulate network latency
        
        # In production, this would be:
        # response = await sa360_client.campaigns.update_budget(
        #     campaign_id=campaign_id,
        #     daily_budget=amount,
        #     currency=currency
        # )
        
        # Simulated successful response
        return {
            'platform_id': campaign_id,
            'operation_id': f'op-{int(time.time())}',
            'status': 'ACTIVE',
            'budget_amount': amount,
            'currency': currency
        }

    async def _set_adgroup_cpc(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Set ad group CPC bid
        
        Params:
            adGroupId: str
            cpc: number
            currency: str (ISO-4217)
        """
        adgroup_id = params.get('adGroupId')
        cpc = params.get('cpc')
        currency = params.get('currency')
        
        logger.info(f"Setting CPC for ad group {adgroup_id}: {cpc} {currency}")
        
        # Simulate SA360 API call
        await asyncio.sleep(0.1)
        
        # In production:
        # response = await sa360_client.adgroups.update_cpc(
        #     adgroup_id=adgroup_id,
        #     max_cpc=cpc,
        #     currency=currency
        # )
        
        return {
            'platform_id': adgroup_id,
            'operation_id': f'op-{int(time.time())}',
            'status': 'ACTIVE',
            'cpc': cpc,
            'currency': currency
        }

    async def _set_target_roas(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Set target ROAS for campaign
        
        Params:
            campaignId: str
            targetROAS: number (0.1 - 20.0)
        """
        campaign_id = params.get('campaignId')
        target_roas = params.get('targetROAS')
        
        logger.info(f"Setting target ROAS for campaign {campaign_id}: {target_roas}")
        
        # Validate ROAS range
        if not (0.1 <= target_roas <= 20.0):
            raise ValueError(f"Target ROAS {target_roas} out of range (0.1-20.0)")
        
        # Simulate SA360 API call
        await asyncio.sleep(0.1)
        
        # In production:
        # response = await sa360_client.campaigns.update_bidding_strategy(
        #     campaign_id=campaign_id,
        #     strategy_type='TARGET_ROAS',
        #     target_roas=target_roas
        # )
        
        return {
            'platform_id': campaign_id,
            'operation_id': f'op-{int(time.time())}',
            'status': 'ACTIVE',
            'target_roas': target_roas,
            'bidding_strategy': 'TARGET_ROAS'
        }

    async def _pause_campaign(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Pause campaign
        
        Params:
            campaignId: str
        """
        campaign_id = params.get('campaignId')
        
        logger.info(f"Pausing campaign {campaign_id}")
        
        # Simulate SA360 API call
        await asyncio.sleep(0.1)
        
        # In production:
        # response = await sa360_client.campaigns.update_status(
        #     campaign_id=campaign_id,
        #     status='PAUSED'
        # )
        
        return {
            'platform_id': campaign_id,
            'operation_id': f'op-{int(time.time())}',
            'status': 'PAUSED'
        }

    async def _add_negative_keyword(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add negative keyword
        
        Params:
            scope: str ('campaign' | 'adGroup')
            id: str (campaignId or adGroupId)
            keyword: str
            matchType: str ('BROAD' | 'PHRASE' | 'EXACT')
        """
        scope = params.get('scope')
        scope_id = params.get('id')
        keyword = params.get('keyword')
        match_type = params.get('matchType')
        
        logger.info(f"Adding negative keyword '{keyword}' ({match_type}) to {scope} {scope_id}")
        
        # Validate match type
        valid_match_types = ['BROAD', 'PHRASE', 'EXACT']
        if match_type not in valid_match_types:
            raise ValueError(f"Invalid match type: {match_type}. Must be one of {valid_match_types}")
        
        # Simulate SA360 API call
        await asyncio.sleep(0.1)
        
        # In production:
        # if scope == 'campaign':
        #     response = await sa360_client.campaigns.add_negative_keyword(
        #         campaign_id=scope_id,
        #         keyword=keyword,
        #         match_type=match_type
        #     )
        # else:
        #     response = await sa360_client.adgroups.add_negative_keyword(
        #         adgroup_id=scope_id,
        #         keyword=keyword,
        #         match_type=match_type
        #     )
        
        return {
            'platform_id': scope_id,
            'operation_id': f'op-{int(time.time())}',
            'status': 'ACTIVE',
            'keyword': keyword,
            'match_type': match_type,
            'scope': scope
        }


# Main entry point for testing
if __name__ == '__main__':
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    adapter = SA360Adapter()
    
    try:
        asyncio.run(adapter.start())
    except KeyboardInterrupt:
        logger.info("Shutting down SA360 adapter...")
        asyncio.run(adapter.stop())
