"""
Federated Learning RAG Integration
===================================

Integrates FL results with the existing RAG architecture for analytics.

Architecture:
- FL numerical results → Feature Store + RAG documents
- FL model metadata → RAG documents with embeddings
- FL training metrics → Time-series + RAG summaries
- FL predictions → Feature Store + RAG explanations

This ensures FL outputs are discoverable and queryable like all other analytics.
"""

from typing import Dict, List, Any, Optional
from crewai_tools import tool
import requests
import json
from datetime import datetime
from pathlib import Path

# Service endpoints
RAG_SERVICE_URL = "http://localhost:3000/api/rag"
FEATURE_STORE_URL = "http://localhost:3000/api/features"
FL_API_URL = "http://localhost:3000/api/fl"

# Import existing RAG tools
import sys
sys.path.append(str(Path(__file__).parent))
from rag_tools import publish_analytics_event, link_numerical_to_evidence


# ===================================================================
# FL RESULT PUBLISHING TO RAG
# ===================================================================

@tool
def publish_fl_model_to_rag(
    model_version: str,
    run_id: str,
    metrics: Dict[str, float],
    model_metadata: Dict[str, Any],
    training_summary: str
) -> Dict[str, Any]:
    """
    Publish FL model results to RAG for discoverability.
    
    Creates a searchable document with:
    - Model performance metrics
    - Training configuration
    - Client participation
    - Convergence analysis
    
    Args:
        model_version: FL model version (e.g., 'fl_run_123_r5')
        run_id: FL run identifier
        metrics: Performance metrics (accuracy, f1, auc, etc.)
        model_metadata: Model configuration and metadata
        training_summary: Natural language summary of training
    
    Returns:
        {
            'document_id': str,
            'published_to_rag': bool,
            'published_to_feature_store': bool,
            'searchable': bool
        }
    
    Example:
        result = publish_fl_model_to_rag(
            model_version='fl_run_001_r5',
            run_id='fl_run_001',
            metrics={'accuracy': 0.87, 'f1': 0.85, 'auc': 0.89},
            model_metadata={
                'dataset': 'call_center_csat',
                'num_clients': 4,
                'num_rounds': 5,
                'strategy': 'FedAvg'
            },
            training_summary='Federated model trained on 4 call center data silos...'
        )
    """
    
    # Build RAG document
    document = {
        'title': f'Federated Learning Model: {model_version}',
        'content': _build_fl_model_document(
            model_version, run_id, metrics, model_metadata, training_summary
        ),
        'metadata': {
            'document_type': 'fl_model',
            'model_version': model_version,
            'run_id': run_id,
            'dataset': model_metadata.get('dataset'),
            'created_at': datetime.utcnow().isoformat(),
            'metrics': metrics,
            'tags': ['federated_learning', 'model', 'analytics']
        },
        'source': 'federated_learning_system',
        'url': f'/fl/models/{model_version}'
    }
    
    try:
        # 1. Publish to RAG service
        rag_response = requests.post(
            f"{RAG_SERVICE_URL}/ingest",
            json={'documents': [document]},
            timeout=10
        )
        rag_response.raise_for_status()
        rag_result = rag_response.json()
        document_id = rag_result.get('document_ids', [None])[0]
        
        # 2. Publish metrics to Feature Store
        feature_store_response = requests.post(
            f"{FEATURE_STORE_URL}/write",
            json={
                'entity_type': 'fl_model',
                'entity_id': model_version,
                'features': {
                    'accuracy': metrics.get('accuracy'),
                    'f1_score': metrics.get('f1'),
                    'auc': metrics.get('auc'),
                    'num_parameters': model_metadata.get('num_parameters')
                },
                'timestamp': datetime.utcnow().isoformat()
            },
            timeout=5
        )
        feature_store_ok = feature_store_response.status_code == 200
        
        # 3. Publish analytics event
        event = publish_analytics_event(
            event_type='fl.model.trained',
            entity_type='fl_model',
            entity_id=model_version,
            result={
                'model_version': model_version,
                'metrics': metrics,
                'metadata': model_metadata
            },
            confidence=metrics.get('accuracy', 0.0),
            citations=[{
                'document_id': document_id,
                'source': 'federated_learning_system',
                'url': f'/fl/models/{model_version}'
            }],
            lineage={
                'run_id': run_id,
                'training_method': 'FedAvg',
                'computed_at': datetime.utcnow().isoformat()
            }
        )
        
        return {
            'document_id': document_id,
            'published_to_rag': True,
            'published_to_feature_store': feature_store_ok,
            'event_id': event.get('event_id'),
            'searchable': True,
            'message': f'FL model {model_version} published to RAG and Feature Store'
        }
        
    except requests.exceptions.RequestException as e:
        return {
            'document_id': None,
            'published_to_rag': False,
            'published_to_feature_store': False,
            'error': str(e)
        }


