/**
 * Ontology Service
 * 
 * Unified API for agents to interact with SKOS ontology + knowledge graph.
 * Implements concept resolution, expansion, enum mapping, constraints, and SHACL validation.
 */

import { createClient } from '@supabase/supabase-js';
import config from '../../config/index.js';
import { logger } from '../../utils/logger.js';

export class OntologyService {
  constructor() {
    this.supabase = null;
    this.cache = new Map(); // Simple in-memory cache
    this.cacheTTL = 3600 * 1000; // 1 hour in milliseconds
    this.healthy = false;
  }

  async initialize() {
    if (!config.supabase.enabled) {
      logger.warn('Supabase not configured, OntologyService will use limited functionality');
      this.healthy = false;
      return;
    }

    try {
      this.supabase = createClient(
        config.supabase.url,
        config.supabase.serviceRoleKey || config.supabase.anonKey,
        {
          auth: { persistSession: false, autoRefreshToken: false }
        }
      );
      
      this.healthy = true;
      logger.info('✅ OntologyService initialized');
    } catch (error) {
      logger.error('❌ OntologyService initialization failed', { error: error.message });
      this.healthy = false;
    }
  }

  isHealthy() {
    return this.healthy;
  }

  /**
   * Resolve label/synonym to canonical URI
   * @param {string} termOrUri - Term or URI to resolve
   * @returns {Promise<string|null>} Canonical URI or null
   */
  async resolve(termOrUri) {
    if (!this.supabase) {
      logger.warn('OntologyService: Supabase not available');
      return null;
    }

    // Check cache first
    const cacheKey = `resolve:${termOrUri}`;
    const cached = this.getFromCache(cacheKey);
    if (cached) {
      return cached;
    }

    // If already a URI, return it
    if (termOrUri.includes(':')) {
      this.setCache(cacheKey, termOrUri);
      return termOrUri;
    }

    try {
      // Use SQL function
      const { data, error } = await this.supabase.rpc('resolve_concept', {
        term: termOrUri
      });

      if (error) {
        logger.error('[OntologyService] resolve error:', error);
        return null;
      }

      const result = data || null;
      if (result) {
        this.setCache(cacheKey, result);
      }

      return result;
    } catch (error) {
      logger.error('[OntologyService] resolve exception:', error);
      return null;
    }
  }

  /**
   * Expand concepts using SKOS relations
   * @param {string[]} concepts - Concept URIs to expand
   * @param {string[]} relations - Relations to follow (default: ['broader', 'narrower', 'related'])
   * @param {number} depth - How many hops to traverse (default: 1)
   * @returns {Promise<string[]>} Expanded concept URIs
   */
  async expand(concepts, relations = ['broader', 'narrower', 'related'], depth = 1) {
    if (!this.supabase) {
      logger.warn('OntologyService: Supabase not available');
      return concepts;
    }

    const cacheKey = `expand:${concepts.sort().join(',')}:${relations.sort().join(',')}:${depth}`;
    const cached = this.getFromCache(cacheKey);
    if (cached) {
      return cached;
    }

    let expandedConcepts = [...concepts];
    
    try {
      // Handle synonyms separately (alt_labels)
      if (relations.includes('synonym')) {
        for (const conceptUri of concepts) {
          const { data } = await this.supabase
            .from('ontology_concepts')
            .select('alt_labels')
            .eq('concept_uri', conceptUri)
            .single();
          
          if (data?.alt_labels) {
            // Resolve alt_labels back to URIs
            for (const label of data.alt_labels) {
              const uri = await this.resolve(label);
              if (uri) expandedConcepts.push(uri);
            }
          }
        }
      }

      // Use SQL function for broader/narrower/related
      const ontologyRelations = relations.filter(r => r !== 'synonym');
      if (ontologyRelations.length > 0) {
        const { data, error } = await this.supabase.rpc('expand_concepts', {
          concept_uris: concepts,
          relations: ontologyRelations,
          max_depth: depth
        });

        if (!error && data) {
          expandedConcepts.push(...data.map(row => row.concept_uri));
        }
      }

      // Deduplicate
      const result = Array.from(new Set(expandedConcepts));
      
      // Cache for 1 hour
      this.setCache(cacheKey, result);
      
      logger.debug(`[OntologyService] Expanded ${concepts.length} → ${result.length} concepts`);
      
      return result;
    } catch (error) {
      logger.error('[OntologyService] expand error:', error);
      return concepts;
    }
  }

  /**
   * Get external ID for entity in different system
   * @param {string} entityUri - Entity URI
   * @param {string} system - System name (e.g., 'erp', 'retailer', 'vendor')
   * @returns {Promise<string|null>} External ID or null
   */
  async sameAs(entityUri, system) {
    if (!this.supabase) {
      return null;
    }

    const cacheKey = `sameas:${entityUri}:${system}`;
    const cached = this.getFromCache(cacheKey);
    if (cached) return cached;

    try {
      // Query entity_properties for sameAs mappings
      const { data } = await this.supabase
        .from('entity_properties')
        .select('value')
        .eq('property', `sameAs_${system}`)
        .eq('entity_id', entityUri)
        .maybeSingle();

      const externalId = data?.value || null;
      
      if (externalId) {
        this.setCache(cacheKey, externalId);
      }
      
      return externalId;
    } catch (error) {
      logger.error('[OntologyService] sameAs error:', error);
      return null;
    }
  }

