-- ============================================================================
-- Workflow Templates for Supabase
-- Based on Real CrewAI Agents (54+ agents)
-- ============================================================================

-- Clear existing templates (optional - remove if you want to keep existing)
-- TRUNCATE TABLE workflow_templates;

-- ============================================================================
-- 1. FORECASTING & DEMAND ANALYSIS TEMPLATES
-- ============================================================================

INSERT INTO workflow_templates (name, description, domain, template_schema)
VALUES 
(
  'Demand Forecasting Workflow',
  'Comprehensive demand forecasting with historical analysis, scenarios, and risk assessment. Ideal for product forecasting, sales predictions, and capacity planning.',
  'supply_chain',
  '{
    "agents": ["fqa", "sda", "ssa", "ira"],
    "steps": [
      {
        "agent": "fqa",
        "action": "generate_forecast",
        "description": "Generate demand forecast with confidence intervals",
        "output": "forecast_data"
      },
      {
        "agent": "sda",
        "action": "retrieve_historical_data",
        "description": "Query historical sales and demand data",
        "output": "historical_data"
      },
      {
        "agent": "ssa",
        "action": "run_scenarios",
        "description": "Simulate optimistic, baseline, and pessimistic scenarios",
        "output": "scenario_analysis"
      },
      {
        "agent": "ira",
        "action": "assess_inventory_risk",
        "description": "Calculate stockout and overstock probabilities",
        "output": "risk_assessment"
      }
    ],
    "parallel_execution": true,
    "timeout_ms": 30000,
    "keywords": ["forecast", "demand", "prediction", "sales forecast", "future", "trend", "projection"]
  }'::jsonb
),
(
  'Quick Forecast Q&A',
  'Fast forecasting for quick questions about future demand or trends',
  'analytics',
  '{
    "agents": ["fqa", "asa"],
    "steps": [
      {"agent": "fqa", "action": "answer_forecast_question", "output": "forecast_answer"},
      {"agent": "asa", "action": "synthesize_answer", "output": "final_answer"}
    ],
    "parallel_execution": false,
    "timeout_ms": 15000,
    "keywords": ["what", "when", "how much", "forecast", "expect", "will be"]
  }'::jsonb
);

-- ============================================================================
-- 2. MARKETING & CAMPAIGN OPTIMIZATION TEMPLATES
-- ============================================================================