@tool
def publish_fl_prediction_to_rag(
    prediction_id: str,
    model_version: str,
    input_features: Dict[str, Any],
    predicted_class: int,
    confidence: float,
    explanation: Optional[str] = None
) -> Dict[str, Any]:
    """
    Publish FL prediction to RAG with explanation.
    
    Creates a searchable document linking:
    - Input features
    - Prediction output
    - Model used
    - Confidence score
    - Natural language explanation
    
    Args:
        prediction_id: Unique prediction identifier
        model_version: FL model version used
        input_features: Input feature values
        predicted_class: Predicted class (0 or 1)
        confidence: Prediction confidence (0-1)
        explanation: Optional natural language explanation
    
    Returns:
        {
            'document_id': str,
            'published': bool,
            'linked_to_model': bool
        }
    
    Example:
        result = publish_fl_prediction_to_rag(
            prediction_id='pred_abc123',
            model_version='fl_run_001_r5',
            input_features={
                'sentiment': 'positive',
                'call_duration_minutes': 8.5,
                'response_time': 45
            },
            predicted_class=1,
            confidence=0.87,
            explanation='High CSAT predicted due to positive sentiment and fast response'
        )
    """
    
    # Build explanation if not provided
    if not explanation:
        explanation = _generate_prediction_explanation(
            input_features, predicted_class, confidence
        )
    
    # Build RAG document
    document = {
        'title': f'FL Prediction: {prediction_id}',
        'content': f"""
Federated Learning Prediction

Model: {model_version}
Prediction ID: {prediction_id}
Predicted Class: {predicted_class} ({'High CSAT' if predicted_class == 1 else 'Low CSAT'})
Confidence: {confidence:.2%}

Input Features:
{json.dumps(input_features, indent=2)}

Explanation:
{explanation}

This prediction was made using a federated learning model trained across multiple 
call center data silos without sharing raw customer data.
        """.strip(),
        'metadata': {
            'document_type': 'fl_prediction',
            'prediction_id': prediction_id,
            'model_version': model_version,
            'predicted_class': predicted_class,
            'confidence': confidence,
            'created_at': datetime.utcnow().isoformat(),
            'tags': ['federated_learning', 'prediction', 'csat']
        },
        'source': 'federated_learning_inference',
        'url': f'/fl/predictions/{prediction_id}'
    }
    
    try:
        # 1. Publish to RAG
        rag_response = requests.post(
            f"{RAG_SERVICE_URL}/ingest",
            json={'documents': [document]},
            timeout=10
        )
        rag_response.raise_for_status()
        rag_result = rag_response.json()
        document_id = rag_result.get('document_ids', [None])[0]
        
        # 2. Link prediction to model document
        # Query RAG for model document
        model_query_response = requests.post(
            f"{RAG_SERVICE_URL}/query",
            json={
                'query': f'Federated Learning Model {model_version}',
                'context': {'model_version': model_version}
            },
            timeout=10
        )
        
        model_citations = []
        if model_query_response.status_code == 200:
            model_result = model_query_response.json()
            model_citations = model_result.get('citations', [])
        
        # 3. Create bidirectional link
        if model_citations:
            link_numerical_to_evidence(
                numerical_result_id=prediction_id,
                evidence_citations=model_citations
            )
        
        return {
            'document_id': document_id,
            'published': True,
            'linked_to_model': len(model_citations) > 0,
            'message': f'Prediction {prediction_id} published to RAG'
        }
        
    except requests.exceptions.RequestException as e:
        return {
            'document_id': None,
            'published': False,
            'error': str(e)
        }