  /**
   * Get constraints/policies for concept or entity
   * @param {string} entityOrConcept - Concept or entity URI
   * @returns {Promise<Record<string, any>>} Constraints object
   */
  async getConstraints(entityOrConcept) {
    if (!this.supabase) {
      return {};
    }

    const cacheKey = `constraints:${entityOrConcept}`;
    const cached = this.getFromCache(cacheKey);
    if (cached) return cached;

    try {
      const { data } = await this.supabase
        .from('ontology_constraints')
        .select('*')
        .eq('concept_uri', entityOrConcept);

      const constraints = {};
      
      for (const row of data || []) {
        constraints[row.constraint_type] = row.constraint_value;
      }

      this.setCache(cacheKey, constraints);
      
      return constraints;
    } catch (error) {
      logger.error('[OntologyService] getConstraints error:', error);
      return {};
    }
  }

  /**
   * Get SHACL shape for validation
   * @param {string} shapeUri - Shape URI
   * @returns {Promise<any>} SHACL shape definition or null
   */
  async getShape(shapeUri) {
    if (!this.supabase) {
      return null;
    }

    try {
      const { data } = await this.supabase
        .from('ontology_shapes')
        .select('shape_definition')
        .eq('shape_uri', shapeUri)
        .maybeSingle();

      return data?.shape_definition || null;
    } catch (error) {
      logger.error('[OntologyService] getShape error:', error);
      return null;
    }
  }

  /**
   * Map enum/unit value using ontology
   * @param {string} fieldUri - Field URI
   * @param {string} fromValue - Source value
   * @returns {Promise<string|null>} Target value or null
   */
  async mapEnum(fieldUri, fromValue) {
    if (!this.supabase) {
      return null;
    }

    const cacheKey = `enum:${fieldUri}:${fromValue}`;
    const cached = this.getFromCache(cacheKey);
    if (cached) return cached;

    try {
      const { data } = await this.supabase
        .from('ontology_mappings')
        .select('target_value')
        .eq('source_field', fieldUri)
        .eq('source_value', fromValue)
        .maybeSingle();

      const targetValue = data?.target_value || null;
      
      if (targetValue) {
        this.setCache(cacheKey, targetValue);
      }
      
      return targetValue;
    } catch (error) {
      logger.error('[OntologyService] mapEnum error:', error);
      return null;
    }
  }

  /**
   * Find agents interested in concepts
   * @param {string[]} conceptUris - Concept URIs
   * @returns {Promise<Array>} Array of matching agents
   */
  async findInterestedAgents(conceptUris) {
    if (!this.supabase) {
      return [];
    }

    try {
      const { data, error } = await this.supabase.rpc('find_interested_agents', {
        concept_uris: conceptUris
      });

      if (error) {
        logger.error('[OntologyService] findInterestedAgents error:', error);
        return [];
      }

      return data || [];
    } catch (error) {
      logger.error('[OntologyService] findInterestedAgents exception:', error);
      return [];
    }
  }

  /**
   * Search concepts by label
   * @param {string} searchTerm - Search term
   * @returns {Promise<Array>} Matching concepts
   */
  async searchConcepts(searchTerm) {
    if (!this.supabase) {
      return [];
    }

    try {
      const { data } = await this.supabase
        .from('ontology_concepts')
        .select('*')
        .or(`pref_label.ilike.%${searchTerm}%,definition.ilike.%${searchTerm}%`)
        .limit(20);

      return data || [];
    } catch (error) {
      logger.error('[OntologyService] searchConcepts error:', error);
      return [];
    }
  }

  /**
   * Simple in-memory cache helpers
   */
  getFromCache(key) {
    const entry = this.cache.get(key);
    if (entry && Date.now() < entry.expires) {
      return entry.value;
    }
    this.cache.delete(key);
    return null;
  }

  setCache(key, value) {
    this.cache.set(key, {
      value,
      expires: Date.now() + this.cacheTTL
    });
    
    // Limit cache size (simple LRU)
    if (this.cache.size > 1000) {
      const firstKey = this.cache.keys().next().value;
      this.cache.delete(firstKey);
    }
  }

  /**
   * Invalidate cache for a concept
   */
  invalidateCache(conceptUri) {
    const keysToDelete = [];
    for (const key of this.cache.keys()) {
      if (key.includes(conceptUri)) {
        keysToDelete.push(key);
      }
    }
    keysToDelete.forEach(key => this.cache.delete(key));
    logger.debug(`[OntologyService] Invalidated cache for concept: ${conceptUri}`);
  }
}

// Singleton instance
let ontologyService = null;

export function getOntologyService() {
  if (!ontologyService) {
    ontologyService = new OntologyService();
  }
  return ontologyService;
}

export default OntologyService;