INSERT INTO workflow_templates (name, description, domain, template_schema)
VALUES
(
  'Marketing Budget Optimization',
  'Optimize marketing budget allocation across channels with ROI analysis and elasticity calculations',
  'marketing',
  '{
    "agents": ["marketing-plan", "budget", "elasticity-uplift", "google-ads", "meta-ads"],
    "steps": [
      {"agent": "marketing-plan", "action": "analyze_campaign_brief", "description": "Convert campaign brief to executable plan"},
      {"agent": "budget", "action": "optimize_allocation", "description": "Optimize budget across channels"},
      {"agent": "elasticity-uplift", "action": "calculate_roi", "description": "Estimate incremental impact and ROI"},
      {"agent": "google-ads", "action": "get_platform_metrics", "description": "Get Google Ads performance data"},
      {"agent": "meta-ads", "action": "get_platform_metrics", "description": "Get Meta Ads performance data"}
    ],
    "parallel_execution": true,
    "timeout_ms": 40000,
    "keywords": ["marketing", "budget", "campaign", "advertising", "ads", "ROI", "spend", "allocation"]
  }'::jsonb
),
(
  'Campaign Performance Analysis',
  'Analyze marketing campaign performance with causal attribution and recommendations',
  'marketing',
  '{
    "agents": ["campaign-sku-mapper", "caa", "elasticity-uplift", "asa"],
    "steps": [
      {"agent": "campaign-sku-mapper", "action": "map_campaigns_to_skus", "description": "Map campaigns to affected products"},
      {"agent": "caa", "action": "attribution_analysis", "description": "Perform causal attribution analysis"},
      {"agent": "elasticity-uplift", "action": "calculate_uplift", "description": "Calculate promotional uplift"},
      {"agent": "asa", "action": "synthesize_insights", "description": "Synthesize actionable insights"}
    ],
    "parallel_execution": false,
    "timeout_ms": 35000,
    "keywords": ["campaign", "performance", "attribution", "impact", "why", "results", "effectiveness"]
  }'::jsonb
),
(
  'Multi-Platform Advertising Analysis',
  'Compare performance across Google, Meta, TikTok, LinkedIn, and other platforms',
  'marketing',
  '{
    "agents": ["google-ads", "meta-ads", "tiktok-ads", "linkedin-ads", "budget", "asa"],
    "steps": [
      {"agent": "google-ads", "action": "get_metrics", "description": "Get Google Ads metrics"},
      {"agent": "meta-ads", "action": "get_metrics", "description": "Get Meta Ads metrics"},
      {"agent": "tiktok-ads", "action": "get_metrics", "description": "Get TikTok Ads metrics"},
      {"agent": "linkedin-ads", "action": "get_metrics", "description": "Get LinkedIn Ads metrics"},
      {"agent": "budget", "action": "compare_roi", "description": "Compare ROI across platforms"},
      {"agent": "asa", "action": "synthesize_comparison", "description": "Synthesize platform comparison"}
    ],
    "parallel_execution": true,
    "timeout_ms": 45000,
    "keywords": ["platforms", "compare", "cross-channel", "multi-platform", "which platform", "best channel"]
  }'::jsonb
);

-- ============================================================================
-- 3. INVENTORY & SUPPLY CHAIN TEMPLATES
-- ============================================================================

INSERT INTO workflow_templates (name, description, domain, template_schema)
VALUES
(
  'Inventory Optimization Workflow',
  'Optimize inventory levels with risk assessment, capacity planning, and replenishment recommendations',
  'supply_chain',
  '{
    "agents": ["inventory-position", "ira", "capacity-leadtime", "opt", "asa"],
    "steps": [
      {"agent": "inventory-position", "action": "check_current_inventory", "description": "Get current inventory positions"},
      {"agent": "ira", "action": "assess_risks", "description": "Assess stockout and overstock risks"},
      {"agent": "capacity-leadtime", "action": "check_capacity", "description": "Check production capacity and lead times"},
      {"agent": "opt", "action": "optimize_inventory", "description": "Calculate optimal inventory levels"},
      {"agent": "asa", "action": "synthesize_recommendations", "description": "Synthesize actionable recommendations"}
    ],
    "parallel_execution": false,
    "timeout_ms": 35000,
    "keywords": ["inventory", "stock", "replenishment", "reorder", "stockout", "overstock", "optimal"]
  }'::jsonb
),
(
  'Supply Chain Planning Workflow',
  'End-to-end supply chain planning with production scheduling, procurement, and logistics',
  'supply_chain',
  '{
    "agents": ["supply-planning", "production-scheduling", "procurement", "logistics-allocation", "atp-ctp"],
    "steps": [
      {"agent": "supply-planning", "action": "create_supply_plan", "description": "Generate supply plan"},
      {"agent": "production-scheduling", "action": "schedule_production", "description": "Optimize production schedule"},
      {"agent": "procurement", "action": "plan_procurement", "description": "Plan procurement activities"},
      {"agent": "logistics-allocation", "action": "optimize_logistics", "description": "Optimize logistics and allocation"},
      {"agent": "atp-ctp", "action": "calculate_promise", "description": "Calculate ATP/CTP dates"}
    ],
    "parallel_execution": false,
    "timeout_ms": 50000,
    "keywords": ["supply chain", "planning", "production", "procurement", "logistics", "S&OP", "available to promise"]
  }'::jsonb
);

-- ============================================================================
-- 4. SCENARIO ANALYSIS & WHAT-IF TEMPLATES
-- ============================================================================