@tool
def publish_fl_training_summary_to_rag(
    run_id: str,
    run_name: str,
    num_rounds: int,
    num_clients: int,
    final_metrics: Dict[str, float],
    convergence_analysis: str,
    privacy_guarantees: str
) -> Dict[str, Any]:
    """
    Publish FL training run summary to RAG.
    
    Creates a comprehensive document about the training run:
    - Configuration and setup
    - Client participation
    - Convergence behavior
    - Final performance
    - Privacy guarantees
    
    Args:
        run_id: FL run identifier
        run_name: Human-readable run name
        num_rounds: Number of federated rounds
        num_clients: Number of participating clients
        final_metrics: Final model metrics
        convergence_analysis: Analysis of convergence behavior
        privacy_guarantees: Description of privacy measures
    
    Returns:
        {
            'document_id': str,
            'published': bool,
            'searchable': bool
        }
    
    Example:
        result = publish_fl_training_summary_to_rag(
            run_id='fl_run_001',
            run_name='Call Center CSAT Q4',
            num_rounds=5,
            num_clients=4,
            final_metrics={'accuracy': 0.87, 'f1': 0.85},
            convergence_analysis='Model converged after round 4...',
            privacy_guarantees='No raw data shared, local training only'
        )
    """
    
    document = {
        'title': f'Federated Learning Training Run: {run_name}',
        'content': f"""
Federated Learning Training Summary

Run ID: {run_id}
Run Name: {run_name}
Configuration:
- Number of Rounds: {num_rounds}
- Number of Clients: {num_clients}
- Strategy: FedAvg (Federated Averaging)

Final Performance Metrics:
{json.dumps(final_metrics, indent=2)}

Convergence Analysis:
{convergence_analysis}

Privacy Guarantees:
{privacy_guarantees}

This federated learning run trained a model across {num_clients} independent data silos 
over {num_rounds} rounds of federated averaging, achieving {final_metrics.get('accuracy', 0):.1%} 
accuracy without sharing raw data between organizations.
        """.strip(),
        'metadata': {
            'document_type': 'fl_training_run',
            'run_id': run_id,
            'run_name': run_name,
            'num_rounds': num_rounds,
            'num_clients': num_clients,
            'final_metrics': final_metrics,
            'created_at': datetime.utcnow().isoformat(),
            'tags': ['federated_learning', 'training', 'summary']
        },
        'source': 'federated_learning_system',
        'url': f'/fl/runs/{run_id}'
    }
    
    try:
        rag_response = requests.post(
            f"{RAG_SERVICE_URL}/ingest",
            json={'documents': [document]},
            timeout=10
        )
        rag_response.raise_for_status()
        rag_result = rag_response.json()
        document_id = rag_result.get('document_ids', [None])[0]
        
        return {
            'document_id': document_id,
            'published': True,
            'searchable': True,
            'message': f'Training run {run_name} published to RAG'
        }
        
    except requests.exceptions.RequestException as e:
        return {
            'document_id': None,
            'published': False,
            'error': str(e)
        }


# ===================================================================
# QUERY FL RESULTS FROM RAG
# ===================================================================

