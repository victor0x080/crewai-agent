# Ontology Mechanism Usage - Examples

## Overview
The ontology mechanism is used in **8 main scenarios**. Here are practical examples:

---

## Example 1: Agent Discovery (Finding the Right Agent)

### Scenario
**User asks**: "Optimize pricing for Coca-Cola products"

### What Happens
```typescript
// 1. System extracts concepts from user query
const concepts = ['pricing', 'optimization', 'coca-cola'];

// 2. Resolve terms to ontology URIs
const resolved = await ontology.resolve('pricing');
// → 'ex:Price'

// 3. Expand concepts to find related agents
const expanded = await ontology.expand(
  ['ex:Price', 'ex:Optimization'],
  ['broader', 'narrower', 'related']
);
// → ['ex:Price', 'ex:Markdown', 'ex:Margin', 'ex:Optimization', 'ex:Analysis', ...]

// 4. Find agents interested in these concepts
const agents = await ontology.findInterestedAgents(expanded);
// → [
//     { agent_id: 'price-optimizer-agent', confidence: 0.95 },
//     { agent_id: 'markdown-planner-agent', confidence: 0.88 },
//     { agent_id: 'margin-analyzer-agent', confidence: 0.82 }
//   ]

// 5. Route to best agent
// → Routes to 'price-optimizer-agent'
```

### Real Code Location
- `src/services/agent-discovery/UnifiedAgentDiscovery.ts` (Line 107-130)
- `src/services/redis-mesh/SemanticRouterMeshBridge.ts` (Line 204-229)

---

## Example 2: Concept Resolution (Understanding Terms)

### Scenario
**Agent receives**: "Need to handle markdown for beverages"

### What Happens
```python
# Agent uses ontology tool to understand terms
from tools.ontology_tools import resolve_concept

# Resolve "markdown" to canonical URI
uri = resolve_concept('markdown')
# → 'ex:Markdown'

# Now agent knows:
# - "markdown" = "ex:Markdown" = price reduction
# - Related to: ex:Price, ex:Discount, ex:Promotion
# - Has constraints: minMarginPct, floorPrice
```

### Real Code Location
- `src/agents/crewai_python/product_agents.py` (Line 63-66)
- Every agent gets `resolve_concept` tool automatically

---

## Example 3: Constraint Enforcement (Business Rules)

### Scenario
**Agent wants to set price**: $0.50 for Beverages category

### What Happens
```python
from tools.ontology_tools import get_category_constraints

# 1. Get constraints for Beverages category
constraints = get_category_constraints('ex:Category/Beverages')
# → {
#     'minMarginPct': 0.15,  # Must maintain 15% margin
#     'floorPrice': 0.99      # Minimum price $0.99
#   }

# 2. Agent checks proposed price
proposed_price = 0.50
if proposed_price < constraints['floorPrice']:
    # ❌ REJECTED: Price $0.50 < floorPrice $0.99
    # Agent automatically adjusts to $0.99
    final_price = constraints['floorPrice']  # $0.99
```

### Real Code Location
- `src/services/ontology/ConstraintEnforcer.ts`
- `src/agents/crewai_python/product_agents.py` (Line 97-99)

---

## Example 4: SHACL Validation (Data Validation)

### Scenario
**Agent creates markdown decision** with data:
```json
{
  "sku": "COKE-12PK",
  "price": 0.75,
  "category": "Beverages",
  "discount": 0.30
}
```

### What Happens
```typescript
// 1. Validate against SHACL shape
const result = await shaclValidator.validateWithCategoryConstraints(
  data,
  'ex:MarkdownDecisionShape',
  'ex:Category/Beverages'
);

// 2. Validation fails because:
// - price (0.75) < floorPrice (0.99) ❌
// - discount (0.30) is OK ✅

// 3. Returns violations
{
  conforms: false,
  violations: [
    {
      resultPath: 'price',
      resultMessage: 'Price 0.75 is below floor price 0.99',
      resultSeverity: 'Violation'
    }
  ]
}

// 4. Agent fixes and retries with price = 0.99
```

### Real Code Location
- `src/services/ontology/SHACLValidator.ts`
- `src/api/routes/ontology-routes.ts` (POST /validate-shacl)

---

## Example 5: Concept Expansion (Finding Related Concepts)

### Scenario
**User asks**: "Find agents for campaign optimization"

### What Happens
```typescript
// 1. Start with concepts
const concepts = ['ex:Campaign', 'ex:Optimization'];

// 2. Expand via SKOS relations
const expanded = await ontology.expand(
  concepts,
  ['broader', 'narrower', 'related'],
  1 // depth
);

// 3. Gets expanded list
// → [
//     'ex:Campaign',           // original
//     'ex:Optimization',       // original
//     'ex:Marketing',          // broader (Campaign is narrower than Marketing)
//     'ex:Budget',             // related (Campaign uses Budget)
//     'ex:Analysis',           // broader (Optimization is narrower than Analysis)
//     'ex:Forecast',           // related (Optimization uses Forecast)
//     'ex:Attribution'         // related (Campaign needs Attribution)
//   ]

// 4. Now finds agents interested in ANY of these concepts
// → Finds more agents than just "campaign optimization"
```

### Real Code Location
- `src/services/agent-discovery/UnifiedAgentDiscovery.ts` (Line 154-180)
- `src/services/redis-mesh/SemanticRouterMeshBridge.ts` (Line 204-208)

---

## Example 6: Enum Mapping (Translating Values)

### Scenario
**System A sends**: `channel: "online"`  
**System B expects**: `channel: "ecom"`

### What Happens
```python
from tools.ontology_tools import map_enum

# Map value between systems
canonical_value = map_enum('channel', 'online')
# → 'ecom'

# Now agent can use 'ecom' for System B
```