INSERT INTO workflow_templates (name, description, domain, template_schema)
VALUES
(
  'What-If Scenario Analysis',
  'Run comprehensive what-if scenarios with risk assessment and optimization',
  'analytics',
  '{
    "agents": ["ssa", "ira", "opt", "risk-digital-twin", "asa"],
    "steps": [
      {"agent": "ssa", "action": "setup_scenarios", "description": "Set up simulation scenarios"},
      {"agent": "ira", "action": "assess_inventory_impact", "description": "Assess inventory implications"},
      {"agent": "opt", "action": "optimize_under_scenarios", "description": "Find optimal actions for each scenario"},
      {"agent": "risk-digital-twin", "action": "run_digital_twin", "description": "Simulate in digital twin environment"},
      {"agent": "asa", "action": "synthesize_scenarios", "description": "Compare and recommend best scenario"}
    ],
    "parallel_execution": true,
    "timeout_ms": 40000,
    "keywords": ["what if", "scenario", "simulation", "if we", "what happens", "simulate", "test"]
  }'::jsonb
),
(
  'Pricing Impact Analysis',
  'Analyze impact of price changes on demand, revenue, and inventory',
  'pricing',
  '{
    "agents": ["elasticity-uplift", "ssa", "ira", "price-promo-guardrail", "asa"],
    "steps": [
      {"agent": "elasticity-uplift", "action": "calculate_price_elasticity", "description": "Calculate price elasticity"},
      {"agent": "ssa", "action": "simulate_price_scenarios", "description": "Simulate different price points"},
      {"agent": "ira", "action": "assess_inventory_impact", "description": "Assess inventory implications"},
      {"agent": "price-promo-guardrail", "action": "check_guardrails", "description": "Check pricing guardrails and margins"},
      {"agent": "asa", "action": "synthesize_pricing_recommendation", "description": "Synthesize pricing recommendation"}
    ],
    "parallel_execution": false,
    "timeout_ms": 35000,
    "keywords": ["price", "pricing", "discount", "promotion", "promo", "elasticity", "margin"]
  }'::jsonb
);

-- ============================================================================
-- 5. DATA ANALYSIS & INSIGHTS TEMPLATES
-- ============================================================================

INSERT INTO workflow_templates (name, description, domain, template_schema)
VALUES
(
  'General Data Analysis',
  'General-purpose data analysis with semantic search and causal attribution',
  'analytics',
  '{
    "agents": ["sda", "caa", "asa"],
    "steps": [
      {"agent": "sda", "action": "retrieve_data", "description": "Query and retrieve relevant data"},
      {"agent": "caa", "action": "analyze_causality", "description": "Perform causal analysis"},
      {"agent": "asa", "action": "synthesize_insights", "description": "Synthesize actionable insights"}
    ],
    "parallel_execution": false,
    "timeout_ms": 25000,
    "keywords": ["analyze", "why", "cause", "reason", "data", "insights", "understanding"]
  }'::jsonb
),
(
  'Root Cause Analysis',
  'Identify root causes of KPI degradation or anomalies',
  'analytics',
  '{
    "agents": ["rca-change-detective", "sda", "caa", "data-gap-mapping", "asa"],
    "steps": [
      {"agent": "rca-change-detective", "action": "detect_changes", "description": "Detect changes and anomalies"},
      {"agent": "sda", "action": "query_related_data", "description": "Query related metrics and data"},
      {"agent": "caa", "action": "causal_inference", "description": "Perform causal inference"},
      {"agent": "data-gap-mapping", "action": "identify_data_gaps", "description": "Identify any data gaps"},
      {"agent": "asa", "action": "synthesize_root_cause", "description": "Synthesize root cause findings"}
    ],
    "parallel_execution": false,
    "timeout_ms": 40000,
    "keywords": ["why dropped", "why increased", "root cause", "problem", "issue", "degradation", "anomaly"]
  }'::jsonb
);

