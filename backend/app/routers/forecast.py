from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.deps import CurrentUser

router = APIRouter(tags=["forecast"])


@router.get("/forecast")
def forecast(_: CurrentUser):
    # No model exists yet; the old demo's fake prediction/anomaly endpoints were removed.
    return JSONResponse(status_code=501, content={"status": "未啟用", "detail": "預測模型尚未建置"})
