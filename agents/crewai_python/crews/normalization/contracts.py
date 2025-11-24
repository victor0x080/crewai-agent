"""
Agent I/O Contracts for Data Normalization Crew

Defines explicit input/output schemas for each agent using Pydantic models.
Enforces consistency, enables testing, and provides clear API boundaries.

Pattern:
- Each agent has XxxAgentInput and XxxAgentOutput models
- All outputs include confidence, rationale, and sources
- Standard error/abstain patterns for low-confidence cases
"""
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum


# =============================================================================
# COMMON MODELS
# =============================================================================

class ConfidenceLevel(str, Enum):
    """Standard confidence levels"""
    HIGH = "high"      # ≥ 0.85
    MEDIUM = "medium"  # 0.70 - 0.84
    LOW = "low"        # 0.60 - 0.69
    ABSTAIN = "abstain"  # < 0.60


class DecisionStatus(str, Enum):
    """Decision outcome status"""
    SUCCESS = "success"
    PARTIAL = "partial"  # Some fields mapped
    ABSTAIN = "abstain"  # Cannot decide
    ERROR = "error"      # Processing error


class FieldDecision(BaseModel):
    """Standard decision object for a single field"""
    field_name: str = Field(..., description="Target CDM field name")
    source_field: Optional[str] = Field(None, description="Source field name if mapped")
    value: Any = Field(..., description="Normalized value")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")
    confidence_level: ConfidenceLevel = Field(..., description="Categorical confidence")
    rationale: str = Field(..., description="Human-readable explanation")
    method: str = Field(..., description="How value was derived: 'rule', 'ml', 'llm', 'vector', 'ontology'")
    sources: List[str] = Field(default_factory=list, description="Evidence sources")
    alternatives: Optional[List[Dict[str, Any]]] = Field(None, description="Alternative options with confidence")
    
    @validator('confidence_level', pre=True, always=True)
    def set_confidence_level(cls, v, values):
        """Auto-set confidence level from confidence score"""
        if v:
            return v
        confidence = values.get('confidence', 0)
        if confidence >= 0.85:
            return ConfidenceLevel.HIGH
        elif confidence >= 0.70:
            return ConfidenceLevel.MEDIUM
        elif confidence >= 0.60:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.ABSTAIN


class ErrorDetail(BaseModel):
    """Standard error structure"""
    error_code: str = Field(..., description="Machine-readable error code")
    error_message: str = Field(..., description="Human-readable error message")
    field_name: Optional[str] = Field(None, description="Field that caused error")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional error context")


# =============================================================================
# SCHEMA DISCOVERY AGENT
# =============================================================================

class SchemaDiscoveryAgentInput(BaseModel):
    """Input for schema discovery agent"""
    raw_data: Dict[str, Any] = Field(..., description="Raw data record")
    source: str = Field(..., description="Data source identifier")
    source_schema: Optional[Dict[str, Any]] = Field(None, description="Known source schema if available")
    sample_records: Optional[List[Dict[str, Any]]] = Field(None, description="Additional sample records for pattern detection")


class FieldMapping(BaseModel):
    """Mapping from source field to CDM field"""
    source_field: str
    target_field: str
    target_table: str
    field_type: Literal["dimension", "metric", "attribute"]
    owner_agent_id: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    confidence_level: ConfidenceLevel
    method: str  # 'regex', 'ml_classifier', 'vector_similarity', 'ontology', 'llm'
    rationale: str
    sample_values: List[Any] = Field(default_factory=list)


class SchemaDiscoveryAgentOutput(BaseModel):
    """Output from schema discovery agent"""
    status: DecisionStatus
    field_mappings: List[FieldMapping] = Field(default_factory=list, description="Discovered field mappings")
    coverage: float = Field(..., ge=0.0, le=1.0, description="% of source fields mapped")
    overall_confidence: float = Field(..., ge=0.0, le=1.0, description="Average confidence across mappings")
    unmapped_fields: List[str] = Field(default_factory=list, description="Fields that couldn't be mapped")
    routing_recommendations: Dict[str, str] = Field(default_factory=dict, description="Which specialist agent should handle each field")
    warnings: List[str] = Field(default_factory=list)
    errors: List[ErrorDetail] = Field(default_factory=list)
    execution_time_ms: Optional[float] = None


