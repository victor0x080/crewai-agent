"""
CrewAI Agent Factory - Auto-generates agents on-the-fly using LLM
Generates role, goal, backstory, and tool configuration from trigger events
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass

from crewai import Agent
import openai

from factory.tool_registry import get_tool_registry, ToolRegistry
from tools.redis_streams_tools import RedisStreamsClient
from tools.redis_streams_tools import publish_cloudevent, fetch_cloudevent, fetch_schema, validate_against_schema, redis_ack
from tools.ontology_tools import resolve_concept, expand_concepts, map_enum, get_category_constraints


@dataclass
class AgentSpec:
    """Specification for a generated agent."""
    role: str
    goal: str
    backstory: str
    capabilities: List[str]
    required_tools: List[str]
    data_sources: List[str]
    output_format: str
    allow_delegation: bool
    model: str
    temperature: float
    metadata: Dict[str, Any]


class CrewAIAgentFactory:
    """
    Auto-generates CrewAI agents on-the-fly using LLM prompts.
    Populates role, goal, backstory, and tool configuration based on trigger events.
    """
    
    def __init__(
        self,
        llm_client: Optional[openai.OpenAI] = None,
        tool_registry: Optional[ToolRegistry] = None,
        supabase_client: Optional[Any] = None
    ):
        """
        Initialize the agent factory.
        
        Args:
            llm_client: OpenAI client (defaults to env-based client)
            tool_registry: Tool registry instance
            supabase_client: Supabase client for agent registration
        """
        # Only initialize OpenAI if not explicitly set to None
        if llm_client is False:
            self.llm_client = None
        else:
            try:
                self.llm_client = llm_client or openai.OpenAI()
            except Exception:
                self.llm_client = None
        
        self.tool_registry = tool_registry or get_tool_registry()
        self.supabase = supabase_client
        
        try:
            self.redis = RedisStreamsClient().get_client()
        except Exception:
            self.redis = None
        
        # Cache for generated agents (avoid regenerating similar agents)
        self._agent_cache: Dict[str, Agent] = {}
        
        # Telemetry
        self._generation_count = 0
        self._cache_hits = 0
        self._generation_times: List[float] = []
    
    async def generate_agent_from_trigger(
        self,
        trigger_event: Dict[str, Any],
        context: Dict[str, Any],
        available_datasets: List[str],
        use_cache: bool = True
    ) -> Agent:
        """
        Generate a CrewAI agent tailored to a specific trigger event.
        
        Args:
            trigger_event: The triggering event (CloudEvent format)
            context: Business context (current state, constraints, goals)
            available_datasets: List of accessible datasets/streams
            use_cache: Whether to use cached agents for similar triggers
        
        Returns:
            Fully configured CrewAI Agent
        """
        start_time = time.time()
        
        # Generate cache key
        cache_key = self._generate_cache_key(trigger_event, context)
        
        # Check cache
        if use_cache and cache_key in self._agent_cache:
            self._cache_hits += 1
            print(f"✅ Using cached agent for trigger: {trigger_event.get('type', 'unknown')}")
            return self._agent_cache[cache_key]
        
        print(f"🤖 Generating new agent for trigger: {trigger_event.get('type', 'unknown')}")
        
        # Step 1: Generate agent specification using LLM
        agent_spec = await self._generate_agent_spec(
            trigger_event, context, available_datasets
        )
        
        # Step 2: Validate and map capabilities to tools
        tools = self._select_tools(agent_spec)
        
        # Step 3: Create ontology profile (for semantic routing)
        ontology_profile = self._create_ontology_profile(agent_spec)
        
        # Step 4: Instantiate CrewAI agent
        agent = Agent(
            role=agent_spec.role,
            goal=agent_spec.goal,
            backstory=agent_spec.backstory,
            tools=tools,
            verbose=True,
            allow_delegation=agent_spec.allow_delegation,
            llm_config={
                'provider': 'openai',
                'model': agent_spec.model,
                'temperature': agent_spec.temperature
            }
        )
        
        # Step 5: Register agent (if Supabase available)
        if self.supabase:
            await self._register_agent(agent, agent_spec, ontology_profile, trigger_event)
        
        # Cache the agent
        if use_cache:
            self._agent_cache[cache_key] = agent
        
        # Update telemetry
        generation_time = time.time() - start_time
        self._generation_count += 1
        self._generation_times.append(generation_time)
        
        print(f"✅ Generated agent '{agent_spec.role}' in {generation_time:.2f}s")
        
        return agent
    
    async def generate_agent_from_conversation(
        self, 
        conversation_context: dict,
        task_description: str
    ) -> Agent:
        """
        Generate agent from conversation context (Phase 3.A implementation).
        Ensures compliance with Redis Streams + CloudEvents + Ontology pattern.
        
        Args:
            conversation_context: Full conversation context
            task_description: Specific task description
        
        Returns:
            Fully configured CrewAI Agent with 100% compliance
        """
        # Build trigger event from conversation
        trigger_event = {
            'id': f"conv_{int(time.time())}",
            'type': 'conversation.task_requested',
            'severity': 'medium',
            'context': {
                'conversation': conversation_context,
                'task': task_description
            }
        }
        
        # Use main generation method (ensures all compliance requirements)
        return await self.generate_agent_from_trigger(
            trigger_event=trigger_event,
            context=conversation_context,
            available_datasets=conversation_context.get('available_datasets', []),
            use_cache=True
        )
    
    async def _generate_agent_spec(
        self,
        trigger_event: Dict[str, Any],
        context: Dict[str, Any],
        available_datasets: List[str]
    ) -> AgentSpec:
        """
        Use LLM to generate agent specification.
        This is the core intelligence of the factory.
        """
        
        # Build comprehensive prompt
        prompt = self._build_agent_generation_prompt(
            trigger_event, context, available_datasets
        )
        
        # Call OpenAI
        try:
            response = self.llm_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=1500
            )
            
            spec_json = response.choices[0].message.content
            
            # Parse JSON response
            spec_dict = json.loads(spec_json)
            
            # Validate required fields
            required_fields = ['role', 'goal', 'backstory', 'capabilities']
            for field in required_fields:
                if field not in spec_dict:
                    raise ValueError(f"Missing required field in LLM response: {field}")
            
            # Create AgentSpec
            return AgentSpec(
                role=spec_dict['role'],
                goal=spec_dict['goal'],
                backstory=spec_dict['backstory'],
                capabilities=spec_dict.get('capabilities', []),
                required_tools=spec_dict.get('required_tools', []),
                data_sources=spec_dict.get('data_sources', []),
                output_format=spec_dict.get('output_format', 'CloudEvent with analysis results'),
                allow_delegation=spec_dict.get('allow_delegation', False),
                model=spec_dict.get('model', 'gpt-4o-mini'),
                temperature=spec_dict.get('temperature', 0.7),
                metadata={
                    'trigger_type': trigger_event.get('type'),
                    'trigger_severity': trigger_event.get('severity'),
                    'generated_at': datetime.utcnow().isoformat()
                }
            )
        
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse LLM response as JSON: {e}\nResponse: {spec_json}")
        except Exception as e:
            raise ValueError(f"Failed to generate agent spec: {e}")
    
    def _build_agent_generation_prompt(
        self,
        trigger_event: Dict[str, Any],
        context: Dict[str, Any],
        available_datasets: List[str]
    ) -> str:
        """
        Build comprehensive prompt for agent generation.
        This is where the magic happens - the prompt engineering.
        """
        
        # Get vocabulary from tool registry
        capability_vocab = self.tool_registry.get_capability_vocabulary()
        tool_vocab = self.tool_registry.get_tool_vocabulary()
        
        prompt = f"""
