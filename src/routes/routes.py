from fastapi import APIRouter
from src.models import CodeDiff

router = APIRouter(prefix="/code")


@router.post(
    "/",
)
def run(code_diff: CodeDiff):
    return {"code_diff is ": code_diff}