# =============================================================================
# METRICS & TIME NORMALIZATION AGENT
# =============================================================================

class MetricsTimeAgentInput(BaseModel):
    """Input for metrics and time normalization"""
    raw_metrics: Dict[str, Any] = Field(..., description="Raw metric values")
    field_mappings: List[FieldMapping] = Field(..., description="Field mappings from schema discovery")
    source: str


class MetricNormalization(BaseModel):
    """Normalized metric with validation"""
    metric_name: str  # impressions_count, clicks_count, etc.
    raw_value: Any
    normalized_value: float
    unit: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    confidence_level: ConfidenceLevel
    method: str
    rationale: str
    validation_passed: bool
    validation_warnings: List[str] = Field(default_factory=list)


class MetricsTimeAgentOutput(BaseModel):
    """Output from metrics/time normalization"""
    status: DecisionStatus
    normalized_metrics: List[MetricNormalization] = Field(default_factory=list)
    normalized_timestamp: Optional[datetime] = Field(None, description="Normalized timestamp (UTC)")
    time_key: Optional[int] = Field(None, description="YYYYMMDD format for dim_time")
    cross_metric_validations: Dict[str, bool] = Field(default_factory=dict, description="E.g., clicks <= impressions")
    warnings: List[str] = Field(default_factory=list)
    errors: List[ErrorDetail] = Field(default_factory=list)
    execution_time_ms: Optional[float] = None


# =============================================================================
# PRODUCT TAXONOMY AGENT
# =============================================================================

class ProductTaxonomyAgentInput(BaseModel):
    """Input for product taxonomy normalization"""
    raw_product_data: Dict[str, Any] = Field(..., description="Raw product fields")
    product_id: Optional[str] = None
    product_title: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    source: str


class ProductNormalization(BaseModel):
    """Normalized product with taxonomy mapping"""
    product_id: str
    product_id_type: str  # 'GTIN-14', 'UPC-12', 'ASIN', 'SKU'
    product_title: Optional[str] = None
    brand: Optional[str] = None
    manufacturer: Optional[str] = None
    category_uri: str
    subcategory_uri: Optional[str] = None
    taxonomy_version: str = "v1.0"
    confidence: float = Field(..., ge=0.0, le=1.0)
    confidence_level: ConfidenceLevel
    method: str
    rationale: str
    taxonomy_path: Optional[str] = Field(None, description="Full category path")


class ProductTaxonomyAgentOutput(BaseModel):
    """Output from product taxonomy agent"""
    status: DecisionStatus
    normalized_product: Optional[ProductNormalization] = None
    product_key: Optional[int] = Field(None, description="Surrogate key from dim_product")
    needs_dimension_insert: bool = Field(False, description="Whether new dim_product row needed")
    warnings: List[str] = Field(default_factory=list)
    errors: List[ErrorDetail] = Field(default_factory=list)
    execution_time_ms: Optional[float] = None


# =============================================================================
# CAMPAIGN TACTIC AGENT
# =============================================================================

class CampaignTacticAgentInput(BaseModel):
    """Input for campaign tactic normalization"""
    raw_campaign_data: Dict[str, Any]
    campaign_id: str
    campaign_name: Optional[str] = None
    rmn_source: str


class CampaignNormalization(BaseModel):
    """Normalized campaign with tactic classification"""
    campaign_id: str
    campaign_name: str
    rmn_source: str
    tactic_uri: str
    ad_format: str
    objective: Optional[str] = None
    funnel_stage: Optional[str] = None
    targeting_type: Optional[str] = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    confidence_level: ConfidenceLevel
    method: str
    rationale: str
    parsed_components: Optional[Dict[str, str]] = Field(None, description="Extracted name components")


class CampaignTacticAgentOutput(BaseModel):
    """Output from campaign tactic agent"""
    status: DecisionStatus
    normalized_campaign: Optional[CampaignNormalization] = None
    campaign_key: Optional[int] = Field(None, description="Surrogate key from dim_campaign")
    needs_dimension_insert: bool = Field(False)
    warnings: List[str] = Field(default_factory=list)
    errors: List[ErrorDetail] = Field(default_factory=list)
    execution_time_ms: Optional[float] = None


