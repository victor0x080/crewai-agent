"""
SHACL Validation Tools for CrewAI Agents
Provides semantic validation against SHACL shapes
"""

from crewai.tools import tool
import requests
import json
from typing import Optional

SHACL_VALIDATOR_URL = "http://localhost:5000/api/ontology/validate-shacl"
CONSTRAINTS_URL = "http://localhost:5000/api/ontology/constraints"


@tool("validate_shacl")
def validate_shacl(data: dict, shape_uri: str, category_uri: Optional[str] = None) -> str:
    """
    Validate data against a SHACL shape for semantic policy enforcement.
    
    Args:
        data: Data to validate
        shape_uri: SHACL shape URI (e.g., 'ex:Shape/MarkdownDecisionV1')
        category_uri: Optional category URI for category-specific constraints
    
    Returns:
        Validation result message
    """
    try:
        payload = {
            "data": data,
            "shape_uri": shape_uri
        }
        
        if category_uri:
            payload["category_uri"] = category_uri
        
        response = requests.post(SHACL_VALIDATOR_URL, json=payload, timeout=5)
        
        if response.status_code == 200:
            result = response.json()
            if result['conforms']:
                return f"✓ Data conforms to SHACL shape {shape_uri}"
            else:
                violations = '\n'.join([
                    f"  - {v['resultPath']}: {v['resultMessage']}" 
                    for v in result['violations']
                ])
                warnings = ''
                if result.get('warnings'):
                    warnings = '\nWarnings:\n' + '\n'.join([
                        f"  - {w['resultPath']}: {w['resultMessage']}" 
                        for w in result['warnings']
                    ])
                return f"✗ SHACL violations:\n{violations}{warnings}"
        else:
            return f"✗ SHACL validation failed: {response.text}"
    except requests.exceptions.Timeout:
        return "✗ SHACL validation timeout"
    except Exception as e:
        return f"✗ SHACL validation error: {str(e)}"


@tool("get_category_constraints")
def get_category_constraints(category_uri: str) -> dict:
    """
    Get policy constraints for a category (e.g., minMarginPct, floorPrice).
    
    Args:
        category_uri: Category URI (e.g., 'ex:Category/Beverages')
    
    Returns:
        Dictionary of constraints
    """
    try:
        import urllib.parse
        encoded_uri = urllib.parse.quote(category_uri, safe='')
        response = requests.get(f"{CONSTRAINTS_URL}/{encoded_uri}", timeout=5)
        
        if response.status_code == 200:
            return response.json()
        else:
            return {}
    except Exception as e:
        print(f"Error fetching category constraints: {e}")
        return {}


@tool("get_shacl_shape")
def get_shacl_shape(shape_uri: str) -> dict:
    """
    Get SHACL shape definition from the ontology.
    
    Args:
        shape_uri: SHACL shape URI (e.g., 'ex:Shape/MarkdownDecisionV1')
    
    Returns:
        SHACL shape definition
    """
    try:
        import urllib.parse
        encoded_uri = urllib.parse.quote(shape_uri, safe='')
        response = requests.get(f"http://localhost:5000/api/ontology/shape/{encoded_uri}", timeout=5)
        
        if response.status_code == 200:
            return response.json()
        else:
            return {}
    except Exception as e:
        print(f"Error fetching SHACL shape: {e}")
        return {}
