/**
 * Ontology API Routes
 * Provides HTTP endpoints for ontology operations and SHACL validation
 */

import express from 'express';
import { getSHACLValidator } from '../../services/ontology/SHACLValidator.js';
import { getOntologyService } from '../../services/ontology/OntologyService.js';
import { logger } from '../../utils/logger.js';

const router = express.Router();
const shaclValidator = getSHACLValidator();
const ontologyService = getOntologyService();

/**
 * POST /api/ontology/validate-shacl
 * Validate data against SHACL shape
 */
router.post('/validate-shacl', async (req, res) => {
  try {
    const { data, shape_uri, category_uri } = req.body;

    if (!data || !shape_uri) {
      return res.status(400).json({ error: 'data and shape_uri are required' });
    }

    let result;
    if (category_uri) {
      result = await shaclValidator.validateWithCategoryConstraints(data, shape_uri, category_uri);
    } else {
      result = await shaclValidator.validate(data, shape_uri);
    }

    res.json(result);
  } catch (error) {
    logger.error('[OntologyRoutes] SHACL validation error:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * GET /api/ontology/constraints/:conceptUri
 * Get constraints for a concept/category
 */
router.get('/constraints/:conceptUri', async (req, res) => {
  try {
    const conceptUri = decodeURIComponent(req.params.conceptUri);
    const constraints = await ontologyService.getConstraints(conceptUri);
    res.json(constraints);
  } catch (error) {
    logger.error('[OntologyRoutes] Get constraints error:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * GET /api/ontology/shape/:shapeUri
 * Get SHACL shape definition
 */
router.get('/shape/:shapeUri', async (req, res) => {
  try {
    const shapeUri = decodeURIComponent(req.params.shapeUri);
    const shape = await ontologyService.getShape(shapeUri);
    
    if (!shape) {
      return res.status(404).json({ error: 'Shape not found' });
    }
    
    res.json(shape);
  } catch (error) {
    logger.error('[OntologyRoutes] Get shape error:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * GET /api/ontology/resolve/:term
 * Resolve term to canonical URI
 */
router.get('/resolve/:term', async (req, res) => {
  try {
    const term = decodeURIComponent(req.params.term);
    const uri = await ontologyService.resolve(term);
    
    if (!uri) {
      return res.status(404).json({ error: 'Term not found' });
    }
    
    res.json({ term, uri });
  } catch (error) {
    logger.error('[OntologyRoutes] Resolve error:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * POST /api/ontology/expand
 * Expand concepts using SKOS relations
 */
router.post('/expand', async (req, res) => {
  try {
    const { concepts, relations = ['broader', 'narrower', 'related'], depth = 1 } = req.body;

    if (!concepts || !Array.isArray(concepts)) {
      return res.status(400).json({ error: 'concepts array is required' });
    }

    const expanded = await ontologyService.expand(concepts, relations, depth);
    res.json({ concepts, expanded, count: expanded.length });
  } catch (error) {
    logger.error('[OntologyRoutes] Expand error:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * GET /api/ontology/same-as/:entityUri/:system
 * Get external ID for entity in different system
 */
router.get('/same-as/:entityUri/:system', async (req, res) => {
  try {
    const entityUri = decodeURIComponent(req.params.entityUri);
    const system = req.params.system;
    
    const externalId = await ontologyService.sameAs(entityUri, system);
    
    if (!externalId) {
      return res.status(404).json({ error: 'External ID not found' });
    }
    
    res.json({ entityUri, system, externalId });
  } catch (error) {
    logger.error('[OntologyRoutes] SameAs error:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * POST /api/ontology/warm-cache
 * Warm the ontology cache with hot concepts
 */
router.post('/warm-cache', async (req, res) => {
  try {
    // Warm cache by resolving common concepts
    const hotConcepts = [
      'ex:Markdown', 'ex:Price', 'ex:Inventory', 'ex:Campaign',
      'ex:Product', 'ex:SKU', 'ex:Channel', 'ex:Budget',
      'ex:Optimization', 'ex:Forecast', 'ex:Attribution',
      'ex:Bid', 'ex:Creative', 'ex:Category', 'ex:Brand',
      'ex:RetailMediaNetwork', 'ex:ROAS', 'ex:CPM', 'ex:CPC'
    ];
    
    for (const concept of hotConcepts) {
      await ontologyService.resolve(concept);
      await ontologyService.expand([concept], ['broader', 'related'], 1);
    }
    
    res.json({ success: true, message: 'Cache warmed successfully' });
  } catch (error) {
    logger.error('[OntologyRoutes] Warm cache error:', error);
    res.status(500).json({ error: error.message });
  }
});

/**
 * GET /api/ontology/search/:term
 * Search concepts by label
 */
router.get('/search/:term', async (req, res) => {
  try {
    const term = decodeURIComponent(req.params.term);
    const concepts = await ontologyService.searchConcepts(term);
    res.json({ term, concepts, count: concepts.length });
  } catch (error) {
    logger.error('[OntologyRoutes] Search error:', error);
    res.status(500).json({ error: error.message });
  }
});

export default router;

