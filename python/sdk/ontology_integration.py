"""
Ontology and Knowledge Graph Integration
==========================================

Provides external agents with access to Quest's semantic layer:
1. Ontology (SKOS) - Concept resolution and expansion
2. Knowledge Graph - Entity navigation and relationships
3. SHACL Validation - Semantic constraints
4. Agent Discovery - Find capable agents by concepts
5. Template Integration - Work with ACT-R templates

This enables semantic interoperability between external and internal agents.
"""

import requests
from typing import List, Dict, Optional, Any
import os

# Default API URL - can be configured via environment variable
DEFAULT_API_URL = os.getenv("ONTOLOGY_API_URL", "http://localhost:5000")


class OntologyClient:
    """Client for Quest Ontology Service"""
    
    def __init__(self, api_url: str = None):
        self.api_url = api_url or DEFAULT_API_URL
        self.base = f"{self.api_url}/api/ontology"
    
    def resolve(self, term: str) -> Optional[str]:
        """
        Resolve a term/label to its canonical URI
        
        Example:
            uri = ontology.resolve("pricing")
            # Returns: "ex:Pricing"
        """
        try:
            response = requests.get(f"{self.base}/resolve/{requests.utils.quote(term)}")
            if response.status_code == 200:
                return response.json().get("uri")
            return None
        except Exception as e:
            print(f"Error resolving term '{term}': {e}")
            return None
    
    def expand(
        self,
        concepts: List[str],
        relations: List[str] = None,
        depth: int = 1
    ) -> List[str]:
        """
        Expand concepts using SKOS relations
        
        Args:
            concepts: List of concept URIs
            relations: Types of relations ['broader', 'narrower', 'related', 'synonym']
            depth: How many hops to traverse
        
        Returns:
            Expanded list of concept URIs
        
        Example:
            expanded = ontology.expand(
                ["ex:Pricing"],
                relations=["broader", "related"],
                depth=1
            )
            # Returns: ["ex:Pricing", "ex:Revenue", "ex:Markdown", ...]
        """
        if relations is None:
            relations = ["broader", "narrower", "related"]
        
        try:
            response = requests.post(f"{self.base}/expand", json={
                "concepts": concepts,
                "relations": relations,
                "depth": depth
            })
            
            if response.status_code == 200:
                return response.json().get("expanded", [])
            return []
        except Exception as e:
            print(f"Error expanding concepts: {e}")
            return []
    
    def same_as(self, entity_uri: str, system: str) -> Optional[str]:
        """
        Get external ID for an entity in a different system
        
        Example:
            external_id = ontology.same_as("ent:product_123", "shopify")
            # Returns: "shopify:prod_xyz"
        """
        try:
            response = requests.get(
                f"{self.base}/same-as/{requests.utils.quote(entity_uri)}/{system}"
            )
            if response.status_code == 200:
                return response.json().get("externalId")
            return None
        except Exception as e:
            print(f"Error getting sameAs mapping: {e}")
            return None
    
    def get_constraints(self, concept_uri: str) -> Dict:
        """
        Get business constraints for a concept/category
        
        Example:
            constraints = ontology.get_constraints("cat:Beverages")
            # Returns: {"minMarginPct": 0.15, "floorPrice": 0.99, ...}
        """
        try:
            response = requests.get(
                f"{self.base}/constraints/{requests.utils.quote(concept_uri)}"
            )
            if response.status_code == 200:
                return response.json()
            return {}
        except Exception as e:
            print(f"Error getting constraints: {e}")
            return {}
    
    def get_shape(self, shape_uri: str) -> Optional[Dict]:
        """
        Get SHACL shape definition
        
        Example:
            shape = ontology.get_shape("shape:PriceEvent")
            # Returns: SHACL shape definition
        """
        try:
            response = requests.get(f"{self.base}/shape/{requests.utils.quote(shape_uri)}")
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Error getting shape: {e}")
            return None
    
    def validate_shacl(
        self,
        data: Dict,
        shape_uri: str,
        category_uri: Optional[str] = None
    ) -> Dict:
        """
        Validate data against SHACL shape
        
        Args:
            data: Data to validate
            shape_uri: SHACL shape URI
            category_uri: Optional category for additional constraints
        
        Returns:
            {
                "conforms": bool,
                "violations": [...],
                "warnings": [...]
            }
        
        Example:
            result = ontology.validate_shacl(
                data={"price": 9.99, "marginPct": 0.10},
                shape_uri="shape:PriceEvent",
                category_uri="cat:Beverages"
            )
            if not result["conforms"]:
                print("Violations:", result["violations"])
        """
        try:
            payload = {
                "data": data,
                "shape_uri": shape_uri
            }
            if category_uri:
                payload["category_uri"] = category_uri
            
            response = requests.post(f"{self.base}/validate-shacl", json=payload)
            if response.status_code == 200:
                return response.json()
            return {"conforms": False, "violations": ["Validation request failed"]}
        except Exception as e:
            print(f"Error validating SHACL: {e}")
            return {"conforms": False, "violations": [str(e)]}


# Helper functions for common patterns

def enrich_action_with_ontology(action: Dict, ontology: OntologyClient) -> Dict:
    """
    Enrich an action with ontology concepts
    
    Example:
        action = {
            "type": "pricing",
            "inputs": {"product": "beverage_cola"}
        }
        enriched = enrich_action_with_ontology(action, ontology)
        # Adds: enriched["@context"] = ["ex:Pricing", "cat:Beverages", ...]
    """
    enriched = action.copy()
    
    # Resolve action type to concept
    action_type = action.get("type", "")
    concept_uri = ontology.resolve(action_type)
    
    if concept_uri:
        # Expand to get related concepts
        expanded = ontology.expand([concept_uri], depth=1)
        enriched["@context"] = expanded
    
    # Resolve product category if present
    product = action.get("inputs", {}).get("product", "")
    if product:
        category_uri = ontology.resolve(product)
        if category_uri:
            enriched["inputs"]["@category"] = category_uri
            # Get business constraints for this category
            constraints = ontology.get_constraints(category_uri)
            enriched["inputs"]["@constraints"] = constraints
    
    return enriched


def validate_output_with_ontology(
    output: Dict,
    expected_shape: str,
    ontology: OntologyClient
) -> Dict:
    """
    Validate output against SHACL shape
    
    Example:
        result = validate_output_with_ontology(
            output={"price": 9.99, "marginPct": 0.10},
            expected_shape="shape:PriceEvent",
            ontology=ontology
        )
    """
    return ontology.validate_shacl(
        data=output,
        shape_uri=expected_shape,
        category_uri=output.get("@category")
    )

