"""
Proactive Agents for Agentic Workspace
Dual-agent system: Sentry (low-cost monitor) + Chief (high-cost reasoner)
MULTI-PROVIDER SUPPORT: Works with OpenAI, Anthropic, Google, Groq, xAI, OpenRouter, Perplexity
"""

from agno.agent import Agent
from agno.storage.agent.sqlite import SqliteAgentStorage
from agno.models.openai import OpenAIChat
from agno.models.anthropic import Claude
from agno.models.google import Gemini
from agno.models.groq import Groq
from agno.models.openrouter import OpenRouter
from agno.models.perplexity import Perplexity
from agno.models.xai import xAI
from agno.tools.shell import ShellTools
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
import os

# ============================================================================
# STRUCTURED OUTPUT MODELS
# ============================================================================

class MonitorResult(BaseModel):
    """Structured output for Sentry Agent monitoring checks."""
    status: str = Field(
        description="Current status: 'healthy', 'degraded', or 'critical'"
    )
    requires_escalation: bool = Field(
        description="True if Chief Agent intervention is needed"
    )
    summary: str = Field(
        description="Brief status summary (1-2 sentences)"
    )
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Raw check data and metrics"
    )


class ActionDecision(BaseModel):
    """Structured output for Chief Agent decision-making."""
    action_type: str = Field(
        description="Action to take: 'notify_user', 'retry', 'pause_task', 'escalate', 'adjust_schedule'"
    )
    message: str = Field(
        description="User-facing notification message (clear and actionable)"
    )
    suggested_next_check: int = Field(
        description="Seconds until next check (adjust based on severity)",
        default=3600
    )
    severity: str = Field(
        description="Issue severity: 'low', 'medium', 'high', 'critical'",
        default="medium"
    )


# ============================================================================
# SQLITE STORAGE CONFIGURATION
# ============================================================================

# Use the same database as the main app for consistency
app_data = os.path.join(os.path.expanduser("~"), ".myapp")
os.makedirs(app_data, exist_ok=True)

storage = SqliteAgentStorage(
    table_name="agno_proactive_sessions",
    db_file=os.path.join(app_data, "memory.db")  # Reuse existing memory.db
)


# ============================================================================
# MODEL CONFIGURATION HELPERS
# ============================================================================

# Recommended models for each provider (cost-optimized)
SENTRY_MODELS = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-haiku-4-5-20251001",  # Cheapest Anthropic model
    "gemini": "gemini-2.0-flash-001",
    "groq": "llama-3.3-70b-versatile",
    "grok": "grok-beta",
    "openrouter": "openai/gpt-4o-mini",  # Route to OpenAI mini
    "perplexity": "sonar"  # Cheapest Perplexity model
}

CHIEF_MODELS = {
    "openai": "gpt-4o",
    "anthropic": "claude-sonnet-4-5-20250929",  # Best reasoning
    "gemini": "gemini-2.0-flash-thinking-exp-01-21",
    "groq": "llama-3.3-70b-versatile",  # Same as sentry for Groq
    "grok": "grok-3",
    "openrouter": "anthropic/claude-3.5-sonnet",  # Route to Claude
    "perplexity": "sonar-pro"
}


def get_model_for_agent(provider: str, agent_type: str, api_key: str, custom_model: Optional[str] = None):
    """
    Get the appropriate model instance for Sentry or Chief agent.
    
    Args:
        provider: LLM provider name
        agent_type: 'sentry' or 'chief'
        api_key: API key for the provider
        custom_model: Optional custom model ID override
    
    Returns:
        Agno model instance
    """
    # Determine which model to use
    if custom_model:
        model_id = custom_model
    else:
        model_map = SENTRY_MODELS if agent_type == 'sentry' else CHIEF_MODELS
        model_id = model_map.get(provider)
    
    # Create model instance based on provider
    if provider == "openai":
        return OpenAIChat(id=model_id, api_key=api_key)
    elif provider == "anthropic":
        return Claude(id=model_id, api_key=api_key)
    elif provider == "gemini":
        return Gemini(id=model_id, api_key=api_key)
    elif provider == "groq":
        return Groq(id=model_id, api_key=api_key)
    elif provider == "grok":
        return xAI(id=model_id, api_key=api_key)
    elif provider == "openrouter":
        return OpenRouter(id=model_id, api_key=api_key)
    elif provider == "perplexity":
        return Perplexity(id=model_id, api_key=api_key)
    else:
        # Fallback to OpenAI
        return OpenAIChat(id="gpt-4o-mini", api_key=api_key)


