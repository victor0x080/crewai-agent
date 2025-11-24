# Ontology Integration Guide

## Overview

The ontology mechanism provides semantic interoperability for agents through:
- **SKOS Ontology**: Standard vocabulary for retail media concepts
- **SHACL Validation**: Semantic constraint validation
- **Concept Resolution**: Mapping terms to canonical URIs
- **Agent Discovery**: Finding agents by semantic interests

## Architecture

```
┌─────────────────┐
│  Python Agents  │
│  (CrewAI)      │
└────────┬────────┘
         │ REST API
         ▼
┌─────────────────┐
│ Ontology Routes │
│ /api/ontology   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ OntologyService │
│ (JavaScript)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Supabase DB   │
│  (PostgreSQL)   │
└─────────────────┘
```

## Database Schema

The ontology uses 5 main tables:

1. **ontology_concepts** - SKOS concepts with labels, definitions, and relationships
2. **ontology_mappings** - Enum/unit/ID translations between systems
3. **ontology_constraints** - Business policy constraints (minMarginPct, floorPrice, etc.)
4. **ontology_shapes** - SHACL validation shapes
5. **agent_ontology_profiles** - Agent capability profiles

See `src/db/ontology_schema.sql` for full schema.

## Seed Data

The seed file (`src/db/seed_ontology.sql`) is based on the **Retail Media Manufacturer Ontology** structure and includes:

- Core Retail Media Network concepts (RMN, AdPlacement, Advertiser, Publisher, etc.)
- Marketing concepts (Campaign, Budget, Bid, Creative, Channel)
- Product concepts (Product, SKU, Category, Brand)
- Pricing concepts (Price, Markdown, Margin)
- Inventory concepts (Inventory, Stockout)
- Analytical concepts (Forecast, Analysis, Optimization, Attribution)

## Usage Examples

### JavaScript/TypeScript

```javascript
import { getOntologyService } from './services/ontology/OntologyService.js';

const ontology = getOntologyService();
await ontology.initialize();

// Resolve a term
const uri = await ontology.resolve('pricing'); // → 'ex:Price'

// Expand concepts
const expanded = await ontology.expand(['ex:Price'], ['broader', 'related']);
// → ['ex:Price', 'ex:Markdown', 'ex:Margin', ...]

// Get constraints
const constraints = await ontology.getConstraints('ex:Category/Beverages');
// → { minMarginPct: 0.15, floorPrice: 0.99 }
```

### Python (CrewAI Tools)

```python
from agents.crewai_python.tools.ontology_tools import (
    resolve_concept,
    expand_concepts,
    get_category_constraints
)

# Resolve concept
uri = resolve_concept('optimization')  # → 'ex:Optimization'

# Expand concepts
expanded = expand_concepts(['ex:Markdown'], ['broader', 'related'])

# Get constraints
constraints = get_category_constraints('ex:Category/Beverages')
```

### REST API

```bash
# Resolve term
curl http://localhost:5000/api/ontology/resolve/pricing

# Expand concepts
curl -X POST http://localhost:5000/api/ontology/expand \
  -H "Content-Type: application/json" \
  -d '{"concepts": ["ex:Markdown"], "relations": ["broader", "related"]}'

# Get constraints
curl http://localhost:5000/api/ontology/constraints/ex:Category/Beverages
```

## SHACL Validation

Validate data against semantic shapes:

```javascript
import { getSHACLValidator } from './services/ontology/SHACLValidator.js';

const validator = getSHACLValidator();
const result = await validator.validate(
  { price: 9.99, marginPct: 0.10 },
  'ex:MarkdownDecisionShape',
  'ex:Category/Beverages'
);

if (!result.conforms) {
  console.log('Violations:', result.violations);
}
```

## Agent Discovery

Find agents by semantic interests:

```javascript
const agents = await ontology.findInterestedAgents(['ex:Optimization', 'ex:Campaign']);
// Returns agents that match these concepts
```

## Configuration

Set environment variables:

```bash
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
ONTOLOGY_API_BASE=http://localhost:5000/api/ontology  # For Python agents
```

## Next Steps

1. **Run Database Schema**: Execute `src/db/ontology_schema.sql` in your Supabase database
2. **Seed Data**: Execute `src/db/seed_ontology.sql` to populate initial concepts
3. **Update Seed**: Add concepts from `Retail Media Manufacturer Ontology Seed.docx` to the seed file
4. **Register Routes**: Add ontology routes to your Express app:

```javascript
import ontologyRoutes from './api/routes/ontology-routes.js';
app.use('/api/ontology', ontologyRoutes);
```

5. **Initialize Service**: Initialize the ontology service on startup:

```javascript
import { getOntologyService } from './services/ontology/OntologyService.js';
const ontology = getOntologyService();
await ontology.initialize();
```

## References

- SKOS Specification: https://www.w3.org/TR/skos-reference/
- SHACL Specification: https://www.w3.org/TR/shacl/
- Retail Media Manufacturer Ontology Seed.docx (source document)

