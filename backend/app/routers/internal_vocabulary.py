from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.core.config import settings
from app.schemas.vocabulary import VocabularyLookupRequest, VocabularyLookupResponse
from app.services.vocabulary_lookup_service import lookup_vocabulary

router = APIRouter(prefix="/internal/v1/vocabulary", tags=["Internal Vocabulary"])


def require_internal_token(
    x_internal_token: str | None = Header(default=None, alias="X-Internal-Token"),
) -> None:
    expected = settings.AI_WORKER_INTERNAL_TOKEN
    if not x_internal_token or not secrets.compare_digest(x_internal_token, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid internal service token",
        )


@router.post("/lookup", response_model=VocabularyLookupResponse)
async def vocabulary_lookup(
    request: VocabularyLookupRequest,
    _authorized: None = Depends(require_internal_token),
):
    return await lookup_vocabulary(request)
