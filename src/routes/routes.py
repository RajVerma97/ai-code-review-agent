from fastapi import APIRouter
from src.models import CodeDiff, AgentFinding, AgentResponse, AgentConfig
from src.agents import BaseAgent
from typing import List
from src.services import OrchestratorService
from src.clients.ollama_client import get_llm_client
from datetime import timedelta
import time

router = APIRouter(prefix="/code")

llm_client = get_llm_client(model_name="llama3.2:latest")


@router.post("/review", response_model=List[AgentResponse])
def review_code(code_diff: CodeDiff):
    print("starting review timer")
    start_time = time.perf_counter()
    agent_configs: List[AgentConfig] = [
        AgentConfig(
            agent_name="security_agent", agent_class="security", temperature=0.1
        ),
        AgentConfig(agent_name="quality_agent", agent_class="quality", temperature=0.3),
    ]

    # call the orchestrator service
    orchestrator_service = OrchestratorService(
        llm_client=llm_client, agent_configs=agent_configs, max_workers=5
    )
    responses = orchestrator_service.review_parallel(code_diff=code_diff)
    end_time = time.perf_counter()
    duration = timedelta(seconds=end_time - start_time)
    print("duration is ", duration)

    return responses
