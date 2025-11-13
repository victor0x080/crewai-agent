/**
 * UnifiedAgentDiscoveryService
 * - Discovers suitable agents from registry (semantic)
 * - Falls back to dynamic agent creation spec when confidence < threshold
 * - Uses OpenAI to generate agent specifications
 * - Integrates with Python CrewAI factory for agent creation
 */

import OpenAI from 'openai';
import config from '../config/index.js';
import { logger } from '../utils/logger.js';
import { agentRegistry } from '../agents/registry.js';

export default class UnifiedAgentDiscoveryService {
  constructor(options = {}) {
    this.threshold = options.threshold ?? 0.72;
    this.openai = null;
  }

  async initialize() {
    if (config.openai.enabled) {
      try {
        this.openai = new OpenAI({ apiKey: config.openai.apiKey });
        logger.info(`✅ UnifiedAgentDiscoveryService initialized with OpenAI (threshold=${this.threshold})`);
      } catch (error) {
        logger.warn('⚠️ OpenAI not available for dynamic agent generation', { error: error.message });
      }
    } else {
      logger.warn('⚠️ OpenAI not configured - dynamic agent generation will use fallback spec');
    }
  }

  /**
   * Discover agents and optionally create a dynamic agent spec
   * @param {string} query
   * @param {object} intent
   * @param {object} entities
   * @param {Array} workflowTemplates
   * @returns {Promise<{ discovered: Array, highConfidence: Array, dynamicAgentSpec?: object }>}
   */
  async discoverAndExecuteAgents(query, intent, entities, workflowTemplates = []) {
    const discovered = await this.semanticAgentDiscovery(query, intent, entities);
    const highConfidence = discovered.filter(a => a.confidence >= this.threshold);

    // Log confidence scores for debugging
    logger.info('📊 Agent discovery results', {
      query: query.substring(0, 100),
      threshold: this.threshold,
      discoveredCount: discovered.length,
      highConfidenceCount: highConfidence.length,
      topScores: discovered
        .sort((a, b) => b.confidence - a.confidence)
        .slice(0, 5)
        .map(a => ({ name: a.name, confidence: a.confidence.toFixed(3) }))
    });

    if (highConfidence.length > 0) {
      return { discovered, highConfidence };
    }

    logger.info('🔧 No suitable agents found above threshold – generating dynamic agent spec', {
      threshold: this.threshold,
      maxConfidence: discovered.length > 0 ? Math.max(...discovered.map(a => a.confidence)) : 0
    });
    const dynamicAgentSpec = await this.generateDynamicAgentConfig(query, intent, entities);
    return { discovered, highConfidence, dynamicAgentSpec };
  }