You are an expert at designing intelligent agents for business operations.

TRIGGER EVENT:
{json.dumps(trigger_event, indent=2)}

BUSINESS CONTEXT:
{json.dumps(context, indent=2)}

AVAILABLE DATASETS:
{', '.join(available_datasets)}

Generate a CrewAI agent specification to handle this trigger. The agent should be:
1. Highly specialized for this specific trigger
2. Have a clear, measurable goal
3. Possess relevant expertise (backstory)
4. Use appropriate tools and data sources

Return ONLY valid JSON in this exact format (no markdown, no backticks):

{{
  "role": "Concise role title (e.g., 'Demand Forecast Analyst', 'Inventory Risk Specialist')",
  "goal": "Specific, measurable goal derived from trigger data. Include metrics, timeframes, and success criteria. Example: 'Identify root causes of 15% demand drop for SKU WH-PRO-2024 and recommend 3 corrective actions within 24 hours'",
  "backstory": "2-3 sentence expertise description that establishes credibility and domain knowledge. Example: 'Expert demand forecaster with 10+ years analyzing consumer behavior patterns. Specializes in diagnosing demand anomalies using causal inference and prescribing data-driven marketing interventions. Deep expertise in retail analytics and promotional effectiveness.'",
  "capabilities": ["list", "of", "required", "capabilities"],
  "required_tools": ["tool_name_1", "tool_name_2"],
  "data_sources": ["dataset_1", "dataset_2"],
  "output_format": "Description of expected output (e.g., 'CloudEvent with root cause analysis and ranked recommendations')",
  "allow_delegation": false,
  "model": "gpt-4o-mini",
  "temperature": 0.7
}}

