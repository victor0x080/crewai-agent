"""
Ontology Tools for CrewAI Agents
Provides semantic concept resolution, expansion, and enum mapping
Following pattern from @ontology.md
"""

from crewai.tools import tool
import requests
from typing import List, Optional, Dict
import urllib.parse

# Base URL for ontology API
ONTOLOGY_API_BASE = "http://localhost:5000/api/ontology"


@tool("resolve_concept")
def resolve_concept(label: str) -> str:
    """
    Resolve a label to its ontology URI.
    
    Args:
        label: Human-readable label (e.g., 'high_intent', 'optimization', 'price')
    
    Returns:
        Ontology URI (e.g., 'ex:HighIntentAudience', 'ex:Optimization', 'schema:price')
    
    Example:
        resolve_concept('optimization') → 'ex:Optimization'
        resolve_concept('price') → 'schema:price'
    """
    try:
        encoded_label = urllib.parse.quote(label, safe='')
        response = requests.get(
            f"{ONTOLOGY_API_BASE}/resolve/{encoded_label}",
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get('uri', label)
        else:
            # Fallback: return label if not found
            return label
    except requests.exceptions.Timeout:
        return f"✗ Timeout resolving '{label}'"
    except Exception as e:
        return f"✗ Error resolving '{label}': {str(e)}"


@tool("expand_concepts")
def expand_concepts(concepts: List[str], relations: Optional[List[str]] = None, depth: int = 1) -> List[str]:
    """
    Expand concepts via SKOS semantic relations (broader, narrower, related).
    
    Args:
        concepts: List of concept URIs to expand (e.g., ['ex:Markdown', 'ex:Inventory'])
        relations: SKOS relations to follow (default: ['broader', 'narrower', 'related'])
        depth: How many hops to traverse (default: 1)
    
    Returns:
        List of expanded concept URIs including originals
    
    Example:
        expand_concepts(['ex:Markdown'], ['broader', 'related']) 
        → ['ex:Markdown', 'ex:Pricing', 'ex:Promotion', 'ex:Discount']
    """
    try:
        if relations is None:
            relations = ['broader', 'narrower', 'related']
        
        payload = {
            "concepts": concepts,
            "relations": relations,
            "depth": depth
        }
        
        response = requests.post(
            f"{ONTOLOGY_API_BASE}/expand",
            json=payload,
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get('expanded', concepts)
        else:
            # Fallback: return original concepts
            return concepts
    except requests.exceptions.Timeout:
        return concepts  # Return original on timeout
    except Exception as e:
        print(f"Error expanding concepts: {e}")
        return concepts


@tool("map_enum")
def map_enum(field: str, value: str) -> str:
    """
    Map an enum value to its canonical form using ontology mappings.
    
    Args:
        field: Field name (e.g., 'currency', 'channel', 'unit')
        value: Input value (e.g., 'USD', 'dollars', '$')
    
    Returns:
        Canonical value (e.g., 'USD')
    
    Example:
        map_enum('currency', 'dollars') → 'USD'
        map_enum('channel', 'fb') → 'Facebook'
        map_enum('unit', 'kg') → 'kilogram'
    """
    try:
        payload = {
            "field": field,
            "value": value
        }
        
        response = requests.post(
            f"{ONTOLOGY_API_BASE}/map-enum",
            json=payload,
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get('canonical', value)
        else:
            # Fallback: return original value
            return value
    except requests.exceptions.Timeout:
        return value
    except Exception as e:
        print(f"Error mapping enum: {e}")
        return value


@tool("get_category_constraints")
def get_category_constraints(category_uri: str) -> Dict:
    """
    Get policy constraints for a product category (e.g., minMarginPct, floorPrice).
    Uses SHACL constraints from the ontology.
    
    Args:
        category_uri: Category URI (e.g., 'ex:Category/Beverages', 'ex:Category/Electronics')
    
    Returns:
        Dictionary of constraints (e.g., {'minMarginPct': 15, 'floorPrice': 5.99})
    
    Example:
        get_category_constraints('ex:Category/Beverages') 
        → {'minMarginPct': 15, 'floorPrice': 5.99}
        
        get_category_constraints('ex:Category/Electronics')
        → {'minMarginPct': 20, 'floorPrice': 49.99}
    """
    try:
        encoded_uri = urllib.parse.quote(category_uri, safe='')
        response = requests.get(
            f"{ONTOLOGY_API_BASE}/constraints/{encoded_uri}",
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get('constraints', {})
        else:
            # Fallback: empty constraints
            return {}
    except requests.exceptions.Timeout:
        return {}
    except Exception as e:
        print(f"Error fetching category constraints: {e}")
        return {}


# Additional utility (not a tool, used by agent code)
def get_same_as_mappings(entity_uri: str, system: str) -> Optional[str]:
    """
    Get sameAs mapping for an entity to an external system.
    
    Args:
        entity_uri: Internal entity URI (e.g., 'ex:Product/SKU-1234')
        system: External system (e.g., 'google_merchant', 'facebook_catalog')
    
    Returns:
        External ID or None
    """
    try:
        encoded_uri = urllib.parse.quote(entity_uri, safe='')
        response = requests.get(
            f"{ONTOLOGY_API_BASE}/same-as/{encoded_uri}/{system}",
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get('external_id')
        else:
            return None
    except Exception as e:
        print(f"Error fetching sameAs mapping: {e}")
        return None
