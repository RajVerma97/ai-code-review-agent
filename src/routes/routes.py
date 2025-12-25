from fastapi import APIRouter
from src.models import CodeDiff, AgentFinding, AgentResponse, AgentConfig
from src.agents import BaseAgent
from typing import List
from src.services import OrchestratorService

router = APIRouter(prefix="/code")
from src.clients.ollama_client import get_llm_client


llm_client = get_llm_client(model_name="llama3.2:latest")


@router.post("/review", response_model=List[AgentResponse])
def review_code(code_diff: CodeDiff):
    agent_configs: List[AgentConfig] = [
        AgentConfig(
            agent_name="security_agent", agent_class="security", temperature=0.1
        ),
        AgentConfig(agent_name="quality_agent", agent_class="quality", temperature=0.3),
    ]

    # call the orchestrator service
    orchestrator_service = OrchestratorService(
        llm_client=llm_client, agent_configs=agent_configs
    )
    responses = orchestrator_service.review(code_diff=code_diff)
    return responses
