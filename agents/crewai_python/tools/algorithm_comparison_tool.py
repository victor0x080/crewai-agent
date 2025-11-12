#!/usr/bin/env python3
"""
Algorithm Comparison Tool
Compares results from multiple algorithms and generates consensus recommendations
"""

import json
from typing import Dict, List, Any
from crewai.tools import tool


@tool("Compare Algorithm Results")
def compare_algorithm_results(algorithm_results: str) -> str:
    """
    Compare results from multiple algorithms and generate consensus recommendations.
    
    Args:
        algorithm_results: JSON string with array of algorithm results, each containing:
            - algorithm: algorithm name
            - outputs: dict with algorithm outputs
            - status: "success" or "error"
    
    Returns:
        JSON with:
            - consensus: weighted consensus values
            - agreement_metrics: correlation, rank correlation, CV
            - divergence_flags: channels/values with high disagreement
            - recommendations: synthesized recommendations
    """
    try:
        results_list = json.loads(algorithm_results) if isinstance(algorithm_results, str) else algorithm_results
        
        if not isinstance(results_list, list):
            return json.dumps({
                "status": "error",
                "error": "algorithm_results must be a list"
            })
        
        # Filter successful results
        successful_results = [r for r in results_list if r.get('status') == 'success']
        
        if len(successful_results) < 2:
            return json.dumps({
                "status": "error",
                "error": "Need at least 2 successful algorithm results to compare"
            })
        
        # Extract common outputs (e.g., ROAS, CPA, allocation)
        consensus_outputs = {}
        agreement_metrics = {}
        divergence_flags = []
        
        # Algorithm weights (from document)
        algorithm_weights = {
            'GeoLift': 0.35,
            'CausalImpact': 0.30,
            'RobynMMM': 0.25,
            'Robyn': 0.25,
            'MultiTouchAttribution': 0.10,
            'MTA': 0.10
        }
        
        # Find common output keys across all algorithms
        all_output_keys = set()
        for result in successful_results:
            outputs = result.get('outputs', {})
            if isinstance(outputs, dict):
                all_output_keys.update(outputs.keys())
        
        # Calculate consensus for each output
        for output_key in all_output_keys:
            values = []
            weights = []
            
            for result in successful_results:
                algo_name = result.get('algorithm', 'Unknown')
                outputs = result.get('outputs', {})
                
                if output_key in outputs:
                    value = outputs[output_key]
                    # Try to extract numeric value
                    if isinstance(value, (int, float)):
                        values.append(value)
                        weight = algorithm_weights.get(algo_name, 0.20)  # Default weight
                        weights.append(weight)
                    elif isinstance(value, dict):
                        # Handle nested structures (e.g., roas_by_channel)
                        if 'roas_by_channel' in output_key or 'cpa_by_channel' in output_key:
                            # Extract channel-level values
                            for channel, channel_value in value.items():
                                if isinstance(channel_value, (int, float)):
                                    channel_key = f"{output_key}.{channel}"
                                    if channel_key not in consensus_outputs:
                                        consensus_outputs[channel_key] = {'values': [], 'weights': []}
                                    consensus_outputs[channel_key]['values'].append(channel_value)
                                    consensus_outputs[channel_key]['weights'].append(
                                        algorithm_weights.get(algo_name, 0.20)
                                    )
            
            if values:
                # Calculate weighted average
                total_weight = sum(weights)
                if total_weight > 0:
                    weighted_avg = sum(v * w for v, w in zip(values, weights)) / total_weight
                    consensus_outputs[output_key] = {
                        'consensus_value': weighted_avg,
                        'values': values,
                        'weights': weights,
                        'min': min(values),
                        'max': max(values),
                        'range': max(values) - min(values) if values else 0
                    }
                    
                    # Calculate coefficient of variation (CV) for agreement
                    if len(values) > 1 and weighted_avg != 0:
                        mean_val = sum(values) / len(values)
                        variance = sum((v - mean_val) ** 2 for v in values) / len(values)
                        std_dev = variance ** 0.5
                        cv = std_dev / abs(mean_val) if mean_val != 0 else float('inf')
                        agreement_metrics[output_key] = {
                            'coefficient_of_variation': cv,
                            'agreement_level': 'high' if cv < 0.2 else 'medium' if cv < 0.4 else 'low'
                        }
                        
                        # Flag high divergence
                        if cv > 0.4:
                            divergence_flags.append({
                                'output': output_key,
                                'cv': cv,
                                'values': values,
                                'message': f'High disagreement in {output_key} (CV={cv:.2f})'
                            })
        
        # Generate recommendations
        recommendations = []
        
        # Check for high-confidence consensus
        high_confidence_outputs = [
            k for k, v in agreement_metrics.items() 
            if v.get('agreement_level') == 'high'
        ]
        
        if high_confidence_outputs:
            recommendations.append({
                'type': 'high_confidence',
                'outputs': high_confidence_outputs,
                'message': f'High agreement found in {len(high_confidence_outputs)} outputs - use consensus values'
            })
        
        # Flag divergences for review
        if divergence_flags:
            recommendations.append({
                'type': 'review_required',
                'divergences': divergence_flags,
                'message': f'{len(divergence_flags)} outputs show high disagreement - manual review recommended'
            })
        
        # Extract optimal allocation if available
        allocation_keys = [k for k in consensus_outputs.keys() if 'allocation' in k.lower() or 'optimal' in k.lower()]
        if allocation_keys:
            recommendations.append({
                'type': 'allocation_recommendation',
                'message': 'Optimal allocation calculated from consensus',
                'allocation': {k: consensus_outputs[k].get('consensus_value') for k in allocation_keys}
            })
        
        return json.dumps({
            "status": "success",
            "consensus": {
                k: v.get('consensus_value') if isinstance(v, dict) else v
                for k, v in consensus_outputs.items()
                if not isinstance(v, dict) or 'consensus_value' in v
            },
            "agreement_metrics": agreement_metrics,
            "divergence_flags": divergence_flags,
            "recommendations": recommendations,
            "algorithms_compared": [r.get('algorithm') for r in successful_results],
            "algorithm_count": len(successful_results)
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__
        })


