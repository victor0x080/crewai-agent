"""
Normalization Tools Library - Part 1: Core Tools

Reusable functions for data normalization agents.
Handles field detection, column mapping, and basic normalization.
"""
import re
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from dateutil import parser as date_parser
from crewai_tools import tool
import hashlib

# Caching
_cache: Dict[str, Any] = {}

def cache_key(*args) -> str:
    key_str = json.dumps(args, sort_keys=True)
    return hashlib.md5(key_str.encode()).hexdigest()

@tool("detect_field_type")
def detect_field_type(field_name: str, sample_values: List[Any]) -> Dict[str, Any]:
    """Detect semantic type of a field (metric, dimension, datetime, etc.)"""
    field_name_lower = field_name.lower()
    
    # Metric patterns
    if re.search(r'imp(r|ression)s?', field_name_lower):
        return {'field_type': 'metric', 'metric_subtype': 'impressions', 'confidence': 0.90, 'method': 'rule'}
    if re.search(r'clicks?', field_name_lower):
        return {'field_type': 'metric', 'metric_subtype': 'clicks', 'confidence': 0.90, 'method': 'rule'}
    if re.search(r'spend|cost', field_name_lower):
        return {'field_type': 'metric', 'metric_subtype': 'spend', 'confidence': 0.88, 'method': 'rule'}
    
    # Product ID
    if re.search(r'(product|sku|upc|asin).*id', field_name_lower):
        return {'field_type': 'product_id', 'confidence': 0.88, 'method': 'rule'}
    
    # Date
    if re.search(r'date|time|timestamp', field_name_lower):
        return {'field_type': 'datetime', 'confidence': 0.85, 'method': 'rule'}
    
    return {'field_type': 'unknown', 'confidence': 0.30, 'method': 'rule'}


@tool("infer_column_mapping")
def infer_column_mapping(source_field: str, sample_values: Optional[List[Any]] = None) -> Dict[str, Any]:
    """Infer CDM field mapping for a source column"""
    patterns = {
        'impressions_count': [r'imp(r|ression)s?'],
        'clicks_count': [r'clicks?'],
        'spend_amount': [r'spend|cost'],
        'product_id': [r'(product|sku|asin).*id']
    }
    
    source_lower = source_field.lower()
    for cdm_field, pats in patterns.items():
        for pat in pats:
            if re.search(pat, source_lower):
                return {'target_field': cdm_field, 'confidence': 0.80, 'method': 'rule'}
    
    return {'target_field': None, 'confidence': 0.20, 'method': 'rule'}


@tool("normalize_metric")
def normalize_metric(metric_name: str, value: Any) -> Dict[str, Any]:
    """Normalize metric value with validation"""
    try:
        normalized = float(value)
        warnings = []
        if normalized < 0:
            warnings.append(f"{metric_name} is negative")
        return {'normalized_value': normalized, 'validation_passed': len(warnings)==0, 'warnings': warnings, 'confidence': 0.95}
    except:
        return {'normalized_value': None, 'validation_passed': False, 'confidence': 0.0}


@tool("normalize_datetime")
def normalize_datetime(date_value: Any) -> Dict[str, Any]:
    """Normalize date to UTC and generate time_key"""
    try:
        if isinstance(date_value, str):
            dt = date_parser.parse(date_value)
        else:
            dt = datetime.fromtimestamp(date_value, tz=timezone.utc)
        dt = dt.astimezone(timezone.utc)
        time_key = int(dt.strftime("%Y%m%d"))
        return {'normalized_timestamp': dt.isoformat(), 'time_key': time_key, 'confidence': 0.98}
    except:
        return {'normalized_timestamp': None, 'time_key': None, 'confidence': 0.0}


@tool("normalize_product_id")
def normalize_product_id(product_id: str) -> Dict[str, Any]:
    """Normalize product ID and detect type"""
    product_id = str(product_id).strip()
    if re.match(r'^B[0-9A-Z]{9}$', product_id):
        return {'normalized_id': product_id, 'id_type': 'ASIN', 'confidence': 0.95}
    elif len(product_id) == 12 and product_id.isdigit():
        return {'normalized_id': product_id, 'id_type': 'UPC-12', 'confidence': 0.90}
    return {'normalized_id': product_id, 'id_type': 'SKU', 'confidence': 0.70}


@tool("classify_campaign_tactic")
def classify_campaign_tactic(campaign_name: str) -> Dict[str, Any]:
    """Classify campaign tactic from name"""
    campaign_lower = campaign_name.lower()
    if re.search(r'\bsp\b', campaign_lower):
        return {'tactic_uri': 'ex:SponsoredProduct', 'confidence': 0.92}
    if re.search(r'display', campaign_lower):
        return {'tactic_uri': 'ex:Display', 'confidence': 0.85}
    return {'tactic_uri': None, 'confidence': 0.30}


@tool("extract_promo_attributes")
def extract_promo_attributes(promo_description: Optional[str] = None) -> Dict[str, Any]:
    """Extract promotional attributes"""
    if not promo_description:
        return {'has_promotion': False, 'promo_type': None, 'confidence': 0.95}
    text_lower = promo_description.lower()
    if 'bogo' in text_lower:
        return {'has_promotion': True, 'promo_type': 'BOGO', 'confidence': 0.88}
    if 'tpr' in text_lower:
        return {'has_promotion': True, 'promo_type': 'TPR', 'confidence': 0.85}
    return {'has_promotion': True, 'promo_type': None, 'confidence': 0.60}


@tool("parse_audience_definition")
def parse_audience_definition(audience_name: str) -> Dict[str, Any]:
    """Parse audience segment definition"""
    text_lower = audience_name.lower()
    lifecycle = None
    if 'new' in text_lower: lifecycle = 'new'
    elif 'lapsed' in text_lower: lifecycle = 'lapsed'
    elif 'active' in text_lower: lifecycle = 'active'
    return {'lifecycle_stage': lifecycle, 'value_tier': None, 'confidence': 0.70 if lifecycle else 0.40}


@tool("extract_kpi_formula")
def extract_kpi_formula(kpi_name: str) -> Dict[str, Any]:
    """Extract KPI formula from name"""
    kpi_lower = kpi_name.lower()
    formulas = {'roas': 'revenue / spend', 'ctr': 'clicks / impressions * 100', 'cpm': 'spend / impressions * 1000'}
    for kpi, formula in formulas.items():
        if kpi in kpi_lower:
            return {'formula': formula, 'kpi_family': 'efficiency', 'confidence': 0.85}
    return {'formula': None, 'confidence': 0.45}


@tool("validate_data_quality")
def validate_data_quality(normalized_data: Dict[str, Any], target_table: str) -> Dict[str, Any]:
    """Perform data quality checks"""
    errors = []
    warnings = []
    
    # Check clicks <= impressions
    if 'clicks_count' in normalized_data and 'impressions_count' in normalized_data:
        if normalized_data['clicks_count'] > normalized_data['impressions_count']:
            errors.append('clicks > impressions')
    
    quality_score = 1.0 - (len(errors) * 0.2 + len(warnings) * 0.1)
    return {'quality_score': max(0, quality_score), 'errors': errors, 'warnings': warnings, 'overall_valid': len(errors)==0}