# =============================================================================
# POS & PROMO AGENT
# =============================================================================

class POSPromoAgentInput(BaseModel):
    """Input for POS/promotion normalization"""
    raw_pos_data: Dict[str, Any]
    store_id: Optional[str] = None
    product_id: Optional[str] = None
    transaction_date: Optional[str] = None
    source: str


class PromoNormalization(BaseModel):
    """Normalized promotion details"""
    has_promotion: bool
    promo_type: Optional[str] = None  # 'TPR', 'BOGO', 'coupon', 'display'
    promo_discount_pct: Optional[float] = None
    has_display: bool = False
    display_type: Optional[str] = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    confidence_level: ConfidenceLevel
    method: str
    rationale: str


class POSPromoAgentOutput(BaseModel):
    """Output from POS/promo agent"""
    status: DecisionStatus
    units_sold: Optional[int] = None
    revenue_amount: Optional[float] = None
    cost_amount: Optional[float] = None
    margin_amount: Optional[float] = None
    promo_details: Optional[PromoNormalization] = None
    store_key: Optional[int] = None
    product_key: Optional[int] = None
    time_key: Optional[int] = None
    warnings: List[str] = Field(default_factory=list)
    errors: List[ErrorDetail] = Field(default_factory=list)
    execution_time_ms: Optional[float] = None


# =============================================================================
# AUDIENCE SEGMENT AGENT
# =============================================================================

class AudienceSegmentAgentInput(BaseModel):
    """Input for audience segment normalization"""
    raw_audience_data: Dict[str, Any]
    audience_id: Optional[str] = None
    audience_name: Optional[str] = None
    segment_label: Optional[str] = None
    rmn_source: str


class AudienceNormalization(BaseModel):
    """Normalized audience segment"""
    audience_id: str
    audience_name: str
    rmn_source: str
    lifecycle_stage: Optional[str] = None
    value_tier: Optional[str] = None
    tenure_days: Optional[int] = None
    recency_days: Optional[int] = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    confidence_level: ConfidenceLevel
    method: str
    rationale: str
    parsed_attributes: Optional[Dict[str, Any]] = None


class AudienceSegmentAgentOutput(BaseModel):
    """Output from audience segment agent"""
    status: DecisionStatus
    normalized_audience: Optional[AudienceNormalization] = None
    audience_key: Optional[int] = None
    needs_dimension_insert: bool = Field(False)
    warnings: List[str] = Field(default_factory=list)
    errors: List[ErrorDetail] = Field(default_factory=list)
    execution_time_ms: Optional[float] = None


# =============================================================================
# KPI ATTRIBUTION AGENT
# =============================================================================

class KPIAttributionAgentInput(BaseModel):
    """Input for KPI attribution normalization"""
    raw_kpi_data: Dict[str, Any]
    kpi_name: Optional[str] = None
    kpi_definition: Optional[str] = None
    attribution_window: Optional[str] = None
    source: str


class KPINormalization(BaseModel):
    """Normalized KPI definition"""
    kpi_id: str
    kpi_name: str
    kpi_family: str
    formula: Optional[str] = None
    attribution_window_days: Optional[int] = None
    attribution_model: Optional[str] = None
    is_incremental: bool = False
    baseline_definition: Optional[str] = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    confidence_level: ConfidenceLevel
    method: str
    rationale: str


class KPIAttributionAgentOutput(BaseModel):
    """Output from KPI attribution agent"""
    status: DecisionStatus
    normalized_kpi: Optional[KPINormalization] = None
    kpi_key: Optional[int] = None
    needs_dimension_insert: bool = Field(False)
    warnings: List[str] = Field(default_factory=list)
    errors: List[ErrorDetail] = Field(default_factory=list)
    execution_time_ms: Optional[float] = None


# =============================================================================
# QA GOVERNANCE AGENT
# =============================================================================

class QAGovernanceAgentInput(BaseModel):
    """Input for QA validation"""
    normalized_data: Dict[str, Any] = Field(..., description="All normalized outputs")
    target_table: str = Field(..., description="Target fact/dimension table")
    source: str


class ValidationResult(BaseModel):
    """Result of a single validation check"""
    check_name: str
    check_type: Literal["field_validation", "cross_field", "shacl", "anomaly"]
    passed: bool
    severity: Literal["error", "warning", "info"]
    message: str
    affected_fields: List[str] = Field(default_factory=list)
    constraint_violated: Optional[str] = None


