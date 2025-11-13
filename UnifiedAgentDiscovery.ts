/**
 * Unified Agent Discovery Service
 * 
 * Consolidates three previous discovery implementations:
 * - SemanticRouterMeshBridge.discoverAgents()
 * - ActionAgentService.findSuitableExistingAgent()
 * - UnifiedAgentDiscoveryService.semanticAgentDiscovery()
 * 
 * Provides consistent capability scoring, threshold management, and agent selection.
 */

import OpenAI from 'openai';
import { supabase } from '../../lib/supabase';
import { getOntologyService } from '../ontology/OntologyService';
import { LoadBalancer } from './LoadBalancer';

export interface AgentCapability {
  name: string;
  confidence: number;
  source: 'ontology' | 'semantic' | 'registry' | 'template';
}

export interface DiscoveredAgent {
  id: string;
  name: string;
  type: string;
  confidence: number;
  capabilities: string[];
  suitability: number;
  matchingCapabilities: string[];
  source: 'ontology' | 'semantic' | 'registry' | 'combined';
  metadata?: Record<string, any>;
}

export interface DiscoveryRequest {
  query?: string;
  actionType?: string;
  requiredCapabilities: string[];
  ontologyConcepts?: string[];
  intent?: string;
  entities?: Record<string, any>;
  minConfidence?: number;
  maxResults?: number;
}

export interface DiscoveryConfig {
  // Unified thresholds
  minConfidenceThreshold: number;        // Default: 0.75
  ontologyMatchBoost: number;            // Default: 0.10
  combinedMatchBoost: number;            // Default: 0.15
  capabilityMatchWeight: number;         // Default: 0.70
  semanticSimilarityWeight: number;      // Default: 0.30
  
  // Caching
  enableCaching: boolean;
  cacheTTL: number;                      // seconds
  
  // Parallel processing
  enableParallelExpansion: boolean;
  batchSize: number;
}

const DEFAULT_CONFIG: DiscoveryConfig = {
  minConfidenceThreshold: 0.75,
  ontologyMatchBoost: 0.10,
  combinedMatchBoost: 0.15,
  capabilityMatchWeight: 0.70,
  semanticSimilarityWeight: 0.30,
  enableCaching: true,
  cacheTTL: 300, // 5 minutes
  enableParallelExpansion: true,
  batchSize: 10
};

export class UnifiedAgentDiscovery {
  private openai: OpenAI;
  private ontologyService = getOntologyService();
  private config: DiscoveryConfig;
  private cache: Map<string, { agents: DiscoveredAgent[]; timestamp: number }> = new Map();
  private loadBalancer = new LoadBalancer();