CAPABILITIES VOCABULARY (choose 2-5 most relevant):
{', '.join(capability_vocab[:30])}

TOOL VOCABULARY (choose 3-8 most relevant):
{', '.join(tool_vocab)}

GUIDELINES:
1. Role: Short, professional title (3-5 words max)
2. Goal: Must be SMART (Specific, Measurable, Achievable, Relevant, Time-bound)
3. Backstory: Establish expertise without being verbose. Focus on relevant domain knowledge.
4. Capabilities: Select 2-5 capabilities that directly address the trigger
5. Tools: Select 3-8 DOMAIN-SPECIFIC tools (Redis Streams, CloudEvents, and Ontology tools are added automatically)
6. Data Sources: List specific datasets from available_datasets that are relevant
7. Output: Agent MUST emit a CloudEvent to Redis Stream (per agent.md pattern)
8. Input: Agent MUST consume from Redis Streams via XREADGROUP (per agent.md pattern)

EXAMPLES OF GOOD GOALS:
- "Reduce stockout risk for SKU-1234 from 90% to <20% by identifying optimal replenishment quantity within 2 hours"
- "Diagnose 15% demand drop for Electronics category, identify top 3 root causes, and recommend corrective budget reallocation within 4 hours"
- "Optimize campaign budget allocation across 5 RMNs to maximize ROAS while maintaining $50K total spend constraint"

EXAMPLES OF GOOD BACKSTORIES:
- "Expert supply chain analyst with deep expertise in inventory optimization, demand forecasting, and service level management. Specializes in stockout prevention using predictive analytics and constraint-based optimization."
- "Senior marketing analyst with 12+ years optimizing multi-channel campaigns. Expert at causal attribution, incrementality testing, and budget allocation across retail media networks."

CRITICAL COMPLIANCE REQUIREMENTS (per agent.md):
1. Agent MUST consume events from Redis Streams using XREADGROUP (consumer groups)
2. Agent MUST publish results as CloudEvents 1.0 to target stream using redis_publish
3. Agent MUST acknowledge processed messages with redis_ack
4. Agent MUST validate input/output against JSON Schema (two-stage: JSON Schema + SHACL)
5. Agent MUST use ontology tools (resolve_concept, expand_concepts, map_enum) for semantic interoperability
6. Agent output format MUST be: CloudEvent with @context, validated against target schema

