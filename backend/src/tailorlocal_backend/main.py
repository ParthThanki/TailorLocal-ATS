"""FastAPI application for the local TailorLocal backend."""

from __future__ import annotations

import os
from collections.abc import Callable

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .model_client import LocalModelClient, LocalModelError
from .schemas import (
    GenerationRequest,
    GenerationResponse,
    HealthResponse,
    ModelListRequest,
    ModelListResponse,
    ScoreRequest,
    ScoreResponse,
)
from .scoring import calculate_ats_score
from .service import ModelResponseError, generate_resume

ClientFactory = Callable[[], LocalModelClient]


def _allowed_origins() -> list[str]:
    configured = os.getenv("TAILORLOCAL_ALLOWED_ORIGINS", "")
    defaults = ["http://localhost:3000", "http://127.0.0.1:3000"]
    return [value.strip().rstrip("/") for value in configured.split(",") if value.strip()] or defaults


def create_app(client_factory: ClientFactory = LocalModelClient) -> FastAPI:
    app = FastAPI(
        title="TailorLocal Python Backend",
        version=__version__,
        docs_url="/docs",
        redoc_url=None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_allowed_origins(),
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(version=__version__)

    @app.post("/api/models", response_model=ModelListResponse)
    async def models(request: ModelListRequest) -> ModelListResponse:
        try:
            found = await client_factory().list_models(request.provider, request.endpoint)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except LocalModelError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        if not found:
            raise HTTPException(status_code=404, detail="Connected, but no local models were found.")
        return ModelListResponse(models=found)

    @app.post("/api/score", response_model=ScoreResponse)
    async def score(request: ScoreRequest) -> ScoreResponse:
        return ScoreResponse(analysis=calculate_ats_score(request.resume, request.job_description))

    @app.post("/api/generate", response_model=GenerationResponse)
    async def generate(request: GenerationRequest) -> GenerationResponse:
        try:
            return await generate_resume(request, client_factory())
        except ModelResponseError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except LocalModelError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    return app


app = create_app()