class QAGovernanceAgentOutput(BaseModel):
    """Output from QA governance agent"""
    status: DecisionStatus
    overall_valid: bool = Field(..., description="All critical checks passed")
    validation_results: List[ValidationResult] = Field(default_factory=list)
    quality_score: float = Field(..., ge=0.0, le=1.0, description="Overall data quality 0-1")
    errors_count: int = 0
    warnings_count: int = 0
    shacl_conforms: bool = True
    shacl_violations: List[Dict[str, Any]] = Field(default_factory=list)
    anomalies_detected: List[Dict[str, Any]] = Field(default_factory=list)
    recommended_action: Literal["accept", "review", "reject"] = "accept"
    execution_time_ms: Optional[float] = None


# =============================================================================
# ORCHESTRATOR AGENT
# =============================================================================

class OrchestratorAgentInput(BaseModel):
    """Input for orchestrator"""
    schema_discovery_output: SchemaDiscoveryAgentOutput
    specialist_outputs: Dict[str, Any] = Field(..., description="Outputs from all specialists")
    source: str


class OrchestratorAgentOutput(BaseModel):
    """Output from orchestrator (merged final record)"""
    status: DecisionStatus
    merged_record: Dict[str, Any] = Field(..., description="Final normalized record")
    target_table: str
    field_lineage: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Transformation lineage per field")
    overall_confidence: float = Field(..., ge=0.0, le=1.0)
    agents_executed: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    errors: List[ErrorDetail] = Field(default_factory=list)
    execution_time_ms: Optional[float] = None


# =============================================================================
# MANAGER (FINAL OUTPUT)
# =============================================================================

class DataNormalizationManagerOutput(BaseModel):
    """Final output from the manager (published to target stream)"""
    status: DecisionStatus
    normalization_run_id: str = Field(..., description="UUID for this normalization run")
    
    # Normalized data
    normalized_data: Dict[str, Any]
    target_table: str
    target_schema_uri: str
    
    # Quality metadata
    overall_confidence: float = Field(..., ge=0.0, le=1.0)
    quality_score: float = Field(..., ge=0.0, le=1.0)
    
    # Validation
    schema_valid: bool
    shacl_valid: bool
    qa_passed: bool
    
    # Lineage
    mapping_log: List[FieldDecision] = Field(default_factory=list)
    transformation_lineage: Dict[str, Any] = Field(default_factory=dict)
    
    # Warnings/Errors
    warnings: List[str] = Field(default_factory=list)
    errors: List[ErrorDetail] = Field(default_factory=list)
    
    # Actions
    recommended_action: Literal["accept", "review", "reject"] = "accept"
    requires_human_review: bool = False
    review_reason: Optional[str] = None
    
    # Metadata
    source: str
    source_event_id: str
    agents_executed: List[str] = Field(default_factory=list)
    total_execution_time_ms: float
    normalized_at: datetime = Field(default_factory=datetime.utcnow)
    
    # CloudEvents metadata
    cloudevent_id: str
    cloudevent_type: str = "com.acme.normalization.complete"
    cloudevent_source: str = "data-normalization-manager"


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_field_decision(
    field_name: str,
    value: Any,
    confidence: float,
    method: str,
    rationale: str,
    source_field: Optional[str] = None,
    sources: Optional[List[str]] = None
) -> FieldDecision:
    """Helper to create a standard field decision object"""
    return FieldDecision(
        field_name=field_name,
        source_field=source_field,
        value=value,
        confidence=confidence,
        confidence_level=ConfidenceLevel.HIGH if confidence >= 0.85 else
                        ConfidenceLevel.MEDIUM if confidence >= 0.70 else
                        ConfidenceLevel.LOW if confidence >= 0.60 else
                        ConfidenceLevel.ABSTAIN,
        rationale=rationale,
        method=method,
        sources=sources or []
    )


def create_error(
    error_code: str,
    error_message: str,
    field_name: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> ErrorDetail:
    """Helper to create a standard error object"""
    return ErrorDetail(
        error_code=error_code,
        error_message=error_message,
        field_name=field_name,
        context=context
    )

