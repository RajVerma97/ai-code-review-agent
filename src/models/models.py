from pydantic import BaseModel


class AgentFinding(BaseModel):
    severity: str
    line_number: int
    issue_type: str
    description: str
    suggestion: str
    confidence: float


class CodeDiff(BaseModel):
    file_path: str
    old_code: str
    new_code: str
    language: str