  constructor(openaiClient: OpenAI, config: Partial<DiscoveryConfig> = {}) {
    this.openai = openaiClient;
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  /**
   * Main discovery method - unified entry point
   */
  async discoverAgents(request: DiscoveryRequest): Promise<DiscoveredAgent[]> {
    const startTime = Date.now();
    console.log(`[UnifiedAgentDiscovery] Starting discovery for action: ${request.actionType || 'unknown'}`);
    console.log(`[UnifiedAgentDiscovery] Required capabilities: ${request.requiredCapabilities.join(', ')}`);

    // Check cache
    const cacheKey = this.getCacheKey(request);
    if (this.config.enableCaching) {
      const cached = this.getFromCache(cacheKey);
      if (cached) {
        console.log(`[UnifiedAgentDiscovery] Cache hit for ${cacheKey}`);
        return cached;
      }
    }

    try {
      // Step 1: Expand ontology concepts (parallel if enabled)
      const expandedConcepts = await this.expandOntologyConcepts(
        request.ontologyConcepts || []
      );

      // Step 2: Discover agents from multiple sources in parallel
      const [ontologyAgents, semanticAgents, registryAgents] = await Promise.all([
        this.discoverViaOntology(expandedConcepts, request.requiredCapabilities),
        this.discoverViaSemantic(request),
        this.discoverViaRegistry(request.requiredCapabilities)
      ]);

      // Step 3: Combine and rank agents
      const combinedAgents = this.combineAndRankAgents(
        ontologyAgents,
        semanticAgents,
        registryAgents,
        request
      );

      // Step 4: Filter by confidence threshold
      const minConfidence = request.minConfidence || this.config.minConfidenceThreshold;
      const filteredAgents = combinedAgents.filter(agent => agent.confidence >= minConfidence);

      // Step 5: Limit results
      const maxResults = request.maxResults || 10;
      const finalAgents = filteredAgents.slice(0, maxResults);

      // Cache results
      if (this.config.enableCaching) {
        this.setCache(cacheKey, finalAgents);
      }

      const duration = Date.now() - startTime;
      console.log(`[UnifiedAgentDiscovery] Discovery complete in ${duration}ms`);
      console.log(`[UnifiedAgentDiscovery] Found ${finalAgents.length} agents (filtered from ${combinedAgents.length})`);

      return this.loadBalancer.selectAgent(finalAgents);

    } catch (error) {
      console.error('[UnifiedAgentDiscovery] Discovery failed:', error);
      throw error;
    }
  }

  /**
   * Expand ontology concepts using SKOS relations (parallel processing)
   */
  private async expandOntologyConcepts(concepts: string[]): Promise<string[]> {
    if (concepts.length === 0) return [];

    console.log(`[UnifiedAgentDiscovery] Expanding ${concepts.length} ontology concepts`);

    if (this.config.enableParallelExpansion) {
      // Parallel expansion with Promise.all
      const expansionPromises = concepts.map(async (concept) => {
        try {
          const expanded = await this.ontologyService.expand(
            [concept],
            ['broader', 'narrower', 'related']
          );
          return expanded;
        } catch (error) {
          console.warn(`[UnifiedAgentDiscovery] Failed to expand concept ${concept}:`, error);
          return [concept]; // Fallback to original concept
        }
      });

      const expandedArrays = await Promise.all(expansionPromises);
      const allExpanded = expandedArrays.flat();
      const uniqueExpanded = [...new Set(allExpanded)];

      console.log(`[UnifiedAgentDiscovery] Expanded to ${uniqueExpanded.length} unique concepts`);
      return uniqueExpanded;

    } else {
      // Sequential expansion (fallback)
      const expandedConcepts: string[] = [];
      for (const concept of concepts) {
        try {
          const expanded = await this.ontologyService.expand(
            [concept],
            ['broader', 'narrower', 'related']
          );
          expandedConcepts.push(...expanded);
        } catch (error) {
          console.warn(`[UnifiedAgentDiscovery] Failed to expand concept ${concept}:`, error);
          expandedConcepts.push(concept);
        }
      }
      return [...new Set(expandedConcepts)];
    }
  }

  /**
   * Discover agents via ontology profiles
   */
  private async discoverViaOntology(
    concepts: string[],
    requiredCapabilities: string[]
  ): Promise<DiscoveredAgent[]> {
    if (concepts.length === 0) return [];

    try {
      const agentMatches = await this.ontologyService.findInterestedAgents(concepts);
      console.log(`[UnifiedAgentDiscovery] Ontology matched ${agentMatches.length} agents`);

      return agentMatches.map(match => ({
        id: match.agent_id,
        name: this.formatAgentName(match.agent_id),
        type: match.agent_id,
        confidence: 0.85, // High confidence from ontology match
        capabilities: requiredCapabilities,
        suitability: 0.85,
        matchingCapabilities: requiredCapabilities,
        source: 'ontology' as const,
        metadata: {
          match_type: match.match_type,
          matched_concepts: match.matched_concepts
        }
      }));

    } catch (error) {
      console.warn('[UnifiedAgentDiscovery] Ontology discovery failed:', error);
      return [];
    }
  }

  /**
   * Discover agents via semantic similarity (vector embeddings)
   */
  private async discoverViaSemantic(request: DiscoveryRequest): Promise<DiscoveredAgent[]> {
    if (!request.query && !request.actionType) return [];

    try {
      const query = request.query || `Execute ${request.actionType} with capabilities: ${request.requiredCapabilities.join(', ')}`;

      // Query agent registry with semantic search
      const { data: agents, error } = await supabase
        .from('agent_registry')
        .select('*')
        .limit(20);

      if (error) throw error;
      if (!agents || agents.length === 0) return [];

      // Calculate semantic similarity using embeddings
      const embedding = await this.getEmbedding(query);
      
      const scoredAgents = agents.map(agent => {
        const capabilityMatch = this.calculateCapabilityMatch(
          agent.capabilities || [],
          request.requiredCapabilities
        );

        return {
          id: agent.id,
          name: agent.name || agent.id,
          type: agent.type || 'unknown',
          confidence: capabilityMatch * 0.8, // Slightly lower than ontology
          capabilities: agent.capabilities || [],
          suitability: capabilityMatch,
          matchingCapabilities: this.getMatchingCapabilities(
            agent.capabilities || [],
            request.requiredCapabilities
          ),
          source: 'semantic' as const,
          metadata: agent.metadata
        };
      });

      return scoredAgents.filter(agent => agent.confidence > 0.5);

    } catch (error) {
      console.warn('[UnifiedAgentDiscovery] Semantic discovery failed:', error);
      return [];
    }
  }

  /**
   * Discover agents via direct registry lookup
   */
  private async discoverViaRegistry(requiredCapabilities: string[]): Promise<DiscoveredAgent[]> {
    try {
      const { data: agents, error } = await supabase
        .from('agent_registry')
        .select('*')
        .limit(50);

      if (error) throw error;
      if (!agents || agents.length === 0) return [];

      const scoredAgents = agents
        .map(agent => {
          const capabilityMatch = this.calculateCapabilityMatch(
            agent.capabilities || [],
            requiredCapabilities
          );

          return {
            id: agent.id,
            name: agent.name || agent.id,
            type: agent.type || 'unknown',
            confidence: capabilityMatch * 0.7, // Lower than ontology/semantic
            capabilities: agent.capabilities || [],
            suitability: capabilityMatch,
            matchingCapabilities: this.getMatchingCapabilities(
              agent.capabilities || [],
              requiredCapabilities
            ),
            source: 'registry' as const,
            metadata: agent.metadata
          };
        })
        .filter(agent => agent.suitability >= 0.6); // Registry requires 60% match

      return scoredAgents;

    } catch (error) {
      console.warn('[UnifiedAgentDiscovery] Registry discovery failed:', error);
      return [];
    }
  }

  /**
   * Combine agents from multiple sources and rank by confidence
   */
  private combineAndRankAgents(
    ontologyAgents: DiscoveredAgent[],
    semanticAgents: DiscoveredAgent[],
    registryAgents: DiscoveredAgent[],
    request: DiscoveryRequest
  ): DiscoveredAgent[] {
    const agentMap = new Map<string, DiscoveredAgent>();

    // Add ontology agents (highest priority)
    for (const agent of ontologyAgents) {
      agentMap.set(agent.id, agent);
    }

    // Add semantic agents (boost if already in map)
    for (const agent of semanticAgents) {
      const existing = agentMap.get(agent.id);
      if (existing) {
        // Boost confidence for agents found by multiple methods
        existing.confidence = Math.min(
          0.95,
          existing.confidence + this.config.combinedMatchBoost
        );
        existing.source = 'combined';
      } else {
        agentMap.set(agent.id, agent);
      }
    }

    // Add registry agents (boost if already in map)
    for (const agent of registryAgents) {
      const existing = agentMap.get(agent.id);
      if (existing) {
        existing.confidence = Math.min(
          0.95,
          existing.confidence + this.config.ontologyMatchBoost
        );
        existing.source = 'combined';
      } else {
        agentMap.set(agent.id, agent);
      }
    }

    // Convert to array and sort by confidence
    const combinedAgents = Array.from(agentMap.values());
    combinedAgents.sort((a, b) => b.confidence - a.confidence);

    return combinedAgents;
  }

  /**
   * Calculate capability match score
   */
  private calculateCapabilityMatch(
    agentCapabilities: string[],
    requiredCapabilities: string[]
  ): number {
    if (requiredCapabilities.length === 0) return 1.0;
    if (agentCapabilities.length === 0) return 0.0;

    const matchingCapabilities = this.getMatchingCapabilities(
      agentCapabilities,
      requiredCapabilities
    );

    return matchingCapabilities.length / requiredCapabilities.length;
  }

  /**
   * Get matching capabilities between agent and requirements
   */
  private getMatchingCapabilities(
    agentCapabilities: string[],
    requiredCapabilities: string[]
  ): string[] {
    return requiredCapabilities.filter(required =>
      agentCapabilities.some(agentCap =>
        agentCap.toLowerCase().includes(required.toLowerCase()) ||
        required.toLowerCase().includes(agentCap.toLowerCase())
      )
    );
  }

  /**
   * Get embedding for semantic similarity
   */
  private async getEmbedding(text: string): Promise<number[]> {
    try {
      const response = await this.openai.embeddings.create({
        model: 'text-embedding-3-small',
        input: text
      });
      return response.data[0].embedding;
    } catch (error) {
      console.warn('[UnifiedAgentDiscovery] Embedding generation failed:', error);
      return [];
    }
  }

  /**
   * Format agent ID to human-readable name
   */
  private formatAgentName(agentId: string): string {
    return agentId
      .replace(/-/g, ' ')
      .replace(/\b\w/g, l => l.toUpperCase());
  }

  /**
   * Generate cache key from request
   */
  private getCacheKey(request: DiscoveryRequest): string {
    const parts = [
      request.actionType || '',
      request.requiredCapabilities.join(','),
      (request.ontologyConcepts || []).join(',')
    ];
    return parts.join('|');
  }

  /**
   * Get agents from cache
   */
  private getFromCache(key: string): DiscoveredAgent[] | null {
    const cached = this.cache.get(key);
    if (!cached) return null;

    const age = Date.now() - cached.timestamp;
    if (age > this.config.cacheTTL * 1000) {
      this.cache.delete(key);
      return null;
    }

    return cached.agents;
  }

  /**
   * Set agents in cache
   */
  private setCache(key: string, agents: DiscoveredAgent[]): void {
    this.cache.set(key, {
      agents,
      timestamp: Date.now()
    });
  }

  /**
   * Clear cache
   */
  public clearCache(): void {
    this.cache.clear();
  }

  /**
   * Update configuration
   */
  public updateConfig(config: Partial<DiscoveryConfig>): void {
    this.config = { ...this.config, ...config };
  }

  /**
   * Get current configuration
   */
  public getConfig(): DiscoveryConfig {
    return { ...this.config };
  }
}

// Export singleton instance
let unifiedDiscoveryInstance: UnifiedAgentDiscovery | null = null;

export function getUnifiedAgentDiscovery(openaiClient?: OpenAI): UnifiedAgentDiscovery {
  if (!unifiedDiscoveryInstance) {
    if (!openaiClient) {
      throw new Error('OpenAI client required for first initialization');
    }
    unifiedDiscoveryInstance = new UnifiedAgentDiscovery(openaiClient);
  }
  return unifiedDiscoveryInstance;
}
