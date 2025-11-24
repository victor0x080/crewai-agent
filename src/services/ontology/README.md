# Ontology Service

## Purpose
Knowledge graph integration for semantic routing, concept resolution, and policy enforcement using SKOS ontology and SHACL validation.

## Key Files
- `OntologyService.js` - Core service (resolve, expand, mapEnum, getConstraints)
- `SHACLValidator.js` - SHACL constraint validation
- `ConstraintEnforcer.js` - Business rule enforcement
- `AgentProfileValidator.js` - Agent capability validation

## Dependencies
- Database: `ontology_concepts`, `ontology_mappings`, `ontology_constraints`, `ontology_shapes`, `agent_ontology_profiles` tables
- Supabase: For database access
- Used by: API routes, Python agents via REST API

## Common Patterns

### Resolve Concept
```javascript
import { getOntologyService } from './services/ontology/OntologyService.js';

const service = getOntologyService();
await service.initialize();
const uri = await service.resolve('Pricing'); // → 'ex:Pricing'
```

### Expand Concepts (SKOS)
```javascript
const expanded = await service.expand(
  ['ex:Pricing'],
  ['broader', 'narrower', 'related']
); // → ['ex:Pricing', 'ex:Margin', 'ex:Elasticity', ...]
```

### Map Enum
```javascript
const uri = await service.mapEnum('currency', 'USD'); // → 'USD'
```

### Get Constraints
```javascript
const constraints = await service.getConstraints('ex:Category/Beverages');
// → { minMarginPct: 0.15, floorPrice: 0.99 }
```

## API Endpoints

The ontology service is exposed via REST API at `/api/ontology`:

- `GET /api/ontology/resolve/:term` - Resolve term to URI
- `POST /api/ontology/expand` - Expand concepts
- `GET /api/ontology/constraints/:conceptUri` - Get constraints
- `GET /api/ontology/shape/:shapeUri` - Get SHACL shape
- `POST /api/ontology/validate-shacl` - Validate data against SHACL
- `GET /api/ontology/same-as/:entityUri/:system` - Get external ID mapping

## Database Setup

1. Run the schema: `src/db/ontology_schema.sql`
2. Seed initial data: `src/db/seed_ontology.sql`

The seed file is based on the Retail Media Manufacturer Ontology structure.

## Python Integration

Python agents can use the ontology via:
- CrewAI tools: `agents/crewai_python/tools/ontology_tools.py`
- Python SDK: `python/sdk/ontology_integration.py`

Both connect to the REST API endpoints.