@tool("Synthesize Multi-Algorithm Insights")
def synthesize_multi_algorithm_insights(comparison_result: str, query: str = "") -> str:
    """
    Synthesize insights from algorithm comparison into actionable recommendations.
    
    Args:
        comparison_result: JSON string from compare_algorithm_results
        query: Original query for context
    
    Returns:
        JSON with synthesized insights and recommendations
    """
    try:
        comparison = json.loads(comparison_result) if isinstance(comparison_result, str) else comparison_result
        
        if comparison.get('status') != 'success':
            return json.dumps({
                "status": "error",
                "error": "Invalid comparison result"
            })
        
        consensus = comparison.get('consensus', {})
        recommendations = comparison.get('recommendations', [])
        divergence_flags = comparison.get('divergence_flags', [])
        
        # Build synthesis
        insights = {
            "summary": f"Analysis from {comparison.get('algorithm_count', 0)} algorithms",
            "key_findings": [],
            "actionable_recommendations": [],
            "confidence_level": "high" if len(divergence_flags) == 0 else "medium" if len(divergence_flags) <= 2 else "low"
        }
        
        # Extract key findings from consensus
        for key, value in consensus.items():
            if isinstance(value, (int, float)):
                insights["key_findings"].append({
                    "metric": key,
                    "value": value,
                    "interpretation": f"{key} consensus value: {value:.2f}"
                })
        
        # Add recommendations
        for rec in recommendations:
            if rec.get('type') == 'allocation_recommendation':
                insights["actionable_recommendations"].append({
                    "type": "budget_allocation",
                    "recommendation": rec.get('message', ''),
                    "details": rec.get('allocation', {})
                })
            elif rec.get('type') == 'review_required':
                insights["actionable_recommendations"].append({
                    "type": "review",
                    "recommendation": rec.get('message', ''),
                    "items": rec.get('divergences', [])
                })
        
        return json.dumps({
            "status": "success",
            "insights": insights,
            "query": query,
            "algorithms_used": comparison.get('algorithms_compared', [])
        }, indent=2)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "error": str(e)
        })


if __name__ == '__main__':
    # Test the comparison tool
    test_results = [
        {
            "algorithm": "RobynMMM",
            "status": "success",
            "outputs": {
                "roas_by_channel": {"digital": 3.2, "tv": 2.8},
                "optimal_allocation": {"digital": 0.45, "tv": 0.35, "radio": 0.20}
            }
        },
        {
            "algorithm": "GeoLift",
            "status": "success",
            "outputs": {
                "roas_by_channel": {"digital": 3.5, "tv": 3.0},
                "optimal_allocation": {"digital": 0.50, "tv": 0.30, "radio": 0.20}
            }
        },
        {
            "algorithm": "CausalImpact",
            "status": "success",
            "outputs": {
                "roas_by_channel": {"digital": 3.3, "tv": 2.9},
                "optimal_allocation": {"digital": 0.48, "tv": 0.32, "radio": 0.20}
            }
        }
    ]
    
    result = compare_algorithm_results(json.dumps(test_results))
    print("Comparison Result:")
    print(result)
    
    synthesis = synthesize_multi_algorithm_insights(result, "Marketing mix optimization")
    print("\nSynthesis:")
    print(synthesis)

