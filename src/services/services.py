from src.clients import OllamaClient
from src.models import AgentConfig, CodeDiff, AgentResponse
from typing import List
from src.agents.registry import create_agent
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from datetime import datetime


class OrchestratorService:

    def __init__(self, llm_client, agent_configs: List[AgentConfig], max_workers: int):
        self.agent_configs = agent_configs
        self.llm_client = llm_client
        self.max_workers = max_workers or len(agent_configs)

    def review_sequential(self, code_diff: CodeDiff) -> List[AgentResponse]:
        responses: List[AgentResponse] = []
        for agent_config in self.agent_configs:
            agent_response =self._run_single_agent(agent_config=agent_config,code_diff=code_diff)
            responses.append(agent_response)
        return responses

    def review_parallel(self, code_diff: CodeDiff) -> List[AgentResponse]:
        """Run agents in parallel using ThreadPoolExecutor"""
        responses: List[AgentResponse] = []

        # Create a thread pool
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all agent tasks
            future_to_agent = {
                executor.submit(
                    self._run_single_agent, agent_config, code_diff
                ): agent_config
                for agent_config in self.agent_configs
            }

            # Collect results as they complete
            for future in as_completed(future_to_agent):
                agent_config = future_to_agent[future]
                try:
                    response = future.result()
                    responses.append(response)
                    print(f"✓ {agent_config.agent_name} completed")
                except Exception as e:
                    print(f"✗ {agent_config.agent_name} failed: {str(e)}")
                    # Optionally add error handling or fallback

        return responses

    def _run_single_agent(
        self, agent_config: AgentConfig, code_diff: CodeDiff
    ) -> AgentResponse:
        """Helper method to run a single agent"""
        start = time.time()
        print(f"{agent_config.agent_name} STARTED")

        agent = create_agent(llm_client=self.llm_client, agent_config=agent_config)
        response = agent.analyze(code_diff=code_diff)  # ← Move timing AFTER this

        end = time.time()
        duration = end - start
        print(f"{agent_config.agent_name} FINISHED ({duration:.2f}s)")
        return response