Return ONLY the JSON object, nothing else.
"""
        
        return prompt
    
    def _select_tools(self, agent_spec: AgentSpec) -> List[Any]:
        """
        Map capabilities and data sources to actual tool functions.
        
        COMPLIANCE: All agents MUST have Redis Streams + CloudEvents + Ontology tools
        per agent.md and crewai-agent-design-pattern.md
        """
        tools = []
        seen = set()
        
        # REQUIRED: Core Redis Streams tools (all agents need these)
        # Note: consume_stream is used internally by runners, not as a CrewAI tool
        # Agents use publish_cloudevent to publish results, not the raw function
        core_redis_tools = [
            publish_cloudevent,  # Publish CloudEvents to streams (decorated with @tool)
            redis_ack            # Acknowledge messages (decorated with @tool)
            # consume_stream is NOT a tool - it's used by runners to consume tasks
        ]
        for tool in core_redis_tools:
            tool_id = id(tool)
            if tool_id not in seen:
                tools.append(tool)
                seen.add(tool_id)
        
        # REQUIRED: Core CloudEvents tools (all agents need these)
        core_cloudevent_tools = [
            publish_cloudevent,       # Publish CloudEvent to stream
            fetch_cloudevent,         # Fetch CloudEvent from RedisJSON
            validate_against_schema,  # JSON Schema validation
            fetch_schema              # Fetch schema from registry
        ]
        for tool in core_cloudevent_tools:
            tool_id = id(tool)
            if tool_id not in seen:
                tools.append(tool)
                seen.add(tool_id)
        
        # REQUIRED: Core Ontology tools (per ontology.md)
        core_ontology_tools = [
            resolve_concept,           # Resolve label → URI
            expand_concepts,           # Expand via SKOS relations
            map_enum,                  # Map enum values
            get_category_constraints   # Get SHACL constraints
        ]
        for tool in core_ontology_tools:
            tool_id = id(tool)
            if tool_id not in seen:
                tools.append(tool)
                seen.add(tool_id)
        
        # Get tools from capabilities
        capability_tools = self.tool_registry.get_tools_for_capabilities(
            agent_spec.capabilities
        )
        for tool in capability_tools:
            tool_id = id(tool)
            if tool_id not in seen:
                tools.append(tool)
                seen.add(tool_id)
        
        # Get tools from data sources
        data_source_tools = self.tool_registry.get_tools_for_data_sources(
            agent_spec.data_sources
        )
        for tool in data_source_tools:
            tool_id = id(tool)
            if tool_id not in seen:
                tools.append(tool)
                seen.add(tool_id)
        
        # Add explicitly requested tools
        for tool_name in agent_spec.required_tools:
            tool_func = self.tool_registry.get_tool_by_name(tool_name)
            if tool_func:
                tool_id = id(tool_func)
                if tool_id not in seen:
                    tools.append(tool_func)
                    seen.add(tool_id)
        
        return tools
    
    def _create_ontology_profile(self, agent_spec: AgentSpec) -> Dict[str, Any]:
        """
        Create ontology profile for semantic routing.
        Maps capabilities to ontology concepts.
        """
        
        # Map capabilities to ontology concepts
        concept_mapping = {
            'optimization': 'ex:Optimization',
            'forecasting': 'ex:Forecast',
            'causal_analysis': 'ex:CausalInference',
            'scenario_simulation': 'ex:Simulation',
            'inventory': 'ex:Inventory',
            'risk': 'ex:Risk',
            'budget_optimization': 'ex:Budget',
            'bid_optimization': 'ex:Bid',
            'anomaly_detection': 'ex:Detection',
            'routing': 'ex:Routing',
            'translation': 'ex:Translation',
            'validation': 'ex:Validation',
            'compliance': 'ex:Compliance',
            'campaign': 'ex:Campaign',
            'attribution': 'ex:Attribution',
            'elasticity': 'ex:Elasticity',
            'retail_media': 'rmn:RetailMediaNetwork',
            'closed_loop_attribution': 'rmn:ClosedLoopAttribution',
            'incrementality': 'rmn:Incrementality',
        }
        
        concepts = [
            concept_mapping[cap] 
            for cap in agent_spec.capabilities 
            if cap in concept_mapping
        ]
        
        # Determine entity interests
        entity_interests = {}
        if any(cap in ['campaign', 'budget_optimization', 'bid_optimization'] for cap in agent_spec.capabilities):
            entity_interests = {
                'type': 'ex:MarketingEntity',
                'where': {
                    'entity_type_in': ['campaign', 'budget', 'creative', 'bid']
                }
            }
        elif any(cap in ['inventory', 'forecasting', 'elasticity'] for cap in agent_spec.capabilities):
            entity_interests = {
                'type': 'ex:BusinessEntity',
                'where': {
                    'entity_type_in': ['product', 'sku', 'customer', 'order']
                }
            }
        
        # Determine ontology tools
        ontology_tools = ['kg.resolve']  # All agents need resolve
        if 'routing' in agent_spec.capabilities:
            ontology_tools.extend(['kg.expand', 'kg.map_enum'])
        if 'translation' in agent_spec.capabilities:
            ontology_tools.extend(['kg.expand', 'kg.map_enum', 'kg.same_as'])
        if any(cap in ['compliance', 'validation'] for cap in agent_spec.capabilities):
            ontology_tools.extend(['kg.get_constraints', 'kg.get_shape'])
        
        return {
            'interests_concepts_must': concepts,
            'interests_concepts_any': [],
            'interests_entities': entity_interests,
            'input_schema_uri': 'https://schemas.mesh/EventPayload.json',
            'output_schema_uri': 'https://schemas.mesh/EventPayload.json',
            'tools': list(set(ontology_tools))
        }
    
    async def _register_agent(
        self,
        agent: Agent,
        agent_spec: AgentSpec,
        ontology_profile: Dict[str, Any],
        trigger_event: Dict[str, Any]
    ):
        """
        Register agent with database and ontology service.
        """
        if not self.supabase:
            return
        
        try:
            # Generate unique agent ID
            agent_id = f"dynamic_{agent_spec.role.lower().replace(' ', '_')}_{int(time.time())}"
            
            # Insert into agents table
            agent_data = {
                'id': agent_id,
                'name': agent_spec.role,
                'role': agent_spec.role,
                'goal': agent_spec.goal,
                'backstory': agent_spec.backstory,
                'tools': [t.__name__ for t in agent.tools],
                'agent_type': 'dynamic',
                'enabled': True,
                'team': 'dynamic',
                'class': 'specialist',
                'level': 5,
                'avatar': '🤖',
                'skills': {
                    'action': 75,
                    'analysis': 80,
                    'learning': 70,
                    'collaboration': 75
                },
                'equipment': agent_spec.required_tools,
                'experience_points': 500,
                'allow_delegation': agent_spec.allow_delegation,
                'verbose': True,
                'llm_config': {
                    'provider': 'openai',
                    'model': agent_spec.model,
                    'temperature': agent_spec.temperature
                },
                'memory_enabled': True,
                'created_at': datetime.utcnow().isoformat(),
                'metadata': {
                    **agent_spec.metadata,
                    'trigger_id': trigger_event.get('id'),
                    'capabilities': agent_spec.capabilities,
                    'data_sources': agent_spec.data_sources
                }
            }
            
            self.supabase.table('agents').insert(agent_data).execute()
            
            # Insert ontology profile
            ontology_data = {
                'agent_id': agent_id,
                **ontology_profile
            }
            
            self.supabase.table('agent_ontology_profiles').insert(ontology_data).execute()
            
            print(f"  ✓ Registered agent '{agent_spec.role}' in database")
        
        except Exception as e:
            print(f"  ⚠️  Failed to register agent: {e}")
    
    def _generate_cache_key(
        self,
        trigger_event: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """
        Generate cache key for agent reuse.
        Similar triggers should produce the same key.
        """
        # Use trigger type + severity as primary key
        trigger_type = trigger_event.get('type', 'unknown')
        severity = trigger_event.get('severity', 'medium')
        
        # Add context hash (simplified)
        context_keys = sorted(context.keys())
        context_sig = '_'.join(context_keys[:3])  # Use first 3 context keys
        
        return f"{trigger_type}_{severity}_{context_sig}"
    
    def get_telemetry(self) -> Dict[str, Any]:
        """Get factory telemetry metrics."""
        avg_generation_time = (
            sum(self._generation_times) / len(self._generation_times)
            if self._generation_times else 0
        )
        
        return {
            'total_generations': self._generation_count,
            'cache_hits': self._cache_hits,
            'cache_hit_rate': (
                self._cache_hits / (self._generation_count + self._cache_hits)
                if (self._generation_count + self._cache_hits) > 0 else 0
            ),
            'avg_generation_time_seconds': avg_generation_time,
            'cached_agents': len(self._agent_cache)
        }
    
    def clear_cache(self):
        """Clear the agent cache."""
        self._agent_cache.clear()
        print("✅ Agent cache cleared")


# Singleton instance
_factory_instance = None

def get_agent_factory() -> CrewAIAgentFactory:
    """Get singleton instance of CrewAIAgentFactory."""
    global _factory_instance
    if _factory_instance is None:
        _factory_instance = CrewAIAgentFactory()
    return _factory_instance


if __name__ == '__main__':
    # Test the factory
    import asyncio
    
    async def test_factory():
        factory = get_agent_factory()
        
        print("=" * 80)
        print("CREWAI AGENT FACTORY TEST")
        print("=" * 80)
        
        # Test trigger event
        trigger_event = {
            'id': 'test-trigger-001',
            'type': 'demand.forecast.updated',
            'severity': 'high',
            'data': {
                'sku': 'WH-PRO-2024',
                'demand_change': -0.15,
                'confidence': 0.85,
                'current_inventory': 15000,
                'forecast_units': 12750
            }
        }
        
        context = {
            'business_unit': 'Electronics',
            'current_quarter': 'Q4',
            'budget_remaining': 250000,
            'constraints': ['maintain_service_level_95', 'max_markdown_20_percent']
        }
        
        available_datasets = [
            'demand_forecast',
            'inventory',
            'pricing',
            'campaign_performance'
        ]
        
        print("\nGenerating agent for demand forecast trigger...")
        agent = await factory.generate_agent_from_trigger(
            trigger_event,
            context,
            available_datasets
        )
        
        print(f"\n✅ Generated Agent:")
        print(f"  Role: {agent.role}")
        print(f"  Goal: {agent.goal}")
        print(f"  Backstory: {agent.backstory}")
        print(f"  Tools: {[t.__name__ for t in agent.tools]}")
        
        print("\nTelemetry:")
        telemetry = factory.get_telemetry()
        for key, value in telemetry.items():
            print(f"  {key}: {value}")
        
        print("\n" + "=" * 80)
    
    asyncio.run(test_factory())
