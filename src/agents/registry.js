/**
 * Agent Registry
 * Definitions for all 55 CrewAI Python agents in the IMS system
 */

export const agentRegistry = [
  // ==========================================
  // 1. SKILL AGENTS (7)
  // ==========================================
  {
    id: 'sda',
    name: 'Semantic Data Agent',
    role: 'Query structured and unstructured data sources using semantic search',
    capabilities: ['semantic_search', 'data_retrieval', 'vector_query'],
    tools: ['vector_search', 'sql_query', 'api_call'],
    category: 'skill'
  },
  {
    id: 'fqa',
    name: 'Forecast Q&A Agent',
    role: 'Answer forecasting questions and provide demand predictions',
    capabilities: ['forecasting', 'demand_prediction', 'qa'],
    tools: ['time_series_query', 'forecast_model', 'statistical_analysis'],
    category: 'skill'
  },
  {
    id: 'caa',
    name: 'Causal & Attribution Agent',
    role: 'Perform causal analysis and marketing attribution',
    capabilities: ['causal_analysis', 'attribution', 'impact_analysis'],
    tools: ['regression_analysis', 'attribution_model', 'impact_calculator'],
    category: 'skill'
  },
  {
    id: 'ssa',
    name: 'Scenario Simulator Agent',
    role: 'Run what-if scenarios and simulations',
    capabilities: ['scenario_simulation', 'monte_carlo', 'sensitivity_analysis'],
    tools: ['simulation_engine', 'parameter_sweep', 'risk_calculator'],
    category: 'skill'
  },
  {
    id: 'ira',
    name: 'Inventory Risk Agent',
    role: 'Assess inventory risks, stockouts, and overstocks',
    capabilities: ['risk_assessment', 'inventory_analysis', 'stockout_prediction'],
    tools: ['inventory_query', 'risk_model', 'demand_forecast'],
    category: 'skill'
  },
  {
    id: 'opt',
    name: 'Optimizer Agent',
    role: 'Solve optimization problems (pricing, inventory, budget allocation)',
    capabilities: ['optimization', 'constraint_solving', 'linear_programming'],
    tools: ['optimizer_solver', 'constraint_checker', 'objective_function'],
    category: 'skill'
  },
  {
    id: 'asa',
    name: 'Answer Synthesis Agent',
    role: 'Synthesize insights from multiple agents into coherent answers',
    capabilities: ['answer_synthesis', 'insight_aggregation', 'response_generation'],
    tools: ['text_synthesis', 'result_aggregation', 'confidence_weighting'],
    category: 'skill'
  },

  // ==========================================
  // 2. DEMAND-GEN AGENTS (4)
  // ==========================================
  {
    id: 'marketing-plan',
    name: 'Marketing Plan Agent',
    role: 'Convert marketing campaign briefs to machine-readable intent',
    capabilities: ['campaign_planning', 'budget_allocation', 'channel_selection'],
    tools: ['campaign_optimizer', 'channel_mix', 'budget_planner'],
    category: 'demand-gen'
  },
  {
    id: 'sales-pipeline',
    name: 'Sales Pipeline Agent',
    role: 'Forecast sales pipeline and expected bookings',
    capabilities: ['pipeline_forecasting', 'conversion_prediction', 'revenue_forecast'],
    tools: ['crm_integration', 'pipeline_model', 'conversion_analysis'],
    category: 'demand-gen'
  },
  {
    id: 'elasticity-uplift',
    name: 'Elasticity & Uplift Agent',
    role: 'Calculate price elasticity and promotional uplift',
    capabilities: ['price_elasticity', 'promo_uplift', 'demand_modeling'],
    tools: ['elasticity_calculator', 'uplift_model', 'demand_curve'],
    category: 'demand-gen'
  },
  {
    id: 'campaign-sku-mapper',
    name: 'Campaign→SKU Mapper Agent',
    role: 'Map marketing campaigns to affected SKUs',
    capabilities: ['campaign_mapping', 'sku_impact', 'attribution'],
    tools: ['taxonomy_mapper', 'sku_lookup', 'impact_tracker'],
    category: 'demand-gen'
  },

  // ==========================================
  // 3. S&OP / DEMAND-SATISFACTION AGENTS (7)
  // ==========================================
  {
    id: 'inventory-position',
    name: 'Inventory Position Agent',
    role: 'Track current inventory levels and positions',
    capabilities: ['inventory_tracking', 'stock_monitoring', 'position_analysis'],
    tools: ['wms_integration', 'inventory_query', 'stock_calculator'],
    category: 'supply'
  },
  {
    id: 'capacity-leadtime',
    name: 'Capacity & Lead-Time Agent',
    role: 'Assess production capacity and lead times',
    capabilities: ['capacity_planning', 'leadtime_analysis', 'bottleneck_detection'],
    tools: ['capacity_model', 'leadtime_calculator', 'production_data'],
    category: 'supply'
  },
  {
    id: 'supply-planning',
    name: 'Supply Planning Agent',
    role: 'Plan supply chain operations and procurement',
    capabilities: ['supply_planning', 'procurement_optimization', 'vendor_selection'],
    tools: ['supply_optimizer', 'vendor_db', 'procurement_model'],
    category: 'supply'
  },
  {
    id: 'production-scheduling',
    name: 'Production Scheduling Agent',
    role: 'Optimize production schedules and resource allocation',
    capabilities: ['production_scheduling', 'resource_allocation', 'constraint_optimization'],
    tools: ['scheduler', 'resource_planner', 'constraint_solver'],
    category: 'supply'
  },
  {
    id: 'procurement',
    name: 'Procurement Agent',
    role: 'Manage procurement decisions and supplier relationships',
    capabilities: ['procurement_planning', 'supplier_evaluation', 'cost_optimization'],
    tools: ['supplier_db', 'cost_analyzer', 'procurement_optimizer'],
    category: 'supply'
  },
  {
    id: 'logistics-allocation',
    name: 'Logistics & Allocation Agent',
    role: 'Optimize logistics and inventory allocation across locations',
    capabilities: ['logistics_optimization', 'allocation', 'routing'],
    tools: ['logistics_optimizer', 'allocation_model', 'routing_engine'],
    category: 'supply'
  },
  {
    id: 'atp-ctp',
    name: 'ATP/CTP Agent',
    role: 'Calculate Available-to-Promise and Capable-to-Promise',
    capabilities: ['atp_calculation', 'ctp_calculation', 'promise_validation'],
    tools: ['atp_engine', 'ctp_engine', 'inventory_check'],
    category: 'supply'
  },

  // ==========================================
  // 4. GOVERNANCE AGENTS (5)
  // ==========================================
  {
    id: 'constraint-broadcast',
    name: 'Constraint Broadcast Agent',
    role: 'Broadcast supply constraints to demand-gen teams',
    capabilities: ['constraint_management', 'guardrail_enforcement', 'policy_broadcast'],
    tools: ['constraint_db', 'policy_validator', 'broadcast_channel'],
    category: 'governance'
  },
  {
    id: 'price-promo-guardrail',
    name: 'Price/Promo Guardrail Agent',
    role: 'Enforce pricing and promotional guardrails (ATP, margin)',
    capabilities: ['price_validation', 'promo_compliance', 'margin_check'],
    tools: ['pricing_rules', 'margin_calculator', 'compliance_checker'],
    category: 'governance'
  },
  {
    id: 'policy-elicitation',
    name: 'Policy Elicitation & S&OP Negotiator Agent',
    role: 'Conversationally build policies and negotiate S&OP plans',
    capabilities: ['policy_creation', 'negotiation', 'consensus_building'],
    tools: ['policy_builder', 'negotiation_protocol', 'consensus_tracker'],
    category: 'governance'
  },
  {
    id: 'data-gap-mapping',
    name: 'Data Gap & Mapping Agent',
    role: 'Identify data gaps and create ID/enum crosswalks',
    capabilities: ['data_mapping', 'gap_identification', 'schema_alignment'],
    tools: ['schema_mapper', 'gap_analyzer', 'crosswalk_generator'],
    category: 'governance'
  },
  {
    id: 'rca-change-detective',
    name: 'RCA / Change Detective Agent',
    role: 'Root cause analysis for KPI degradation',
    capabilities: ['root_cause_analysis', 'anomaly_detection', 'change_detection'],
    tools: ['rca_engine', 'anomaly_detector', 'change_tracker'],
    category: 'governance'
  },

  // ==========================================
  // 5. MCO CORE PIPELINE AGENTS (11)
  // ==========================================
  {
    id: 'ingress-normalization',
    name: 'Ingress & Normalization Agent',
    role: 'Ingest and normalize data from multiple sources',
    capabilities: ['data_ingestion', 'normalization', 'schema_mapping'],
    tools: ['data_ingester', 'normalizer', 'schema_validator'],
    category: 'mco'
  },
  {
    id: 'catalog-schema',
    name: 'Catalog & Schema Agent',
    role: 'Manage product catalog and data schemas',
    capabilities: ['catalog_management', 'schema_validation', 'taxonomy'],
    tools: ['catalog_db', 'schema_validator', 'taxonomy_manager'],
    category: 'mco'
  },
  {
    id: 'feature-forecast',
    name: 'Feature & Forecast Agent',
    role: 'Feature engineering and demand forecasting',
    capabilities: ['feature_engineering', 'forecasting', 'ml_modeling'],
    tools: ['feature_builder', 'forecast_model', 'ml_pipeline'],
    category: 'mco'
  },
  {
    id: 'attribution-causal',
    name: 'Attribution & Causal Agent',
    role: 'Marketing attribution and causal impact analysis',
    capabilities: ['attribution', 'causal_inference', 'incrementality'],
    tools: ['attribution_model', 'causal_engine', 'incrementality_test'],
    category: 'mco'
  },
  {
    id: 'opportunity-scanner',
    name: 'Opportunity Scanner Agent',
    role: 'Identify optimization opportunities and anomalies',
    capabilities: ['opportunity_detection', 'anomaly_detection', 'optimization_recommendation'],
    tools: ['scanner', 'anomaly_detector', 'opportunity_ranker'],
    category: 'mco'
  },
  {
    id: 'cost-finance-mapper',
    name: 'Cost & Finance Mapper Agent',
    role: 'Map costs to financial categories and budgets',
    capabilities: ['cost_mapping', 'budget_tracking', 'financial_allocation'],
    tools: ['cost_mapper', 'budget_tracker', 'gl_integrator'],
    category: 'mco'
  },
  {
    id: 'budget-optimizer',
    name: 'Budget Optimizer Agent',
    role: 'Optimize budget allocation across channels and campaigns',
    capabilities: ['budget_optimization', 'allocation', 'roi_maximization'],
    tools: ['budget_optimizer', 'allocation_engine', 'roi_calculator'],
    category: 'mco'
  },
  {
    id: 'bid-target-setter',
    name: 'Bid & Target Setter Agent',
    role: 'Set optimal bids and performance targets',
    capabilities: ['bid_optimization', 'target_setting', 'pacing'],
    tools: ['bid_optimizer', 'target_calculator', 'pacing_engine'],
    category: 'mco'
  },
  {
    id: 'creative-ops',
    name: 'Creative Ops Agent',
    role: 'Manage creative assets and performance tracking',
    capabilities: ['creative_management', 'asset_tracking', 'performance_analysis'],
    tools: ['asset_db', 'creative_analyzer', 'performance_tracker'],
    category: 'mco'
  },
  {
    id: 'platform-adapter',
    name: 'Platform Adapter Agent',
    role: 'Adapt workflows to different advertising platforms',
    capabilities: ['platform_adaptation', 'api_integration', 'format_conversion'],
    tools: ['platform_api', 'format_converter', 'credential_manager'],
    category: 'mco'
  },
  {
    id: 'question-router-planner',
    name: 'Question Router & Planner Agent',
    role: 'Route questions and plan multi-step workflows',
    capabilities: ['question_routing', 'workflow_planning', 'decomposition'],
    tools: ['router', 'planner', 'dag_builder'],
    category: 'mco'
  },

  // ==========================================
  // 6. INTEROP/CONSENSUS AGENTS (3)
  // ==========================================
  {
    id: 'forecast-fusion',
    name: 'Forecast Fusion Agent',
    role: 'Fuse forecasts from multiple sources into consensus',
    capabilities: ['forecast_fusion', 'ensemble', 'consensus_building'],
    tools: ['fusion_engine', 'ensemble_model', 'consensus_calculator'],
    category: 'interop'
  },
  {
    id: 'sop-orchestrator',
    name: 'S&OP Orchestrator Agent',
    role: 'Orchestrate Sales & Operations Planning processes',
    capabilities: ['sop_orchestration', 'cross_functional_planning', 'consensus'],
    tools: ['sop_planner', 'consensus_engine', 'plan_validator'],
    category: 'interop'
  },
  {
    id: 'risk-digital-twin',
    name: 'Risk & Digital Twin Agent',
    role: 'Maintain digital twin model and assess risks',
    capabilities: ['digital_twin', 'risk_modeling', 'scenario_testing'],
    tools: ['twin_engine', 'risk_simulator', 'scenario_tester'],
    category: 'interop'
  },

  // ==========================================
  // 7. RMN (RETAIL MEDIA NETWORK) AGENTS (4)
  // ==========================================
  {
    id: 'amazon-rmn',
    name: 'Amazon RMN Specialist',
    role: 'Optimize Amazon Advertising campaigns',
    capabilities: ['amazon_ads', 'sponsored_products', 'dsp_optimization'],
    tools: ['amazon_api', 'sponsored_ads_optimizer', 'dsp_manager'],
    category: 'rmn'
  },
  {
    id: 'walmart-rmn',
    name: 'Walmart Connect Specialist',
    role: 'Optimize Walmart Connect advertising',
    capabilities: ['walmart_connect', 'sponsored_search', 'display_ads'],
    tools: ['walmart_api', 'connect_optimizer', 'attribution_tracker'],
    category: 'rmn'
  },
  {
    id: 'target-rmn',
    name: 'Target Roundel Specialist',
    role: 'Optimize Target Roundel campaigns',
    capabilities: ['target_roundel', 'retail_media', 'audience_targeting'],
    tools: ['roundel_api', 'audience_builder', 'campaign_manager'],
    category: 'rmn'
  },
  {
    id: 'instacart-rmn',
    name: 'Instacart Ads Specialist',
    role: 'Optimize Instacart Ads campaigns',
    capabilities: ['instacart_ads', 'sponsored_listings', 'shoppable_ads'],
    tools: ['instacart_api', 'listing_optimizer', 'shoppable_manager'],
    category: 'rmn'
  },

  // ==========================================
  // 8. PLATFORM AGENTS (6)
  // ==========================================
  {
    id: 'google-ads',
    name: 'Google Ads Agent',
    role: 'Optimize Google Ads campaigns',
    capabilities: ['google_ads', 'search_ads', 'display_network'],
    tools: ['google_ads_api', 'keyword_planner', 'bid_optimizer'],
    category: 'platform'
  },
  {
    id: 'meta-ads',
    name: 'Meta Ads Agent',
    role: 'Optimize Facebook and Instagram advertising',
    capabilities: ['meta_ads', 'facebook_ads', 'instagram_ads'],
    tools: ['meta_api', 'audience_network', 'creative_optimizer'],
    category: 'platform'
  },
  {
    id: 'tiktok-ads',
    name: 'TikTok Ads Agent',
    role: 'Optimize TikTok advertising campaigns',
    capabilities: ['tiktok_ads', 'short_form_video', 'influencer_marketing'],
    tools: ['tiktok_api', 'video_optimizer', 'influencer_matcher'],
    category: 'platform'
  },
  {
    id: 'linkedin-ads',
    name: 'LinkedIn Ads Agent',
    role: 'Optimize LinkedIn B2B advertising',
    capabilities: ['linkedin_ads', 'b2b_targeting', 'lead_gen'],
    tools: ['linkedin_api', 'b2b_optimizer', 'lead_scorer'],
    category: 'platform'
  },
  {
    id: 'pinterest-ads',
    name: 'Pinterest Ads Agent',
    role: 'Optimize Pinterest shopping and inspiration ads',
    capabilities: ['pinterest_ads', 'shopping_ads', 'visual_search'],
    tools: ['pinterest_api', 'visual_optimizer', 'catalog_sync'],
    category: 'platform'
  },
  {
    id: 'snapchat-ads',
    name: 'Snapchat Ads Agent',
    role: 'Optimize Snapchat AR and video campaigns',
    capabilities: ['snapchat_ads', 'ar_ads', 'gen_z_targeting'],
    tools: ['snapchat_api', 'ar_creator', 'audience_builder'],
    category: 'platform'
  },

  // ==========================================
  // 9. SEMANTIC/TRANSLATION AGENTS (3)
  // ==========================================
  {
    id: 'semantic-router',
    name: 'Semantic Router Agent',
    role: 'Route queries to appropriate agents using semantic understanding',
    capabilities: ['semantic_routing', 'agent_selection', 'capability_matching'],
    tools: ['vector_matcher', 'capability_index', 'router'],
    category: 'semantic'
  },
  {
    id: 'translator-contract',
    name: 'Translator Contract Agent',
    role: 'Translate between different data contracts and schemas',
    capabilities: ['schema_translation', 'contract_mapping', 'format_conversion'],
    tools: ['schema_mapper', 'contract_validator', 'format_converter'],
    category: 'semantic'
  },
  {
    id: 'validator-registry',
    name: 'Validator Registry Agent',
    role: 'Validate data against registered schemas and rules',
    capabilities: ['schema_validation', 'rule_validation', 'compliance_check'],
    tools: ['json_schema_validator', 'shacl_validator', 'rule_engine'],
    category: 'semantic'
  },

  // ==========================================
  // 10. ADDITIONAL DOMAIN AGENTS (16 more)
  // ==========================================
  {
    id: 'guardrail-compliance',
    name: 'Guardrail Compliance Agent',
    role: 'Ensure all actions comply with business guardrails',
    capabilities: ['compliance_check', 'guardrail_enforcement', 'policy_validation'],
    tools: ['guardrail_db', 'compliance_checker', 'policy_engine'],
    category: 'governance'
  },
  {
    id: 'safeguard-rollback',
    name: 'Safeguard Rollback Agent',
    role: 'Monitor execution and rollback on errors',
    capabilities: ['error_detection', 'rollback', 'recovery'],
    tools: ['monitor', 'rollback_engine', 'recovery_protocol'],
    category: 'governance'
  },
  {
    id: 'goal-policy-elicitation',
    name: 'Goal & Policy Elicitation Agent',
    role: 'Elicit business goals and policies through conversation',
    capabilities: ['goal_elicitation', 'policy_discovery', 'conversational_ui'],
    tools: ['dialogue_manager', 'goal_extractor', 'policy_builder'],
    category: 'governance'
  },
  {
    id: 'qrp-planner',
    name: 'QRP Planner Agent',
    role: 'Query-Response-Plan coordination',
    capabilities: ['query_planning', 'response_coordination', 'plan_execution'],
    tools: ['query_planner', 'response_builder', 'execution_coordinator'],
    category: 'planning'
  }
];

// Export utility functions
export function getAgentById(id) {
  return agentRegistry.find(a => a.id === id);
}

export function getAgentsByCategory(category) {
  return agentRegistry.filter(a => a.category === category);
}

export function getAgentsByCapability(capability) {
  return agentRegistry.filter(a => a.capabilities.includes(capability));
}

export function getAllAgentIds() {
  return agentRegistry.map(a => a.id);
}

export function getAgentCount() {
  return agentRegistry.length;
}

// Log registry info on import
console.log(`📦 Agent Registry loaded: ${agentRegistry.length} agents`);
console.log(`   Categories: ${new Set(agentRegistry.map(a => a.category)).size}`);
console.log(`   Skill: ${getAgentsByCategory('skill').length}`);
console.log(`   Demand-Gen: ${getAgentsByCategory('demand-gen').length}`);
console.log(`   Supply: ${getAgentsByCategory('supply').length}`);
console.log(`   Governance: ${getAgentsByCategory('governance').length}`);
console.log(`   MCO: ${getAgentsByCategory('mco').length}`);
console.log(`   RMN: ${getAgentsByCategory('rmn').length}`);
console.log(`   Platform: ${getAgentsByCategory('platform').length}`);

