from fastapi import APIRouter


router = APIRouter()


@router.get("/health", summary="健康检查")
def check_health() -> dict[str, str]:
    """用于确认后端服务是否正常运行。"""
    return {"status": "ok"}