-- ============================================================================
-- 6. SALES & REVENUE TEMPLATES
-- ============================================================================

INSERT INTO workflow_templates (name, description, domain, template_schema)
VALUES
(
  'Sales Pipeline Forecasting',
  'Forecast sales pipeline with conversion analysis and revenue predictions',
  'sales',
  '{
    "agents": ["sales-pipeline", "fqa", "caa", "asa"],
    "steps": [
      {"agent": "sales-pipeline", "action": "analyze_pipeline", "description": "Analyze current sales pipeline"},
      {"agent": "fqa", "action": "forecast_revenue", "description": "Forecast expected revenue"},
      {"agent": "caa", "action": "analyze_conversion_factors", "description": "Analyze conversion factors"},
      {"agent": "asa", "action": "synthesize_forecast", "description": "Synthesize sales forecast"}
    ],
    "parallel_execution": true,
    "timeout_ms": 30000,
    "keywords": ["sales", "pipeline", "revenue", "bookings", "close rate", "conversion", "deals"]
  }'::jsonb
),
(
  'Revenue Optimization',
  'Optimize revenue through pricing, promotions, and channel mix',
  'sales',
  '{
    "agents": ["elasticity-uplift", "price-promo-guardrail", "budget", "opt", "asa"],
    "steps": [
      {"agent": "elasticity-uplift", "action": "analyze_revenue_drivers", "description": "Analyze revenue drivers"},
      {"agent": "price-promo-guardrail", "action": "evaluate_pricing_options", "description": "Evaluate pricing options"},
      {"agent": "budget", "action": "optimize_channel_mix", "description": "Optimize channel budget allocation"},
      {"agent": "opt", "action": "optimize_revenue", "description": "Find optimal revenue strategy"},
      {"agent": "asa", "action": "synthesize_recommendations", "description": "Synthesize revenue recommendations"}
    ],
    "parallel_execution": false,
    "timeout_ms": 35000,
    "keywords": ["revenue", "optimize", "increase sales", "maximize", "grow revenue", "profitability"]
  }'::jsonb
);

-- ============================================================================
-- 7. RETAIL MEDIA NETWORK (RMN) TEMPLATES
-- ============================================================================

INSERT INTO workflow_templates (name, description, domain, template_schema)
VALUES
(
  'Amazon RMN Campaign Optimization',
  'Optimize Amazon Advertising campaigns with sponsored products and DSP',
  'rmn',
  '{
    "agents": ["amazon-rmn", "budget", "elasticity-uplift", "asa"],
    "steps": [
      {"agent": "amazon-rmn", "action": "analyze_amazon_campaigns", "description": "Analyze Amazon campaign performance"},
      {"agent": "budget", "action": "optimize_amazon_budget", "description": "Optimize Amazon advertising budget"},
      {"agent": "elasticity-uplift", "action": "calculate_amazon_roi", "description": "Calculate ROI and incremental sales"},
      {"agent": "asa", "action": "synthesize_recommendations", "description": "Synthesize Amazon optimization recommendations"}
    ],
    "parallel_execution": true,
    "timeout_ms": 30000,
    "keywords": ["amazon", "sponsored products", "DSP", "amazon ads", "amazon advertising"]
  }'::jsonb
),
(
  'Walmart Connect Campaign Analysis',
  'Analyze and optimize Walmart Connect advertising campaigns',
  'rmn',
  '{
    "agents": ["walmart-rmn", "budget", "campaign-sku-mapper", "asa"],
    "steps": [
      {"agent": "walmart-rmn", "action": "analyze_walmart_campaigns", "description": "Analyze Walmart Connect campaigns"},
      {"agent": "budget", "action": "optimize_walmart_budget", "description": "Optimize Walmart advertising budget"},
      {"agent": "campaign-sku-mapper", "action": "map_walmart_skus", "description": "Map campaigns to Walmart SKUs"},
      {"agent": "asa", "action": "synthesize_insights", "description": "Synthesize Walmart insights"}
    ],
    "parallel_execution": true,
    "timeout_ms": 30000,
    "keywords": ["walmart", "walmart connect", "walmart ads", "walmart advertising"]
  }'::jsonb
),
(
  'Multi-Retailer RMN Comparison',
  'Compare performance across Amazon, Walmart, Target, and Instacart retail media',
  'rmn',
  '{
    "agents": ["amazon-rmn", "walmart-rmn", "target-rmn", "instacart-rmn", "budget", "asa"],
    "steps": [
      {"agent": "amazon-rmn", "action": "get_amazon_metrics", "description": "Get Amazon metrics"},
      {"agent": "walmart-rmn", "action": "get_walmart_metrics", "description": "Get Walmart metrics"},
      {"agent": "target-rmn", "action": "get_target_metrics", "description": "Get Target metrics"},
      {"agent": "instacart-rmn", "action": "get_instacart_metrics", "description": "Get Instacart metrics"},
      {"agent": "budget", "action": "compare_rmn_roi", "description": "Compare ROI across retailers"},
      {"agent": "asa", "action": "synthesize_rmn_comparison", "description": "Synthesize retailer comparison"}
    ],
    "parallel_execution": true,
    "timeout_ms": 45000,
    "keywords": ["retail media", "RMN", "compare retailers", "which retailer", "amazon vs walmart"]
  }'::jsonb
);

