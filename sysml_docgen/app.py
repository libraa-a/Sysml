"""Run the FastAPI SysML DocGen application."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from .api.routes import docgen_router, integration_router, mms_router, system_router
from .auth import identity_from_headers
from .config import FRONTEND_DIST_DIR, resolve_frontend_dir
from .ops import configure_logging, request_logging_middleware
from .repository import create_model_store
from .services.mms_service import effective_project_role, project_id_from_path
from .repository import StoreError, enforce_role


def create_app() -> FastAPI:
    configure_logging()
    frontend_dir, frontend_mode = resolve_frontend_dir()
    app = FastAPI(
        title="SysML DocGen",
        version="3.0",
        description="SysML document generation service with MMS, VE, MDK, and DocGen capabilities.",
    )
    app.state.store = create_model_store()
    app.state.frontend_dir = frontend_dir
    app.state.frontend_mode = frontend_mode
    app.middleware("http")(request_logging_middleware)

    @app.middleware("http")
    async def project_access_middleware(request: Request, call_next: Any) -> Response:
        project_id = project_id_from_path(request.url.path)
        if project_id:
            try:
                project = app.state.store.get_project(project_id)
                identity = identity_from_headers(request.headers)
                enforce_role(request.method, effective_project_role(project, identity))
            except StoreError as exc:
                return JSONResponse({"error": str(exc)}, status_code=exc.status_code)
        return await call_next(request)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(StoreError)
    async def store_error_handler(_: Request, exc: StoreError) -> JSONResponse:
        return JSONResponse({"error": str(exc)}, status_code=exc.status_code)

    @app.exception_handler(HTTPException)
    async def http_error_handler(_: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse({"error": exc.detail}, status_code=exc.status_code)

    app.include_router(system_router)
    app.include_router(mms_router)
    app.include_router(docgen_router)
    app.include_router(integration_router)

    if app.state.frontend_dir is not None:
        app.mount("/", StaticFiles(directory=app.state.frontend_dir, html=True), name="ve")
    else:
        @app.get("/", include_in_schema=False)
        async def frontend_not_built() -> JSONResponse:
            return JSONResponse(
                {
                    "error": "Frontend build artifacts are missing",
                    "expected": str(FRONTEND_DIST_DIR / "index.html"),
                    "hint": "Build the frontend with `npm install && npm run build` in the `frontend` directory.",
                },
                status_code=503,
            )

    return app


app = create_app()
