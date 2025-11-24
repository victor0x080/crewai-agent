/**
 * SHACL Validator Service
 * Validates data against SHACL shapes for semantic policy enforcement
 * Complements JSON Schema validation with semantic rules
 */

import { getOntologyService } from './OntologyService.js';
import { logger } from '../../utils/logger.js';

export class SHACLValidator {
  constructor() {
    this.ontologyService = getOntologyService();
  }

  /**
   * Validate data against a SHACL shape
   * @param {any} data - Data to validate
   * @param {string} shapeUri - SHACL shape URI
   * @param {Record<string, any>} context - Optional context
   * @returns {Promise<SHACLValidationResult>} Validation result
   */
  async validate(data, shapeUri, context = {}) {
    // Fetch SHACL shape from ontology
    const shape = await this.ontologyService.getShape(shapeUri);
    
    if (!shape) {
      throw new Error(`SHACL shape not found: ${shapeUri}`);
    }

    const violations = [];
    const warnings = [];
    const infos = [];

    // Validate against shape properties
    if (shape.properties || shape.property) {
      const properties = shape.properties || shape.property;
      for (const propertyConstraint of properties) {
        const propertyViolations = this.validateProperty(
          data,
          propertyConstraint,
          context
        );
        
        for (const violation of propertyViolations) {
          if (violation.resultSeverity === 'Violation') {
            violations.push(violation);
          } else if (violation.resultSeverity === 'Warning') {
            warnings.push(violation);
          } else {
            infos.push(violation);
          }
        }
      }
    }

    // Validate constraints
    if (shape.constraints) {
      const constraintViolations = this.validateConstraints(
        data,
        shape.constraints,
        context
      );
      violations.push(...constraintViolations);
    }

    return {
      conforms: violations.length === 0,
      violations,
      warnings,
      infos
    };
  }

  /**
   * Validate a single property constraint
   */
  validateProperty(data, propertyConstraint, context = {}) {
    const violations = [];
    const path = propertyConstraint.path;
    const value = this.getValueAtPath(data, path);

    // sh:minCount - minimum occurrences
    if (propertyConstraint.minCount !== undefined) {
      if (value === undefined || value === null) {
        violations.push({
          focusNode: data['@id'] || 'root',
          resultPath: path,
          resultMessage: `Property ${path} is required (minCount: ${propertyConstraint.minCount})`,
          resultSeverity: 'Violation',
          sourceConstraintComponent: 'sh:minCount'
        });
      }
    }

    // sh:maxCount - maximum occurrences
    if (propertyConstraint.maxCount !== undefined && Array.isArray(value)) {
      if (value.length > propertyConstraint.maxCount) {
        violations.push({
          focusNode: data['@id'] || 'root',
          resultPath: path,
          resultMessage: `Property ${path} exceeds maxCount: ${propertyConstraint.maxCount}`,
          resultSeverity: 'Violation',
          sourceConstraintComponent: 'sh:maxCount',
          value
        });
      }
    }

    // sh:datatype - datatype constraint
    if (propertyConstraint.datatype && value !== undefined) {
      if (!this.validateDatatype(value, propertyConstraint.datatype)) {
        violations.push({
          focusNode: data['@id'] || 'root',
          resultPath: path,
          resultMessage: `Property ${path} must be of type ${propertyConstraint.datatype}`,
          resultSeverity: 'Violation',
          sourceConstraintComponent: 'sh:datatype',
          value
        });
      }
    }

    // sh:in - enumeration constraint
    if (propertyConstraint.in && value !== undefined) {
      if (!propertyConstraint.in.includes(value)) {
        violations.push({
          focusNode: data['@id'] || 'root',
          resultPath: path,
          resultMessage: `Property ${path} must be one of: ${propertyConstraint.in.join(', ')}`,
          resultSeverity: 'Violation',
          sourceConstraintComponent: 'sh:in',
          value
        });
      }
    }

    // sh:minInclusive - minimum value (inclusive)
    if (propertyConstraint.minInclusive !== undefined && typeof value === 'number') {
      if (value < propertyConstraint.minInclusive) {
        violations.push({
          focusNode: data['@id'] || 'root',
          resultPath: path,
          resultMessage: `Property ${path} must be >= ${propertyConstraint.minInclusive}`,
          resultSeverity: 'Violation',
          sourceConstraintComponent: 'sh:minInclusive',
          value
        });
      }
    }

    // sh:maxInclusive - maximum value (inclusive)
    if (propertyConstraint.maxInclusive !== undefined && typeof value === 'number') {
      if (value > propertyConstraint.maxInclusive) {
        violations.push({
          focusNode: data['@id'] || 'root',
          resultPath: path,
          resultMessage: `Property ${path} must be <= ${propertyConstraint.maxInclusive}`,
          resultSeverity: 'Violation',
          sourceConstraintComponent: 'sh:maxInclusive',
          value
        });
      }
    }

    // sh:pattern - regex pattern
    if (propertyConstraint.pattern && typeof value === 'string') {
      const regex = new RegExp(propertyConstraint.pattern);
      if (!regex.test(value)) {
        violations.push({
          focusNode: data['@id'] || 'root',
          resultPath: path,
          resultMessage: `Property ${path} must match pattern: ${propertyConstraint.pattern}`,
          resultSeverity: 'Violation',
          sourceConstraintComponent: 'sh:pattern',
          value
        });
      }
    }

    return violations;
  }