-- ============================================================================
-- 8. GOVERNANCE & POLICY TEMPLATES
-- ============================================================================

INSERT INTO workflow_templates (name, description, domain, template_schema)
VALUES
(
  'Policy Compliance Check',
  'Check compliance with business policies and guardrails',
  'governance',
  '{
    "agents": ["price-promo-guardrail", "guardrail-compliance", "constraint-broadcast", "asa"],
    "steps": [
      {"agent": "price-promo-guardrail", "action": "check_pricing_policies", "description": "Check pricing and promo policies"},
      {"agent": "guardrail-compliance", "action": "check_all_guardrails", "description": "Check all business guardrails"},
      {"agent": "constraint-broadcast", "action": "check_constraints", "description": "Check supply and capacity constraints"},
      {"agent": "asa", "action": "synthesize_compliance_report", "description": "Synthesize compliance report"}
    ],
    "parallel_execution": true,
    "timeout_ms": 25000,
    "keywords": ["compliance", "policy", "guardrails", "rules", "allowed", "permitted", "constraints"]
  }'::jsonb
),
(
  'Policy Creation & Negotiation',
  'Conversationally create new policies and negotiate S&OP plans',
  'governance',
  '{
    "agents": ["policy-elicitation", "sop-orchestrator", "constraint-broadcast", "asa"],
    "steps": [
      {"agent": "policy-elicitation", "action": "elicit_policy_requirements", "description": "Elicit policy requirements"},
      {"agent": "sop-orchestrator", "action": "coordinate_sop", "description": "Coordinate S&OP process"},
      {"agent": "constraint-broadcast", "action": "broadcast_new_policies", "description": "Broadcast new policies"},
      {"agent": "asa", "action": "synthesize_policy_plan", "description": "Synthesize policy implementation plan"}
    ],
    "parallel_execution": false,
    "timeout_ms": 35000,
    "keywords": ["create policy", "new rule", "negotiate", "S&OP", "agreement", "consensus"]
  }'::jsonb
);

-- ============================================================================
-- 9. MCO (MARKETING CAMPAIGN OPTIMIZATION) TEMPLATES
-- ============================================================================

