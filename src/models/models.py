from pydantic import BaseModel
from typing import List
from datetime import timedelta


class AgentConfig(BaseModel):
    agent_name: str
    agent_class: str
    temperature: float


class AgentFinding(BaseModel):
    severity: str
    line_number: int
    issue_type: str
    description: str
    suggestion: str
    confidence: float


class AgentResponse(BaseModel):
    agent_name: str
    findings: List[AgentFinding]
    execution_time: float # seconds


class ReviewResult(BaseModel):
    """Complete review result from all agents"""

    agent_responses: List[AgentResponse]
    total_findings: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    summary: str


class CodeDiff(BaseModel):
    file_path: str
    old_code: str
    new_code: str
    language: str
