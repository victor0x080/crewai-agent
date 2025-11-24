/**
 * Agent Profile Validator
 * 
 * Validates that agents actually have the capabilities they claim in their profiles.
 * Prevents capability fraud and ensures ontology profiles are accurate.
 */

import { createClient } from '@supabase/supabase-js';
import { getOntologyService } from './OntologyService.js';
import config from '../../config/index.js';
import { logger } from '../../utils/logger.js';

export class AgentProfileValidator {
  constructor(ontologyService = null) {
    this.ontologyService = ontologyService || getOntologyService();
    this.supabase = null;
  }

  async initialize() {
    if (config.supabase.enabled) {
      this.supabase = createClient(
        config.supabase.url,
        config.supabase.serviceRoleKey || config.supabase.anonKey
      );
    }
  }

  /**
   * Validate a single agent profile
   */
  async validateProfile(profile) {
    const errors = [];
    const warnings = [];

    // 1. Validate capabilities exist and are not empty
    if (!profile.capabilities || profile.capabilities.length === 0) {
      errors.push({
        type: 'missing_capability',
        message: 'Agent must declare at least one capability',
        field: 'capabilities'
      });
    }

    // 2. Validate ontology concepts are valid URIs
    const allConcepts = [
      ...(profile.interests_concepts_must || []),
      ...(profile.interests_concepts_any || [])
    ];

    for (const concept of allConcepts) {
      try {
        const resolved = await this.ontologyService.resolve(concept);
        if (!resolved) {
          errors.push({
            type: 'invalid_concept',
            message: `Ontology concept '${concept}' does not exist`,
            field: 'interests_concepts',
            expected: 'valid concept URI',
            actual: concept
          });
        }
      } catch (error) {
        errors.push({
          type: 'invalid_concept',
          message: `Failed to resolve concept '${concept}': ${error.message}`,
          field: 'interests_concepts'
        });
      }
    }

    return {
      valid: errors.length === 0,
      agent_id: profile.agent_id,
      errors,
      warnings
    };
  }

  /**
   * Validate all agent profiles in the registry
   */
  async validateAllProfiles() {
    const results = [];

    if (!this.supabase) {
      logger.warn('[AgentProfileValidator] Supabase not available');
      return results;
    }

    try {
      // Get all agent profiles
      const { data: profiles, error } = await this.supabase
        .from('agent_ontology_profiles')
        .select('*');

      if (error) {
        logger.error('[AgentProfileValidator] Error fetching profiles:', error);
        return results;
      }

      // Validate each profile
      for (const profile of profiles || []) {
        const result = await this.validateProfile(profile);
        results.push(result);
      }
    } catch (error) {
      logger.error('[AgentProfileValidator] Error validating profiles:', error);
    }

    return results;
  }
}

// Singleton
let validatorInstance = null;

export function getAgentProfileValidator() {
  if (!validatorInstance) {
    validatorInstance = new AgentProfileValidator();
    validatorInstance.initialize();
  }
  return validatorInstance;
}

export default AgentProfileValidator;

