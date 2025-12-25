from src.clients import OllamaClient
from src.models import AgentConfig, CodeDiff, AgentResponse
from typing import List
from src.agents.registry import create_agent


class OrchestratorService:
    def __init__(self, llm_client, agent_configs: List[AgentConfig]):
        self.agent_configs = agent_configs
        self.llm_client = llm_client

    def review(self, code_diff: CodeDiff) -> List[AgentResponse]:
        responses: List[AgentResponse] = []
        for agent_config in self.agent_configs:
            agent_class = create_agent(llm_client=self.llm_client, agent_config=agent_config)
            agent_response = agent_class.analyze(code_diff=code_diff)
            responses.append(agent_response)
        return responses