@tool
def query_fl_models_from_rag(
    query: str,
    filters: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Query FL models and results from RAG.
    
    Use this to:
    - Find FL models by performance criteria
    - Compare different FL runs
    - Retrieve model explanations
    - Get training summaries
    
    Args:
        query: Natural language query
        filters: Optional filters (dataset, min_accuracy, etc.)
    
    Returns:
        {
            'answer': str,
            'models': List[Dict],
            'citations': List[Dict],
            'confidence': float
        }
    
    Example:
        # Find best performing FL model
        result = query_fl_models_from_rag(
            query='What is the best performing federated learning model for CSAT prediction?',
            filters={'dataset': 'call_center_csat', 'min_accuracy': 0.85}
        )
        
        print(result['answer'])
        for model in result['models']:
            print(f"Model: {model['model_version']}, Accuracy: {model['accuracy']}")
    """
    
    try:
        # Add FL-specific context to query
        context = filters or {}
        context['document_type'] = 'fl_model'
        
        response = requests.post(
            f"{RAG_SERVICE_URL}/query",
            json={
                'query': query,
                'context': context
            },
            timeout=10
        )
        response.raise_for_status()
        result = response.json()
        
        # Extract FL models from citations
        models = []
        for citation in result.get('citations', []):
            if citation.get('metadata', {}).get('document_type') == 'fl_model':
                models.append({
                    'model_version': citation['metadata'].get('model_version'),
                    'metrics': citation['metadata'].get('metrics', {}),
                    'url': citation.get('url')
                })
        
        return {
            'answer': result.get('answer'),
            'models': models,
            'citations': result.get('citations', []),
            'confidence': result.get('confidence', 0)
        }
        
    except requests.exceptions.RequestException as e:
        return {
            'answer': None,
            'models': [],
            'citations': [],
            'error': str(e)
        }


# ===================================================================
# HELPER FUNCTIONS
# ===================================================================

def _build_fl_model_document(
    model_version: str,
    run_id: str,
    metrics: Dict[str, float],
    metadata: Dict[str, Any],
    summary: str
) -> str:
    """Build comprehensive FL model document."""
    
    return f"""
Federated Learning Model: {model_version}

Training Run: {run_id}
Dataset: {metadata.get('dataset', 'Unknown')}
Strategy: {metadata.get('strategy', 'FedAvg')}

Configuration:
- Number of Clients: {metadata.get('num_clients', 'N/A')}
- Number of Rounds: {metadata.get('num_rounds', 'N/A')}
- Minimum Clients per Round: {metadata.get('min_clients', 'N/A')}

Performance Metrics:
- Accuracy: {metrics.get('accuracy', 0):.4f}
- F1 Score: {metrics.get('f1', 0):.4f}
- AUC: {metrics.get('auc', 0):.4f}
- Precision: {metrics.get('precision', 0):.4f}
- Recall: {metrics.get('recall', 0):.4f}

Model Details:
- Number of Parameters: {metadata.get('num_parameters', 'N/A')}
- Model Type: {metadata.get('model_type', 'Logistic Regression')}

Training Summary:
{summary}

Privacy Guarantees:
This model was trained using federated learning, which means:
- No raw data was shared between organizations
- Each client trained locally on their own data
- Only model parameters were aggregated
- Individual data points remain private

Use Cases:
- Customer satisfaction prediction
- Call center analytics
- Privacy-preserving machine learning
- Distributed model training
    """.strip()


def _generate_prediction_explanation(
    input_features: Dict[str, Any],
    predicted_class: int,
    confidence: float
) -> str:
    """Generate natural language explanation for prediction."""
    
    sentiment = input_features.get('sentiment', 'unknown')
    call_duration = input_features.get('call_duration_minutes', 0)
    response_time = input_features.get('response_time', 0)
    
    class_label = 'High CSAT (≥4)' if predicted_class == 1 else 'Low CSAT (<4)'
    
    explanation = f"Predicted {class_label} with {confidence:.1%} confidence. "
    
    # Add feature-based reasoning
    if predicted_class == 1:
        if sentiment == 'positive':
            explanation += "Positive sentiment is a strong indicator of satisfaction. "
        if call_duration < 10:
            explanation += "Short call duration suggests efficient resolution. "
        if response_time < 60:
            explanation += "Fast response time contributes to positive experience."
    else:
        if sentiment == 'negative':
            explanation += "Negative sentiment indicates dissatisfaction. "
        if call_duration > 15:
            explanation += "Long call duration may indicate complex issues. "
        if response_time > 180:
            explanation += "Slow response time negatively impacts satisfaction."
    
    return explanation


# ===================================================================
# EXPORT FL RAG TOOLS
# ===================================================================

FL_RAG_TOOLS = [
    publish_fl_model_to_rag,
    publish_fl_prediction_to_rag,
    publish_fl_training_summary_to_rag,
    query_fl_models_from_rag
]

