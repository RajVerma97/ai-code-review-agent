from pydantic import BaseModel


class CodeDiff(BaseModel):
    file_path: str
    old_code: str
    new_code: str
    language: str
