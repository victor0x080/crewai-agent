"""
Register All CrewAI Agents
Registers platform, product, and brand agents with PythonAgentSyncBridge
and creates ontology profiles for agent discovery
"""
import sys
import os
import requests
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

# Supabase configuration
SUPABASE_URL = os.getenv('SUPABASE_URL', 'http://localhost:54321')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', 'your-supabase-key')


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


def create_ontology_profiles():
    """Create ontology profiles for all agents to enable ontology-based discovery."""
    print("\n🔗 Creating ontology profiles for agent discovery...")
    
    # Map agent capabilities/interests to ontology concepts
    # Based on agent roles, goals, and capabilities
    profiles = [
        # Platform Agents
        {
            "agent_id": "google_ads",
            "interests_concepts_must": ["ex:Campaign", "ex:Channel", "ex:Google"],
            "interests_concepts_any": ["ex:Advertising", "ex:SearchAds", "ex:DisplayAds", "ex:VideoAds"],
            "tools": ["resolve_concept", "expand_concepts", "map_enum"]
        },
        {
            "agent_id": "meta_ads",
            "interests_concepts_must": ["ex:Campaign", "ex:Channel", "ex:Meta"],
            "interests_concepts_any": ["ex:Advertising", "ex:SocialMedia", "ex:FacebookAds", "ex:InstagramAds"],
            "tools": ["resolve_concept", "expand_concepts", "map_enum"]
        },
        {
            "agent_id": "tiktok_ads",
            "interests_concepts_must": ["ex:Campaign", "ex:Channel", "ex:TikTok"],
            "interests_concepts_any": ["ex:Advertising", "ex:SocialMedia", "ex:VideoAds", "ex:ShortFormVideo"],
            "tools": ["resolve_concept", "expand_concepts", "map_enum"]
        },
        {
            "agent_id": "linkedin_ads",
            "interests_concepts_must": ["ex:Campaign", "ex:Channel", "ex:LinkedIn"],
            "interests_concepts_any": ["ex:Advertising", "ex:SocialMedia", "ex:B2BMarketing", "ex:ProfessionalNetwork"],
            "tools": ["resolve_concept", "expand_concepts", "map_enum"]
        },
        {
            "agent_id": "pinterest_ads",
            "interests_concepts_must": ["ex:Campaign", "ex:Channel", "ex:Pinterest"],
            "interests_concepts_any": ["ex:Advertising", "ex:SocialMedia", "ex:VisualDiscovery", "ex:ShoppingIntent"],
            "tools": ["resolve_concept", "expand_concepts", "map_enum"]
        },
        {
            "agent_id": "snapchat_ads",
            "interests_concepts_must": ["ex:Campaign", "ex:Channel", "ex:Snapchat"],
            "interests_concepts_any": ["ex:Advertising", "ex:SocialMedia", "ex:ARAds", "ex:VerticalVideo"],
            "tools": ["resolve_concept", "expand_concepts", "map_enum"]
        },
        # Product Agents
        {
            "agent_id": "nike_air_max_270",
            "interests_concepts_must": ["ex:Product", "ex:Pricing", "ex:Inventory"],
            "interests_concepts_any": ["ex:ProductManagement", "ex:AthleticFootwear", "ex:Nike", "ex:SKU"],
            "tools": ["resolve_concept", "expand_concepts", "map_enum", "get_category_constraints"]
        },
        {
            "agent_id": "coca_cola_zero",
            "interests_concepts_must": ["ex:Product", "ex:Pricing", "ex:Category/Beverages"],
            "interests_concepts_any": ["ex:ProductManagement", "ex:SoftDrinks", "ex:Distribution", "ex:CocaCola"],
            "tools": ["resolve_concept", "expand_concepts", "map_enum", "get_category_constraints"]
        },
        {
            "agent_id": "airpods_pro",
            "interests_concepts_must": ["ex:Product", "ex:Pricing", "ex:ConsumerElectronics"],
            "interests_concepts_any": ["ex:ProductManagement", "ex:Audio", "ex:Premium", "ex:Apple"],
            "tools": ["resolve_concept", "expand_concepts", "map_enum", "get_category_constraints"]
        },
        {
            "agent_id": "tide_pods",
            "interests_concepts_must": ["ex:Product", "ex:Pricing", "ex:HouseholdGoods"],
            "interests_concepts_any": ["ex:ProductManagement", "ex:Laundry", "ex:ProcterGamble"],
            "tools": ["resolve_concept", "expand_concepts", "map_enum", "get_category_constraints"]
        },
        {
            "agent_id": "lululemon_align",
            "interests_concepts_must": ["ex:Product", "ex:Pricing", "ex:Apparel"],
            "interests_concepts_any": ["ex:ProductManagement", "ex:Activewear", "ex:Premium", "ex:Lululemon"],
            "tools": ["resolve_concept", "expand_concepts", "map_enum", "get_category_constraints"]
        },
        # Brand Agents
        {
            "agent_id": "nike",
            "interests_concepts_must": ["ex:Brand", "ex:PortfolioOptimization"],
            "interests_concepts_any": ["ex:BrandStrategy", "ex:Athletic", "ex:Premium", "ex:Global"],
            "tools": ["resolve_concept", "expand_concepts", "map_enum"]
        },
        {
            "agent_id": "coca_cola",
            "interests_concepts_must": ["ex:Brand", "ex:PortfolioOptimization", "ex:Category/Beverages"],
            "interests_concepts_any": ["ex:BrandStrategy", "ex:MassMarket", "ex:Global"],
            "tools": ["resolve_concept", "expand_concepts", "map_enum"]
        },
        {
            "agent_id": "apple",
            "interests_concepts_must": ["ex:Brand", "ex:PortfolioOptimization", "ex:ConsumerElectronics"],
            "interests_concepts_any": ["ex:BrandStrategy", "ex:Ecosystem", "ex:Premium", "ex:Global"],
            "tools": ["resolve_concept", "expand_concepts", "map_enum"]
        }
    ]
    
    success_count = 0
    error_count = 0
    
    for profile in profiles:
        try:
            response = requests.post(
                f'{SUPABASE_URL}/rest/v1/agent_ontology_profiles',
                headers={
                    'apikey': SUPABASE_KEY,
                    'Authorization': f'Bearer {SUPABASE_KEY}',
                    'Content-Type': 'application/json',
                    'Prefer': 'resolution=merge-duplicates'
                },
                json=profile,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                print(f"  ✅ Registered: {profile['agent_id']}")
                success_count += 1
            else:
                print(f"  ❌ Failed: {profile['agent_id']} - {response.status_code}: {response.text}")
                error_count += 1
        except Exception as e:
            print(f"  ❌ Error registering {profile['agent_id']}: {str(e)}")
            error_count += 1
    
    print(f"\n📊 Summary: {success_count} succeeded, {error_count} failed")
    return success_count, error_count


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
    
    # Register ontology profiles for agent discovery
    print("\n" + "=" * 80)
    print("ONTOLOGY PROFILE REGISTRATION")
    print("=" * 80)
    create_ontology_profiles()
    
    register_with_sync_bridge()
