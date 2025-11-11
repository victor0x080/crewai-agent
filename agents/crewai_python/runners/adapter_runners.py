"""
Platform Adapter Runners
Runs SA360, DV360, Amazon, TikTok adapters
"""
import sys
import asyncio
import logging

sys.path.append('..')
from adapters.sa360_adapter import SA360Adapter
from adapters.dv360_adapter import DV360Adapter
from adapters.amazon_adapter import AmazonAdapter
from adapters.tiktok_adapter import TikTokAdapter
from adapters.walmart_connect_adapter import WalmartConnectAdapter
from adapters.target_roundel_adapter import TargetRoundelAdapter
from adapters.kroger_precision_adapter import KrogerPrecisionAdapter
from adapters.albertsons_media_adapter import AlbertsonsMediaAdapter
from adapters.cvs_media_adapter import CVSMediaAdapter
from adapters.walgreens_ads_adapter import WalgreensAdsAdapter
from adapters.bestbuy_ads_adapter import BestBuyAdsAdapter
from adapters.homedepot_media_adapter import HomeDepotMediaAdapter

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Adapter registry
ADAPTERS = {
    # Platform Adapters (Phase 1)
    'sa360': SA360Adapter,
    'dv360': DV360Adapter,
    'amazon': AmazonAdapter,
    'tiktok': TikTokAdapter,
    # RMN Tier 1 Adapters (Phase 2)
    'walmart-connect': WalmartConnectAdapter,
    'target-roundel': TargetRoundelAdapter,
    # RMN Tier 2 Adapters (Phase 3)
    'kroger-precision': KrogerPrecisionAdapter,
    'albertsons-media': AlbertsonsMediaAdapter,
    'cvs-media': CVSMediaAdapter,
    'walgreens-ads': WalgreensAdsAdapter,
    'bestbuy-ads': BestBuyAdsAdapter,
    'homedepot-media': HomeDepotMediaAdapter
}


def run_adapter(adapter_name: str):
    """Run a specific adapter"""
    if adapter_name not in ADAPTERS:
        logger.error(f"Unknown adapter: {adapter_name}")
        logger.info(f"Available adapters: {', '.join(ADAPTERS.keys())}")
        sys.exit(1)
    
    adapter_class = ADAPTERS[adapter_name]
    adapter = adapter_class()
    
    logger.info(f"Starting {adapter_name} adapter...")
    
    try:
        asyncio.run(adapter.start())
    except KeyboardInterrupt:
        logger.info(f"Shutting down {adapter_name} adapter...")
        asyncio.run(adapter.stop())
    except Exception as e:
        logger.error(f"Error running {adapter_name} adapter: {e}")
        sys.exit(1)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python adapter_runners.py <adapter_name>")
        print(f"Available adapters: {', '.join(ADAPTERS.keys())}")
        sys.exit(1)
    
    adapter_name = sys.argv[1]
    run_adapter(adapter_name)