  /**
   * Calculate confidence score for agent matching query
   * Uses multi-factor scoring: keyword matching, intent alignment, capability matching, entity relevance
   * Returns confidence 0.0-1.0, where >= 0.72 indicates strong match
   */
  async semanticAgentDiscovery(query, intent, entities) {
    const queryLower = query.toLowerCase();
    const intentType = (intent?.intent || '').toLowerCase();
    const intentCategory = (intent?.category || '').toLowerCase();
    const entityValues = Object.values(entities || {}).map(v => String(v).toLowerCase());
    const entityKeys = Object.keys(entities || {}).map(k => k.toLowerCase());
    
    // Extract query keywords (remove common stop words)
    const stopWords = new Set(['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'what', 'how', 'when', 'where', 'why']);
    const queryWords = queryLower
      .split(/\s+/)
      .filter(w => w.length > 2 && !stopWords.has(w))
      .filter((w, i, arr) => arr.indexOf(w) === i); // unique

    const scored = agentRegistry.map(agent => {
      let confidence = 0;
      const reasons = [];

      // Build agent text corpus for matching
      const agentText = [
        agent.id,
        agent.name,
        agent.role,
        ...(agent.capabilities || []),
        ...(agent.tools || []),
        agent.category
      ].join(' ').toLowerCase();

      // Factor 1: Direct keyword matching (0-0.45 weight) - Balanced
      let keywordScore = 0;
      let matchedKeywords = 0;
      
      // Helper function for partial/fuzzy matching (more strict - only exact or close matches)
      const fuzzyMatch = (text, word) => {
        const lowerText = text.toLowerCase();
        const lowerWord = word.toLowerCase();
        // Exact match
        if (lowerText.includes(lowerWord)) return 1.0;
        // Partial match only for longer words (4+ chars)
        if (lowerWord.length >= 4) {
          // Check if word starts with same 4 chars or contains 4-char substring
          const prefix = lowerWord.substring(0, 4);
          if (lowerText.includes(prefix)) return 0.6; // Reduced from 0.7
        }
        return 0;
      };
      
      for (const word of queryWords) {
        if (word.length < 3) continue; // Skip very short words
        
        // Check name/role (highest weight)
        const nameMatch = fuzzyMatch(agent.name, word);
        const roleMatch = fuzzyMatch(agent.role, word);
        if (nameMatch > 0 || roleMatch > 0) {
          keywordScore += (nameMatch || roleMatch) * 0.20; // Reduced from 0.25
          matchedKeywords++;
          continue;
        }
        
        // Check agent ID
        if (fuzzyMatch(agent.id, word) > 0) {
          keywordScore += 0.15; // Reduced from 0.20
          matchedKeywords++;
          continue;
        }
        
        // Check in agent text (capabilities, tools, category) - only exact matches
        if (agentText.includes(word)) {
          keywordScore += 0.10; // Reduced from 0.12, removed fuzzy for text
          matchedKeywords++;
        }
      }
      
      // Boost for multiple keyword matches (moderate)
      if (matchedKeywords > 1) {
        keywordScore *= (1 + matchedKeywords * 0.12); // Reduced from 0.15
      }
      
      // Additional boost: if query has domain-specific terms (reduced boost)
      const domainTerms = ['marketing', 'sales', 'inventory', 'forecast', 'optimize', 'analysis', 'campaign'];
      const hasDomainTerm = domainTerms.some(term => queryLower.includes(term));
      if (hasDomainTerm && matchedKeywords > 0) {
        keywordScore *= 1.1; // Reduced from 1.2 (10% boost instead of 20%)
      }
      
      // Cap at 0.45 (reduced from 0.5)
      keywordScore = Math.min(0.45, keywordScore);
      if (keywordScore > 0) {
        confidence += keywordScore;
        reasons.push(`keyword_match:${matchedKeywords}`);
      }
      
      // Base score: only if very low score (more strict)
      if (matchedKeywords > 0 && keywordScore < 0.15 && confidence < 0.2) {
        confidence += 0.05; // Reduced from 0.1
        reasons.push('base_keyword_match');
      }

      // Factor 2: Capability matching (0-0.4 weight) - INCREASED from 0.3
      const agentCapabilities = (agent.capabilities || []).map(c => c.toLowerCase());
      let capabilityScore = 0;
      const capabilityKeywords = [
        { keywords: ['forecast', 'forecasting', 'demand', 'prediction', 'predict', 'future', 'projection'], caps: ['forecasting', 'demand_prediction', 'pipeline_forecasting', 'revenue_forecast'] },
        { keywords: ['marketing', 'mix', 'mmm', 'media', 'campaign', 'advertising', 'promotion'], caps: ['campaign_planning', 'budget_allocation', 'channel_selection', 'campaign', 'campaign_mapping'] },
        { keywords: ['elasticity', 'uplift', 'price', 'pricing', 'promo', 'discount'], caps: ['price_elasticity', 'promo_uplift', 'elasticity'] },
        { keywords: ['attribution', 'causal', 'incrementality', 'impact', 'effect'], caps: ['causal_analysis', 'attribution', 'impact_analysis', 'closed_loop_attribution'] },
        { keywords: ['optimization', 'optimize', 'optimise', 'allocation', 'allocate', 'budget'], caps: ['optimization', 'constraint_solving', 'budget_optimization', 'bid_optimization', 'portfolio_optimization'] },
        { keywords: ['simulation', 'scenario', 'what-if', 'whatif', 'simulate'], caps: ['scenario_simulation', 'monte_carlo'] },
        { keywords: ['risk', 'stockout', 'inventory', 'stock', 'safety'], caps: ['risk_assessment', 'inventory_analysis', 'stockout_prediction', 'inventory'] },
        { keywords: ['semantic', 'search', 'data', 'query', 'retrieve', 'find'], caps: ['semantic_search', 'data_retrieval', 'vector_query'] },
        { keywords: ['synthesis', 'aggregate', 'combine', 'summarize', 'summary'], caps: ['answer_synthesis', 'insight_aggregation', 'response_generation'] },
        { keywords: ['sales', 'pipeline', 'booking', 'revenue'], caps: ['pipeline_forecasting', 'conversion_prediction', 'revenue_forecast'] },
        { keywords: ['growth', 'opportunity', 'prioritize', 'segment'], caps: ['opportunity_scanning', 'gap_detection'] }
      ];

      for (const { keywords, caps } of capabilityKeywords) {
        const hasKeyword = keywords.some(kw => queryLower.includes(kw));
        const hasCapability = caps.some(cap => agentCapabilities.includes(cap));
        
        if (hasKeyword && hasCapability) {
          capabilityScore += 0.18; // Reduced from 0.20
        } else if (hasCapability) {
          // More strict: require better partial match
          const partialMatch = queryWords.some(qw => 
            keywords.some(kw => kw.includes(qw) || qw.includes(kw) || 
            (qw.length >= 4 && kw.includes(qw.substring(0, 4))) ||
            (kw.length >= 4 && qw.includes(kw.substring(0, 4))))
          );
          if (partialMatch) {
            capabilityScore += 0.12; // Reduced from 0.15
          }
          // Removed the "even more lenient" 0.05 base score
        }
      }

      capabilityScore = Math.min(0.35, capabilityScore); // Reduced from 0.4
      if (capabilityScore > 0) {
        confidence += capabilityScore;
        reasons.push(`capability_match:${capabilityScore.toFixed(2)}`);
      }
      // Removed the "capability_presence" bonus

      // Factor 3: Intent alignment (0-0.22 weight) - Balanced
      const intentMapping = {
        'analysis': ['sda', 'caa', 'asa', 'marketing-plan'],
        'simulation': ['ssa', 'ira'],
        'question': ['fqa', 'asa', 'sda'],
        'decision': ['opt', 'asa', 'marketing-plan'],
        'action': ['opt', 'marketing-plan'],
        'forecast': ['fqa', 'sales-pipeline'],
        'optimization': ['opt', 'marketing-plan'],
        'attribution': ['caa', 'campaign-sku-mapper'],
        'risk': ['ira'],
        'marketing': ['marketing-plan', 'elasticity-uplift', 'campaign-sku-mapper'],
        'sales': ['sales-pipeline'],
        'inventory': ['ira', 'inventory-position']
      };

      let intentScore = 0;
      for (const [intentKey, agentIds] of Object.entries(intentMapping)) {
        // More strict: only check intent type/category, not query text
        if ((intentType.includes(intentKey) || intentCategory.includes(intentKey)) && agentIds.includes(agent.id)) {
          intentScore = 0.22; // Reduced from 0.25
          reasons.push(`intent_match:${intentKey}`);
          break;
        }
      }
      confidence += intentScore;

      // Factor 4: Entity relevance (0-0.12 weight) - Balanced
      let entityScore = 0;
      if (entityValues.length > 0 || entityKeys.length > 0) {
        // Check if agent handles specific entity types
        const entityKeywords = [...entityValues, ...entityKeys].join(' ');
        const entityText = entityKeywords.toLowerCase();
        
        // More strict entity matching - require exact or close match
        if (agentText.includes(entityText) || 
            entityKeys.some(ek => agentText.includes(ek.toLowerCase())) ||
            entityValues.some(ev => agentText.includes(String(ev).toLowerCase()))) {
          entityScore = 0.12; // Reduced from 0.15
          reasons.push('entity_match');
        }
        // Removed the partial match bonus
      }
      confidence += entityScore;

      // Factor 5: Category alignment bonus (0-0.08 weight) - Balanced
      const categoryMapping = {
        'marketing': ['marketing-plan', 'elasticity-uplift', 'campaign-sku-mapper', 'caa'],
        'supply_chain': ['inventory-position', 'capacity-leadtime', 'supply-planning', 'production-scheduling', 'procurement', 'logistics-allocation'],
        'sales': ['sales-pipeline'],
        'analytics': ['sda', 'fqa', 'caa', 'ssa', 'ira', 'opt', 'asa'],
        'demand-gen': ['marketing-plan', 'sales-pipeline', 'elasticity-uplift', 'campaign-sku-mapper']
      };

      let categoryScore = 0;
      for (const [cat, agentIds] of Object.entries(categoryMapping)) {
        // More strict: only check intent category, not query text
        if (intentCategory.includes(cat) && agentIds.includes(agent.id)) {
          categoryScore = 0.08; // Reduced from 0.1
          reasons.push(`category_match:${cat}`);
          break;
        }
      }
      confidence += categoryScore;

      // Factor 6: General purpose agent bonus (more strict)
      // Only give bonus if confidence is very low and agent is truly general-purpose
      if (confidence < 0.25 && (agent.id === 'asa' || agent.id === 'sda')) {
        confidence += 0.12; // Reduced from 0.20
        reasons.push('general_purpose_agent');
      }

      // Factor 7: Query length bonus (more strict)
      // Require more keywords and matches
      if (queryWords.length >= 6 && matchedKeywords >= 3) {
        confidence += 0.05; // Reduced from 0.08
        reasons.push('detailed_query');
      }

      // Removed Factor 8 (category keyword match) - too lenient

      // Normalize to 0.0-1.0 range
      confidence = Math.min(1.0, Math.max(0.0, confidence));

      return {
        id: agent.id,
        name: agent.name,
        confidence: Math.round(confidence * 100) / 100, // Round to 2 decimals
        reasons: reasons.join(', '),
        matchedKeywords,
        category: agent.category
      };
    });

    // Sort by confidence descending, filter out zero confidence
    return scored
      .filter(s => s.confidence > 0)
      .sort((a, b) => {
        // Primary sort: confidence
        if (Math.abs(a.confidence - b.confidence) > 0.01) {
          return b.confidence - a.confidence;
        }
        // Secondary sort: number of matched keywords
        return b.matchedKeywords - a.matchedKeywords;
      });
  }

  /**
   * Generate dynamic agent configuration using OpenAI
   * Returns a spec that Python factory can use to create the agent
   * The spec includes capabilities that tool_registry.py can map to tools
   */
  async generateDynamicAgentConfig(query, intent, entities) {
    // Available capabilities from tool_registry.py (must match exactly)
    const availableCapabilities = [
      'semantic_data', 'forecasting', 'causal_analysis', 'scenario_simulation',
      'inventory', 'risk', 'optimization', 'budget_optimization', 'bid_optimization',
      'portfolio_optimization', 'anomaly_detection', 'opportunity_scanning',
      'change_detection', 'routing', 'translation', 'validation', 'compliance',
      'platform_integration', 'creative', 'retail_media', 'closed_loop_attribution',
      'incrementality', 'campaign', 'attribution', 'elasticity', 'mapping', 'gap_detection'
    ];

    // Available tools from tool_registry.py
    const availableTools = [
      'publish_cloudevent', 'fetch_cloudevent', 'fetch_schema',
      'validate_against_schema', 'publish_platform_action',
      'fetch_demand_forecast_signal', 'fetch_inventory_position',
      'fetch_pricing_promo_data', 'fetch_campaign_performance',
      'run_simulation_scenario', 'compute_stockout_risk'
    ];

    if (!this.openai) {
      logger.warn('⚠️ OpenAI not available - using fallback agent spec');
      return this._getFallbackAgentSpec(query, intent, entities);
    }

    try {
      const prompt = this._buildAgentSpecPrompt(query, intent, entities, availableCapabilities, availableTools);
      
      logger.info('🤖 Calling OpenAI to generate dynamic agent specification');
      
      const completion = await this.openai.chat.completions.create({
        model: config.openai.model || 'gpt-4-turbo-preview',
        messages: [
          { role: 'system', content: 'You are an expert at designing specialized AI agents for business operations. Return ONLY valid JSON, no markdown, no code blocks.' },
          { role: 'user', content: prompt }
        ],
        temperature: 0.3,
        max_tokens: 2000,
        response_format: { type: 'json_object' }
      });

      const content = completion.choices[0]?.message?.content || '{}';
      const spec = JSON.parse(content);

      // Validate and normalize the spec
      const validatedSpec = this._validateAgentSpec(spec, availableCapabilities, availableTools);
      
      logger.info('✅ Generated dynamic agent spec', {
        agentName: validatedSpec.agentName,
        capabilities: validatedSpec.capabilities.length,
        algorithms: validatedSpec.algorithms?.length || 0
      });

      return validatedSpec;

    } catch (error) {
      logger.error('❌ Failed to generate agent spec with OpenAI', { error: error.message });
      return this._getFallbackAgentSpec(query, intent, entities);
    }
  }

  /**
   * Build prompt for OpenAI to generate agent specification
   */
  _buildAgentSpecPrompt(query, intent, entities, availableCapabilities, availableTools) {
    return `Analyze this business query and create a specialized agent configuration.

QUERY: "${query}"
INTENT: ${JSON.stringify(intent)}
ENTITIES: ${JSON.stringify(entities)}

Generate a JSON specification for a CrewAI agent that can handle this query. The agent will be created dynamically using the Python factory.

AVAILABLE CAPABILITIES (choose 2-5 that best match the query):
${availableCapabilities.join(', ')}

AVAILABLE TOOLS (will be automatically selected based on capabilities):
${availableTools.join(', ')}

Return JSON in this exact format:
{
  "agentName": "Specialized agent name (e.g., 'Marketing Mix Modeling Specialist')",
  "agentType": "agent_type_id (e.g., 'marketing_mix_analyst')",
  "role": "Concise role description",
  "goal": "Specific, measurable goal",
  "backstory": "2-3 sentence expertise description",
  "capabilities": ["list", "of", "capabilities", "from", "available", "list"],
  "required_tools": ["optional", "specific", "tools"],
  "data_sources": ["relevant", "data", "sources"],
  "algorithms": [
    {
      "name": "Algorithm name (e.g., 'RobynMMM', 'GeoLift', 'CausalImpact')",
      "parameters": ["param1", "param2"],
      "outputs": ["output1", "output2"],
      "description": "What this algorithm does",
      "implementation": "Python function code (optional, for custom algorithms)",
      "dependencies": ["numpy", "pandas"] (optional)
    }
  ],
  "expectedInsights": ["insight1", "insight2"],
  "confidence": 0.95
}

CRITICAL REQUIREMENTS:
1. Capabilities MUST be from the available list above (exact match, case-sensitive)
2. Select 2-5 capabilities that directly address the query
3. Algorithms should be relevant to the query domain (e.g., marketing mix → RobynMMM, GeoLift, CausalImpact)
4. The agent will automatically get Redis Streams, CloudEvents, and Ontology tools
5. Tools will be automatically selected by tool_registry.py based on capabilities

EXAMPLES:
- Marketing mix query → capabilities: ['campaign', 'budget_optimization', 'attribution', 'elasticity']
- Forecast query → capabilities: ['forecasting', 'scenario_simulation']
- Risk analysis → capabilities: ['risk', 'inventory', 'anomaly_detection']

Return ONLY the JSON object, nothing else.`;
  }

  /**
   * Validate and normalize agent spec from OpenAI
   */
  _validateAgentSpec(spec, availableCapabilities, availableTools) {
    // Ensure required fields
    const validated = {
      agentName: spec.agentName || 'Dynamic Specialist Agent',
      agentType: spec.agentType || spec.agentName?.toLowerCase().replace(/\s+/g, '_') || 'dynamic_agent',
      role: spec.role || spec.agentName,
      goal: spec.goal || 'Analyze and provide insights',
      backstory: spec.backstory || 'Specialized agent for dynamic task execution',
      capabilities: [],
      required_tools: spec.required_tools || [],
      data_sources: spec.data_sources || [],
      algorithms: spec.algorithms || [],
      expectedInsights: spec.expectedInsights || [],
      confidence: spec.confidence || 0.95,
      input: spec.input || {}
    };

    // Filter capabilities to only include valid ones
    const capabilitySet = new Set(availableCapabilities);
    validated.capabilities = (spec.capabilities || [])
      .filter(cap => capabilitySet.has(cap.toLowerCase()))
      .map(cap => cap.toLowerCase());

    // If no valid capabilities, add defaults based on common patterns
    if (validated.capabilities.length === 0) {
      logger.warn('⚠️ No valid capabilities found, using defaults');
      validated.capabilities = ['semantic_data', 'forecasting'];
    }

    return validated;
  }

  /**
   * Fallback agent spec when OpenAI is unavailable
   */
  _getFallbackAgentSpec(query, intent, entities) {
    const queryLower = query.toLowerCase();
    
    // Infer capabilities from query keywords
    let capabilities = [];
    if (queryLower.includes('marketing') || queryLower.includes('mix') || queryLower.includes('mmm')) {
      capabilities = ['campaign', 'budget_optimization', 'attribution', 'elasticity'];
    } else if (queryLower.includes('forecast') || queryLower.includes('predict')) {
      capabilities = ['forecasting', 'scenario_simulation'];
    } else if (queryLower.includes('risk') || queryLower.includes('inventory')) {
      capabilities = ['risk', 'inventory', 'anomaly_detection'];
    } else if (queryLower.includes('optimize') || queryLower.includes('allocation')) {
      capabilities = ['optimization', 'budget_optimization'];
    } else {
      capabilities = ['semantic_data', 'forecasting'];
    }

    return {
      agentName: 'Dynamic Specialist Agent',
      agentType: 'dynamic_agent',
      role: 'Specialized Analyst',
      goal: `Analyze and provide insights for: ${query.slice(0, 100)}`,
      backstory: 'Specialized agent created dynamically to handle specific business queries',
      capabilities,
      required_tools: [],
      data_sources: ['demand_forecast', 'inventory', 'campaign'],
      algorithms: [],
      expectedInsights: ['analysis_results', 'recommendations'],
      confidence: 0.85,
      input: { query, intent, entities }
    };
  }
}


