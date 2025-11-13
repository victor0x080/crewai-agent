"""
DV360 (Display & Video 360) Platform Adapter
Implements all 5 DV360 operations from ActionContract
"""
import asyncio
import logging
import time
from typing import Dict, Any
from adapters.base_platform_adapter import BasePlatformAdapter, ActionOutcome

logger = logging.getLogger(__name__)


class DV360Adapter(BasePlatformAdapter):
    """
    DV360 Platform Adapter
    Operations: setInsertionOrderBudget, setLineItemPacing, pauseLineItem, updateBidStrategy, linkCreative
    """
    
    def __init__(self):
        super().__init__(
            platform_name='dv360',
            input_stream='stream:mco:event:action',
            output_stream='stream:mco:event:outcome',
            consumer_group='adapter-dv360',
            rate_limit_per_hour=1000
        )
        logger.info("DV360 Adapter initialized")

    async def execute_action(self, action: Dict[str, Any]) -> ActionOutcome:
        """Execute DV360-specific action"""
        operation = action.get('operation')
        params = action.get('params', {})
        target = action.get('target', {})
        action_id = target.get('entityId', 'unknown')
        
        logger.info(f"Executing DV360 operation: {operation} for action {action_id}")
        
        start_time = time.time()
        
        try:
            if operation == 'setInsertionOrderBudget':
                result = await self._set_insertion_order_budget(params)
            elif operation == 'setLineItemPacing':
                result = await self._set_line_item_pacing(params)
            elif operation == 'pauseLineItem':
                result = await self._pause_line_item(params)
            elif operation == 'updateBidStrategy':
                result = await self._update_bid_strategy(params)
            elif operation == 'linkCreative':
                result = await self._link_creative(params)
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
            logger.error(f"DV360 operation {operation} failed: {e}")
            return ActionOutcome(
                action_id=action_id,
                status='failure',
                error_message=str(e),
                api_latency_ms=api_latency_ms
            )

    async def _set_insertion_order_budget(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Set insertion order budget"""
        io_id = params.get('insertionOrderId')
        start_date = params.get('startDate')
        end_date = params.get('endDate')
        budget = params.get('budget')
        currency = params.get('currency')
        
        logger.info(f"Setting budget for IO {io_id}: {budget} {currency} ({start_date} to {end_date})")
        
        await asyncio.sleep(0.1)  # Simulate API call
        
        return {
            'platform_id': io_id,
            'operation_id': f'op-{int(time.time())}',
            'status': 'ACTIVE',
            'budget': budget,
            'currency': currency
        }

    async def _set_line_item_pacing(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Set line item pacing"""
        line_item_id = params.get('lineItemId')
        pacing_type = params.get('pacingType')
        daily_budget = params.get('dailyBudget')
        currency = params.get('currency')
        
        logger.info(f"Setting pacing for line item {line_item_id}: {pacing_type}, {daily_budget} {currency}/day")
        
        await asyncio.sleep(0.1)
        
        return {
            'platform_id': line_item_id,
            'operation_id': f'op-{int(time.time())}',
            'status': 'ACTIVE',
            'pacing_type': pacing_type,
            'daily_budget': daily_budget
        }

    async def _pause_line_item(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Pause line item"""
        line_item_id = params.get('lineItemId')
        
        logger.info(f"Pausing line item {line_item_id}")
        
        await asyncio.sleep(0.1)
        
        return {
            'platform_id': line_item_id,
            'operation_id': f'op-{int(time.time())}',
            'status': 'PAUSED'
        }

    async def _update_bid_strategy(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update bid strategy"""
        line_item_id = params.get('lineItemId')
        strategy_type = params.get('strategyType')
        target_cpa = params.get('targetCpa')
        currency = params.get('currency')
        
        logger.info(f"Updating bid strategy for line item {line_item_id}: {strategy_type}")
        
        await asyncio.sleep(0.1)
        
        return {
            'platform_id': line_item_id,
            'operation_id': f'op-{int(time.time())}',
            'status': 'ACTIVE',
            'strategy_type': strategy_type,
            'target_cpa': target_cpa
        }

    async def _link_creative(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Link creative to line item"""
        line_item_id = params.get('lineItemId')
        creative_id = params.get('creativeId')
        
        logger.info(f"Linking creative {creative_id} to line item {line_item_id}")
        
        await asyncio.sleep(0.1)
        
        return {
            'platform_id': line_item_id,
            'operation_id': f'op-{int(time.time())}',
            'status': 'ACTIVE',
            'creative_id': creative_id
        }


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    adapter = DV360Adapter()
    
    try:
        asyncio.run(adapter.start())
    except KeyboardInterrupt:
        logger.info("Shutting down DV360 adapter...")
        asyncio.run(adapter.stop())
