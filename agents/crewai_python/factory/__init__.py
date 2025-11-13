"""
CrewAI Agent Factory Package
Auto-generates agents on-the-fly using LLM prompts
"""

from .agent_factory import (
    CrewAIAgentFactory,
    AgentSpec,
    get_agent_factory
)

from .tool_registry import (
    ToolRegistry,
    get_tool_registry,
    get_tools_for_capabilities,
    get_tools_for_data_sources
)

__all__ = [
    'CrewAIAgentFactory',
    'AgentSpec',
    'get_agent_factory',
    'ToolRegistry',
    'get_tool_registry',
    'get_tools_for_capabilities',
    'get_tools_for_data_sources',
]