### Real Code Location
- `src/services/ontology/OntologyService.ts` (mapEnum method)
- `src/agents/crewai_python/tools/ontology_tools.py` (map_enum tool)

---

## Example 7: Cross-System ID Translation

### Scenario
**Agent has**: Shopify product ID `shopify:prod_123`  
**Needs**: Internal database ID

### What Happens
```typescript
// Get internal ID for Shopify product
const internalId = await ontology.sameAs(
  'shopify:prod_123',
  'internal'
);
// → 'ent:product_456'

// Now agent can query internal database
const product = await db.query(`SELECT * FROM products WHERE id = '${internalId}'`);
```

### Real Code Location
- `src/services/ontology/OntologyService.ts` (sameAs method)
- `src/api/routes/ontology-routes.ts` (GET /same-as/:entityUri/:system)

---

## Example 8: Python Agent Using Ontology

### Scenario
**Price Optimization Agent** receives event: "Price change for Coca-Cola"

### What Happens
```python
from tools.ontology_tools import (
    resolve_concept,
    expand_concepts,
    get_category_constraints
)

# 1. Resolve "price" to ontology concept
price_concept = resolve_concept('price')
# → 'ex:Price'

# 2. Expand to get related concepts
related = expand_concepts(['ex:Price'], ['related'])
# → ['ex:Price', 'ex:Markdown', 'ex:Margin', 'ex:Inventory']

# 3. Get constraints for Beverages category
constraints = get_category_constraints('ex:Category/Beverages')
# → {'minMarginPct': 0.15, 'floorPrice': 0.99}

# 4. Agent uses constraints to validate decision
if new_price < constraints['floorPrice']:
    new_price = constraints['floorPrice']  # Enforce floor price

# 5. Agent makes decision with validated price
decision = {
    'sku': 'COKE-12PK',
    'new_price': new_price,  # $0.99 (enforced)
    'margin_pct': 0.18,      # > 0.15 ✅
    'reason': 'Price optimized within constraints'
}
```

### Real Code Location
- `src/agents/crewai_python/product_agents.py` (All product agents)
- `src/agents/crewai_python/factory/agent_factory.py` (Line 377-382)

---

## Complete Workflow Example

### Scenario
**User**: "Optimize the marketing campaign for Beverages with a $10,000 budget"

### Step-by-Step Flow

```typescript
// STEP 1: Parse user query
const query = "Optimize the marketing campaign for Beverages with a $10,000 budget";
const concepts = ['optimize', 'campaign', 'beverages', 'budget'];

// STEP 2: Resolve concepts to URIs
const resolved = await Promise.all([
  ontology.resolve('optimize'),    // → 'ex:Optimization'
  ontology.resolve('campaign'),   // → 'ex:Campaign'
  ontology.resolve('beverages'),  // → 'ex:Category/Beverages'
  ontology.resolve('budget')       // → 'ex:Budget'
]);

// STEP 3: Expand concepts
const expanded = await ontology.expand(
  ['ex:Optimization', 'ex:Campaign', 'ex:Budget'],
  ['broader', 'narrower', 'related']
);
// → ['ex:Optimization', 'ex:Campaign', 'ex:Budget', 'ex:Marketing', 
//    'ex:Analysis', 'ex:Forecast', 'ex:Attribution', ...]

// STEP 4: Find agents
const agents = await ontology.findInterestedAgents(expanded);
// → [
//     { agent_id: 'campaign-optimizer', confidence: 0.92 },
//     { agent_id: 'budget-planner', confidence: 0.85 },
//     { agent_id: 'marketing-analyst', confidence: 0.78 }
//   ]

// STEP 5: Route to best agent
const selectedAgent = agents[0]; // campaign-optimizer

// STEP 6: Agent gets constraints
const constraints = await ontology.getConstraints('ex:Category/Beverages');
// → { minMarginPct: 0.15, floorPrice: 0.99, minROAS: 2.0 }

// STEP 7: Agent validates decision
const decision = {
  budget: 10000,
  targetROAS: 2.5,  // > 2.0 ✅
  category: 'Beverages'
};

// STEP 8: Validate with SHACL
const validation = await shaclValidator.validate(
  decision,
  'ex:CampaignShape',
  'ex:Category/Beverages'
);
// → { conforms: true, violations: [] }

// STEP 9: Execute campaign optimization
// ✅ Success!
```

---

## Summary Table

| **When** | **What Ontology Does** | **Example** |
|----------|----------------------|-------------|
| **Agent Discovery** | Expands concepts to find agents | "pricing" → finds price-optimizer-agent |
| **Concept Resolution** | Maps terms to URIs | "markdown" → "ex:Markdown" |
| **Constraint Enforcement** | Applies business rules | Price $0.50 → rejected (floorPrice $0.99) |
| **SHACL Validation** | Validates data structure | Validates markdown decision against shape |
| **Concept Expansion** | Finds related concepts | "campaign" → ["campaign", "marketing", "budget"] |
| **Enum Mapping** | Translates values | "online" → "ecom" |
| **ID Translation** | Maps IDs between systems | "shopify:prod_123" → "ent:product_456" |
| **Agent Operations** | Every agent uses ontology | All Python agents have ontology tools |

---

## Key Takeaway

**Ontology is used whenever agents need to:**
1. ✅ **Understand** what something means (resolve)
2. ✅ **Find** related things (expand)
3. ✅ **Discover** other agents (findInterestedAgents)
4. ✅ **Validate** data (SHACL)
5. ✅ **Enforce** rules (constraints)
6. ✅ **Translate** between systems (mapEnum, sameAs)

**It's the "semantic glue" that makes agents understand each other!** 🧠🔗

