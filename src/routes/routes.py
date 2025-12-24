from fastapi import APIRouter
from src.models import CodeDiff, AgentFinding
from src.agents import CodeQualityAgent, SecurityAgent
from typing import List

router = APIRouter(prefix="/code")
from src.clients.ollama_client import get_llm_client


llm_client = get_llm_client(model_name="llama3.2:latest")
quality_agent = CodeQualityAgent(llm_client=llm_client)
security_agent = SecurityAgent(llm_client=llm_client)


@router.post("/review", response_model=List[AgentFinding])
def review_code(code_diff: CodeDiff):
    quality_agent_response = quality_agent.analyze(code_diff=code_diff, temperature=0.3)
    security_agent_response = security_agent.analyze(
        code_diff=code_diff, temperature=0.1
    )
    return security_agent_response