INSERT INTO workflow_templates (name, description, domain, template_schema)
VALUES
(
  'End-to-End Campaign Optimization',
  'Complete MCO pipeline from ingress to bid optimization',
  'mco',
  '{
    "agents": ["ingress-normalization", "feature-forecast", "attribution-causal", "budget", "bid-target-setter", "creative-ops"],
    "steps": [
      {"agent": "ingress-normalization", "action": "ingest_normalize_data", "description": "Ingest and normalize campaign data"},
      {"agent": "feature-forecast", "action": "feature_engineering", "description": "Perform feature engineering"},
      {"agent": "attribution-causal", "action": "attribution_analysis", "description": "Perform attribution analysis"},
      {"agent": "budget", "action": "optimize_budget", "description": "Optimize budget allocation"},
      {"agent": "bid-target-setter", "action": "set_optimal_bids", "description": "Set optimal bids and targets"},
      {"agent": "creative-ops", "action": "select_creatives", "description": "Select best-performing creatives"}
    ],
    "parallel_execution": false,
    "timeout_ms": 50000,
    "keywords": ["MCO", "campaign optimization", "bid", "creative", "full optimization"]
  }'::jsonb
),
(
  'Campaign Opportunity Scanning',
  'Scan for optimization opportunities and anomalies in campaigns',
  'mco',
  '{
    "agents": ["opportunity-scanner", "rca-change-detective", "budget", "asa"],
    "steps": [
      {"agent": "opportunity-scanner", "action": "scan_opportunities", "description": "Scan for optimization opportunities"},
      {"agent": "rca-change-detective", "action": "detect_anomalies", "description": "Detect anomalies and changes"},
      {"agent": "budget", "action": "quantify_opportunities", "description": "Quantify opportunity value"},
      {"agent": "asa", "action": "prioritize_opportunities", "description": "Prioritize and recommend actions"}
    ],
    "parallel_execution": true,
    "timeout_ms": 30000,
    "keywords": ["opportunities", "optimize", "improve", "find issues", "anomalies", "underperforming"]
  }'::jsonb
);

-- ============================================================================
-- 10. QUICK ANSWER TEMPLATES (SIMPLE QUERIES)
-- ============================================================================

INSERT INTO workflow_templates (name, description, domain, template_schema)
VALUES
(
  'Quick Question Answering',
  'Fast answer to simple questions using specialized Q&A agents',
  'general',
  '{
    "agents": ["fqa", "asa"],
    "steps": [
      {"agent": "fqa", "action": "answer_question", "description": "Answer the question directly"},
      {"agent": "asa", "action": "format_answer", "description": "Format the final answer"}
    ],
    "parallel_execution": false,
    "timeout_ms": 10000,
    "keywords": ["what", "how", "when", "where", "who", "quick", "simple"]
  }'::jsonb
),
(
  'Data Retrieval Query',
  'Simple data retrieval and synthesis',
  'general',
  '{
    "agents": ["sda", "asa"],
    "steps": [
      {"agent": "sda", "action": "query_data", "description": "Query requested data"},
      {"agent": "asa", "action": "synthesize_response", "description": "Synthesize response"}
    ],
    "parallel_execution": false,
    "timeout_ms": 10000,
    "keywords": ["show me", "get", "retrieve", "find", "look up", "data"]
  }'::jsonb
);

-- ============================================================================
-- Verify templates were inserted
-- ============================================================================

SELECT 
  name, 
  domain, 
  jsonb_array_length(template_schema->'agents') as agent_count,
  created_at
FROM workflow_templates
ORDER BY created_at DESC;

-- ============================================================================
-- USAGE EXAMPLES
-- ============================================================================

/*
-- Example 1: Find templates for forecasting
SELECT name, description, template_schema->'agents' as agents
FROM workflow_templates
WHERE template_schema->>'keywords' LIKE '%forecast%'
   OR name LIKE '%Forecast%';

-- Example 2: Get template by domain
SELECT name, description, template_schema->'agents' as agents
FROM workflow_templates
WHERE domain = 'marketing';

-- Example 3: Find templates with specific agent
SELECT name, description
FROM workflow_templates
WHERE template_schema->'agents' @> '["fqa"]'::jsonb;
*/

