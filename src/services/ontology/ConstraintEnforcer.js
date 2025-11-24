/**
 * Constraint Enforcer
 * 
 * Applies ontology constraints (retrieved via getConstraints()) during validation.
 * Enforces business rules like minimum margins, price floors, etc.
 */

import { getOntologyService } from './OntologyService.js';
import { logger } from '../../utils/logger.js';

export class ConstraintEnforcer {
  constructor(ontologyService = null) {
    this.ontologyService = ontologyService || getOntologyService();
  }

  /**
   * Enforce constraints on a payload based on its concept/category
   * @param {string} conceptUri - Concept URI
   * @param {Record<string, any>} payload - Payload to validate
   * @param {string} category - Optional category
   * @returns {Promise<EnforcementResult>} Enforcement result
   */
  async enforce(conceptUri, payload, category = null) {
    const violations = [];

    try {
      // Get constraints for this concept
      const constraints = await this.ontologyService.getConstraints(conceptUri);

      if (!constraints || Object.keys(constraints).length === 0) {
        // No constraints defined, pass validation
        return { valid: true, violations: [] };
      }

      // Apply each constraint
      for (const [constraintType, constraintValue] of Object.entries(constraints)) {
        const violation = this.applyConstraint(constraintType, constraintValue, payload);
        if (violation) {
          violations.push(violation);
        }
      }
    } catch (error) {
      logger.error('[ConstraintEnforcer] Error enforcing constraints:', error);
      // Don't fail validation if constraint checking fails
      return { valid: true, violations: [] };
    }

    return {
      valid: violations.filter(v => v.severity === 'error').length === 0,
      violations
    };
  }

  /**
   * Apply a single constraint to a payload
   */
  applyConstraint(constraintType, constraintValue, payload) {
    // Handle JSONB constraint values
    const value = constraintValue?.value ?? constraintValue;
    
    // Check constraint type
    switch (constraintType) {
      case 'minMarginPct':
        const marginPct = payload.marginPct || payload.margin_pct;
        if (marginPct !== undefined && marginPct < value) {
          return {
            field: 'marginPct',
            constraint: 'minMarginPct',
            value: marginPct,
            expected: `>= ${value}`,
            severity: 'error',
            message: `Margin percentage ${marginPct}% is below minimum ${value}%`
          };
        }
        break;

      case 'floorPrice':
        const price = payload.price || payload.newPrice;
        if (price !== undefined && price < value) {
          return {
            field: 'price',
            constraint: 'floorPrice',
            value: price,
            expected: `>= ${value}`,
            severity: 'error',
            message: `Price ${price} is below floor price ${value}`
          };
        }
        break;

      case 'maxDiscount':
        const discount = payload.discount || payload.discountPct;
        if (discount !== undefined && discount > value) {
          return {
            field: 'discount',
            constraint: 'maxDiscount',
            value: discount,
            expected: `<= ${value}`,
            severity: 'error',
            message: `Discount ${discount}% exceeds maximum ${value}%`
          };
        }
        break;

      case 'minROAS':
        const roas = payload.roas || payload.ROAS;
        if (roas !== undefined && roas < value) {
          return {
            field: 'roas',
            constraint: 'minROAS',
            value: roas,
            expected: `>= ${value}`,
            severity: 'error',
            message: `ROAS ${roas} is below minimum ${value}`
          };
        }
        break;
    }

    return null;
  }

  /**
   * Format violations as human-readable messages
   */
  formatViolations(violations) {
    return violations.map(v => 
      `[${v.severity.toUpperCase()}] ${v.message} (field: ${v.field})`
    );
  }
}

// Singleton
let enforcerInstance = null;

export function getConstraintEnforcer() {
  if (!enforcerInstance) {
    enforcerInstance = new ConstraintEnforcer();
  }
  return enforcerInstance;
}

export default ConstraintEnforcer;