def create_sentry_agent(
    provider: str = "openai",
    api_key: Optional[str] = None,
    custom_model: Optional[str] = None
) -> Agent:
    """
    Create Sentry Agent with specified provider.
    
    Args:
        provider: LLM provider (openai, anthropic, gemini, etc.)
        api_key: API key (defaults to env var)
        custom_model: Optional custom model ID
    
    Returns:
        Configured Sentry Agent
    """
    # Get API key from environment if not provided
    if not api_key:
        env_var = f"{provider.upper()}_API_KEY"
        if provider == "grok":
            env_var = "XAI_API_KEY"
        api_key = os.environ.get(env_var)
    
    if not api_key:
        raise ValueError(f"No API key found for provider '{provider}'. Set {env_var} environment variable.")
    
    # Get model
    model = get_model_for_agent(provider, 'sentry', api_key, custom_model)
    
    return Agent(
        agent_id=f"sentry-monitor-{provider}",
        name="Sentry Monitor",
        model=model,
        storage=storage,
        tools=[ShellTools()],
        response_model=MonitorResult,
        instructions=[
            "You are a low-level monitoring agent responsible for routine system checks.",
            "Execute checks efficiently and report status in structured format.",
            "Set requires_escalation=True ONLY when you detect genuine anomalies or issues.",
            "DO NOT escalate routine status updates or normal operations.",
            "Focus on factual observations - no speculation or assumptions.",
            "If you cannot determine status definitively, set status='degraded' and escalate.",
            "",
            "Status Guidelines:",
            "- 'healthy': Everything operating normally within expected parameters",
            "- 'degraded': Minor issues detected but system still functional",
            "- 'critical': Severe issues requiring immediate attention",
            "",
            "Escalation Rules:",
            "- Escalate if status is 'critical'",
            "- Escalate if status is 'degraded' for 3+ consecutive checks",
            "- Escalate if metrics exceed defined thresholds",
            "- DO NOT escalate for normal operations",
        ],
        add_history_to_messages=True,
        num_history_responses=3,
        markdown=False,
        show_tool_calls=False
    )


def create_chief_agent(
    provider: str = "openai",
    api_key: Optional[str] = None,
    custom_model: Optional[str] = None
) -> Agent:
    """
    Create Chief Agent with specified provider.
    
    Args:
        provider: LLM provider (openai, anthropic, gemini, etc.)
        api_key: API key (defaults to env var)
        custom_model: Optional custom model ID
    
    Returns:
        Configured Chief Agent
    """
    # Get API key from environment if not provided
    if not api_key:
        env_var = f"{provider.upper()}_API_KEY"
        if provider == "grok":
            env_var = "XAI_API_KEY"
        api_key = os.environ.get(env_var)
    
    if not api_key:
        raise ValueError(f"No API key found for provider '{provider}'. Set {env_var} environment variable.")
    
    # Get model
    model = get_model_for_agent(provider, 'chief', api_key, custom_model)
    
    return Agent(
        agent_id=f"chief-reasoning-{provider}",
        name="Chief Reasoning Agent",
        model=model,
        storage=storage,
        response_model=ActionDecision,
        instructions=[
            "You are the primary decision-maker for the proactive monitoring system.",
            "Analyze escalations from the Sentry Agent and make informed decisions.",
            "Communicate with users in clear, actionable, and empathetic terms.",
            "Adjust monitoring schedules based on issue severity and patterns.",
            "",
            "Decision Framework:",
            "1. Assess the severity of the reported issue",
            "2. Determine if user notification is necessary",
            "3. Decide on appropriate action (notify, retry, pause, adjust schedule)",
            "4. Craft clear, actionable message for the user",
            "",
            "Action Type Guidelines:",
            "- 'notify_user': Issue requires user awareness (always include clear message)",
            "- 'retry': Temporary issue, retry check with current interval",
            "- 'pause_task': Persistent issue, pause monitoring until user intervenes",
            "- 'adjust_schedule': Change check frequency based on patterns",
            "- 'escalate': Critical issue requiring immediate user action",
            "",
            "Scheduling Adjustments:",
            "- Increase frequency (shorter interval) for unstable/critical situations",
            "- Decrease frequency (longer interval) for stable/healthy situations",
            "- Default interval: 3600 seconds (1 hour)",
            "- Critical issues: 300-600 seconds (5-10 minutes)",
            "- Stable monitoring: 7200-14400 seconds (2-4 hours)",
            "",
            "Message Guidelines:",
            "- Be concise but informative",
            "- Include specific details (what, when, why it matters)",
            "- Provide actionable next steps when appropriate",
            "- Use friendly, professional tone",
            "- Avoid technical jargon unless necessary",
        ],
        add_history_to_messages=True,
        num_history_responses=10,
        markdown=True,
        show_tool_calls=False
    )