  /**
   * Validate business constraints from ontology
   */
  validateConstraints(data, constraints, context = {}) {
    const violations = [];

    // Example: minMarginPct constraint for markdown decisions
    if (constraints.minMarginPct !== undefined) {
      const marginPct = data.marginPct || data.margin_pct;
      if (marginPct !== undefined && marginPct < constraints.minMarginPct) {
        violations.push({
          focusNode: data['@id'] || 'root',
          resultPath: 'marginPct',
          resultMessage: `Margin percentage ${marginPct}% is below minimum ${constraints.minMarginPct}%`,
          resultSeverity: 'Violation',
          sourceConstraintComponent: 'ex:minMarginPct',
          value: marginPct
        });
      }
    }

    // Example: floorPrice constraint
    if (constraints.floorPrice !== undefined) {
      const price = data.price || data.newPrice;
      if (price !== undefined && price < constraints.floorPrice) {
        violations.push({
          focusNode: data['@id'] || 'root',
          resultPath: 'price',
          resultMessage: `Price ${price} is below floor price ${constraints.floorPrice}`,
          resultSeverity: 'Violation',
          sourceConstraintComponent: 'ex:floorPrice',
          value: price
        });
      }
    }

    return violations;
  }

  /**
   * Get value at JSON path
   */
  getValueAtPath(data, path) {
    const parts = path.split('.');
    let current = data;
    
    for (const part of parts) {
      if (current === undefined || current === null) {
        return undefined;
      }
      current = current[part];
    }
    
    return current;
  }

  /**
   * Validate datatype
   */
  validateDatatype(value, datatype) {
    switch (datatype) {
      case 'xsd:string':
        return typeof value === 'string';
      case 'xsd:integer':
      case 'xsd:int':
        return Number.isInteger(value);
      case 'xsd:decimal':
      case 'xsd:double':
      case 'xsd:float':
        return typeof value === 'number';
      case 'xsd:boolean':
        return typeof value === 'boolean';
      case 'xsd:dateTime':
        return typeof value === 'string' && !isNaN(Date.parse(value));
      case 'xsd:date':
        return typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value);
      default:
        return true; // Unknown datatype, pass validation
    }
  }

  /**
   * Validate with category-specific constraints
   */
  async validateWithCategoryConstraints(data, shapeUri, categoryUri) {
    // Get category constraints if provided
    let categoryConstraints = {};
    if (categoryUri) {
      categoryConstraints = await this.ontologyService.getConstraints(categoryUri);
    }

    // Fetch shape
    const shape = await this.ontologyService.getShape(shapeUri);
    if (!shape) {
      throw new Error(`SHACL shape not found: ${shapeUri}`);
    }

    // Merge category constraints into shape
    const mergedShape = {
      ...shape,
      constraints: {
        ...(shape.constraints || {}),
        ...categoryConstraints
      }
    };

    // Create temporary shape for validation
    const originalGetShape = this.ontologyService.getShape.bind(this.ontologyService);
    this.ontologyService.getShape = async (uri) => {
      if (uri === shapeUri) {
        return mergedShape;
      }
      return originalGetShape(uri);
    };

    const result = await this.validate(data, shapeUri, { categoryConstraints });

    // Restore original method
    this.ontologyService.getShape = originalGetShape;

    return result;
  }
}

// Singleton instance
let shaclValidator = null;

export function getSHACLValidator() {
  if (!shaclValidator) {
    shaclValidator = new SHACLValidator();
  }
  return shaclValidator;
}

export default SHACLValidator;

