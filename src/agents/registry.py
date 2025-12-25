from src.agents import CodeQualityAgent, SecurityAgent, BaseAgent
from src.models import AgentConfig
from src.clients import OllamaClient

# Registry of all available agents
AGENT_REGISTRY = {
    "quality": CodeQualityAgent,
    "security": SecurityAgent,
    # Add more agents here as you build them
}


def create_agent(llm_client: OllamaClient, agent_config: AgentConfig) -> BaseAgent:
    agent_class = AGENT_REGISTRY.get(agent_config.agent_class)
    if agent_class is None:
        raise ValueError(f"Unknown Agent Class: {agent_config.agent_class}")
    return agent_class(llm_client, agent_config)
