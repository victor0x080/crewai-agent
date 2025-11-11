"""
Register All CrewAI Agents
Registers platform, product, and brand agents with PythonAgentSyncBridge
"""
import sys
sys.path.append('..')
from platform_agents import (
    google_ads_agent,
    meta_ads_agent,
    tiktok_ads_agent,
    linkedin_ads_agent,
    pinterest_ads_agent,
    snapchat_ads_agent
)
from product_agents import (
    nike_air_max_270_agent,
    coca_cola_zero_agent,
    airpods_pro_agent,
    tide_pods_agent,
    lululemon_align_agent
)
from brand_agents import (
    nike_brand_agent,
    coca_cola_brand_agent,
    apple_brand_agent
)


# ============================================================================
# Agent Registry
# ============================================================================

ALL_AGENTS = {
    # Platform Agents (6)
    'platform': {
        'google_ads': google_ads_agent,
        'meta_ads': meta_ads_agent,
        'tiktok_ads': tiktok_ads_agent,
        'linkedin_ads': linkedin_ads_agent,
        'pinterest_ads': pinterest_ads_agent,
        'snapchat_ads': snapchat_ads_agent
    },
    
    # Product Agents (5)
    'product': {
        'nike_air_max_270': nike_air_max_270_agent,
        'coca_cola_zero': coca_cola_zero_agent,
        'airpods_pro': airpods_pro_agent,
        'tide_pods': tide_pods_agent,
        'lululemon_align': lululemon_align_agent
    },
    
    # Brand Agents (3)
    'brand': {
        'nike': nike_brand_agent,
        'coca_cola': coca_cola_brand_agent,
        'apple': apple_brand_agent
    }
}


def print_agent_summary():
    """Print summary of all agents"""
    print("=" * 80)
    print("CREWAI AGENT REGISTRY")
    print("=" * 80)
    
    total_agents = sum(len(agents) for agents in ALL_AGENTS.values())
    print(f"\nTotal Agents: {total_agents}\n")
    
    for category, agents in ALL_AGENTS.items():
        print(f"{category.upper()} AGENTS ({len(agents)}):")
        for agent_id, agent in agents.items():
            print(f"  - {agent_id}: {agent.role}")
        print()
    
    print("=" * 80)
    print("CAPABILITIES MAPPING")
    print("=" * 80)
    
    # Platform agents
    print("\nPLATFORM AGENTS:")
    print("  google_ads: ['advertising', 'search_ads', 'display_ads', 'video_ads', 'shopping_ads', 'google_platform']")
    print("  meta_ads: ['advertising', 'social_media', 'facebook_ads', 'instagram_ads', 'meta_platform']")
    print("  tiktok_ads: ['advertising', 'social_media', 'video_ads', 'short_form_video', 'tiktok_platform']")
    print("  linkedin_ads: ['advertising', 'social_media', 'b2b_marketing', 'professional_network', 'linkedin_platform']")
    print("  pinterest_ads: ['advertising', 'social_media', 'visual_discovery', 'shopping_intent', 'pinterest_platform']")
    print("  snapchat_ads: ['advertising', 'social_media', 'ar_ads', 'vertical_video', 'snapchat_platform']")
    
    # Product agents
    print("\nPRODUCT AGENTS:")
    print("  nike_air_max_270: ['product_management', 'athletic_footwear', 'pricing', 'inventory', 'nike']")
    print("  coca_cola_zero: ['product_management', 'beverages', 'pricing', 'distribution', 'coca_cola']")
    print("  airpods_pro: ['product_management', 'consumer_electronics', 'audio', 'premium', 'apple']")
    print("  tide_pods: ['product_management', 'household_goods', 'laundry', 'pricing', 'procter_gamble']")
    print("  lululemon_align: ['product_management', 'apparel', 'activewear', 'premium', 'lululemon']")
    
    # Brand agents
    print("\nBRAND AGENTS:")
    print("  nike: ['brand_strategy', 'portfolio_optimization', 'athletic', 'premium', 'global']")
    print("  coca_cola: ['brand_strategy', 'portfolio_optimization', 'beverages', 'mass_market', 'global']")
    print("  apple: ['brand_strategy', 'ecosystem', 'consumer_electronics', 'premium', 'global']")
    
    print("\n" + "=" * 80)


def register_with_sync_bridge():
    """
    Register agents with PythonAgentSyncBridge
    This would normally call the sync bridge to register agents in the database
    """
    print("\nREGISTRATION INSTRUCTIONS:")
    print("=" * 80)
    print("\nTo register these agents with the database, run:")
    print("\n  python src/services/agent-sync/PythonAgentSyncBridge.py")
    print("\nThis will:")
    print("  1. Discover all CrewAI agents")
    print("  2. Extract role, goal, backstory, tools, capabilities")
    print("  3. Create agent_ontology_profiles")
    print("  4. Map capabilities to ontology concepts")
    print("  5. Insert into agent_registry table")
    print("\nOr use the API endpoint:")
    print("\n  curl -X POST http://localhost:3000/api/agents/sync")
    print("\n" + "=" * 80)


if __name__ == '__main__':
    print_agent_summary()
    register_with_sync_bridge()
