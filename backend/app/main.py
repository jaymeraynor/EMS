from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import get_settings, validate_for_startup
from app.db import get_db
from app.routers import auth, billing, carbon, energy, forecast, ingest, meters, orgs, sites


def create_app() -> FastAPI:
    settings = get_settings()
    validate_for_startup(settings)           # raises RuntimeError on a weak JWT_SECRET
    prod = settings.ems_env == "production"
    app = FastAPI(title="EMS API", version="1.0.0",
                  docs_url=None if prod else "/docs", redoc_url=None, openapi_url=None if prod else "/openapi.json")
    if settings.cors_origins:
        app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins),
                           allow_methods=["GET", "POST", "PATCH"],
                           allow_headers=["Authorization", "Content-Type", "X-API-Key"])

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        # Drop echoed ``input``/``ctx``: values such as NaN/Infinity are not JSON-serialisable.
        errors = [{"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
        return JSONResponse(status_code=422, content={"detail": errors})

    api = APIRouter(prefix="/api/v1")

    @api.get("/health", tags=["health"])
    def health(db=Depends(get_db)):
        db.execute(text("SELECT 1"))
        return {"status": "ok"}

    for r in (auth, orgs, sites, meters, ingest, energy, billing, carbon, forecast):
        api.include_router(r.router)
    app.include_router(api)
    return app


app = create_app()