# ============================================================================
# DEFAULT AGENTS (OpenAI for backwards compatibility)
# ============================================================================

# Default agents use OpenAI (can be overridden by creating custom agents)
# We wrap this in a try/except because we might not have API keys at import time
try:
    if os.environ.get("OPENAI_API_KEY"):
        sentry_agent = create_sentry_agent(provider="openai")
        chief_agent = create_chief_agent(provider="openai")
except Exception:
    pass

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_monitoring_prompt(
    task_type: str,
    config: Dict[str, Any],
    context: str = ""
) -> str:
    """
    Create appropriate monitoring prompt for Sentry Agent.
    
    Args:
        task_type: Type of monitoring task
        config: Task configuration dictionary
        context: Additional context (e.g., previous check results)
    
    Returns:
        Formatted prompt string
    """
    prompts = {
        "monitor_url": f"""
Execute health check on endpoint:
URL: {config.get('url', 'N/A')}
Expected Status: {config.get('expected_status', 200)}
Timeout: {config.get('timeout', 30)}s
{context}
""",
        "monitor_file": f"""
Check file status:
Path: {config.get('path', 'N/A')}
Watch for: {config.get('watch_for', 'changes')}
{context}
""",
        "monitor_process": f"""
Monitor process:
Process Name: {config.get('process_name', 'N/A')}
Expected Status: {config.get('expected_status', 'running')}
{context}
""",
        "daily_briefing": f"""
Generate briefing:
Topics: {', '.join(config.get('topics', []))}
Focus Areas: {', '.join(config.get('focus_areas', []))}
{context}
""",
    }
    
    return prompts.get(task_type, f"Execute monitoring task: {task_type}\nConfig: {config}\n{context}")


def test_sentry_agent():
    """Test function to verify Sentry Agent is working."""
    if 'sentry_agent' not in globals():
        print("Sentry agent not initialized (check API key)")
        return None
        
    result = sentry_agent.run(
        message="Perform a test health check. Report status as 'healthy'.",
        session_id="test-session"
    )
    print("Sentry Test Result:")
    print(result.content)
    return result


def test_chief_agent():
    """Test function to verify Chief Agent is working."""
    if 'chief_agent' not in globals():
        print("Chief agent not initialized (check API key)")
        return None

    result = chief_agent.run(
        message="""Sentry Agent has detected an issue:
**Status:** degraded
**Summary:** API response time increased to 2.5 seconds (threshold: 1 second)
**Data:** {"avg_response_time": 2.5, "threshold": 1.0, "endpoint": "https://api.example.com/health"}
Analyze and decide on action.""",
        session_id="test-session"
    )
    print("Chief Test Result:")
    print(result.content)
    return result


if __name__ == "__main__":
    # Run tests when module is executed directly
    print("Testing Proactive Agents...\n")
    print("="*50)
    test_sentry_agent()
    print("\n" + "="*50)
    test_chief_agent()
