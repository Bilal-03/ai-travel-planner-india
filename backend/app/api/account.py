"""Anonymous continuity, optional account, trip history, and preference memory APIs."""

from __future__ import annotations

import hashlib

from fastapi import APIRouter, Header, HTTPException, Response
from pydantic import BaseModel, Field

from app.models.account import (
    Account,
    AccountRegistrationRequest,
    AccountSession,
    PreferenceMemory,
    PreferenceMemoryUpdate,
    SavedTripSummary,
)
from app.services.account_service import (
    create_anonymous_session,
    delete_account,
    delete_preferences,
    get_account_for_token,
    get_preferences,
    register_account,
    update_preferences,
)
from app.services.trip_storage import (
    claim_multi_city_trip,
    claim_trip,
    delete_saved_trips,
    list_saved_trip_summaries,
)

router = APIRouter(prefix="/api/account", tags=["account"])
ACCOUNT_TOKEN_HEADER = "X-Yatra-Account-Token"
EDIT_TOKEN_HEADER = "X-Trip-Edit-Token"


class ClaimTripRequest(BaseModel):
    trip_id: str = Field(..., min_length=4, max_length=64)


def _token_from_headers(
    account_token: str | None,
    authorization: str | None,
) -> str | None:
    if account_token:
        return account_token.strip()
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


async def _require_account(
    account_token: str | None,
    authorization: str | None,
) -> Account:
    account = await get_account_for_token(_token_from_headers(account_token, authorization))
    if not account:
        raise HTTPException(status_code=401, detail="Create or continue an account session first.")
    return account


def _set_session_header(response: Response, session: AccountSession) -> None:
    response.headers[ACCOUNT_TOKEN_HEADER] = session.access_token


@router.post("/anonymous", response_model=AccountSession)
async def create_anonymous_account_session(response: Response):
    """Create a non-blocking anonymous identity for trip continuity."""
    session = await create_anonymous_session()
    _set_session_header(response, session)
    return session


@router.post("/register", response_model=AccountSession)
async def register_optional_account(
    request: AccountRegistrationRequest,
    response: Response,
    account_token: str | None = Header(None, alias=ACCOUNT_TOKEN_HEADER),
    authorization: str | None = Header(None, alias="Authorization"),
):
    """Upgrade the current anonymous identity without forcing authentication."""
    try:
        session = await register_account(request, _token_from_headers(account_token, authorization))
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    _set_session_header(response, session)
    return session


@router.get("/me", response_model=Account)
async def get_current_account(
    account_token: str | None = Header(None, alias=ACCOUNT_TOKEN_HEADER),
    authorization: str | None = Header(None, alias="Authorization"),
):
    return await _require_account(account_token, authorization)


@router.post("/claim-trip")
async def claim_anonymous_trip(
    request: ClaimTripRequest,
    account_token: str | None = Header(None, alias=ACCOUNT_TOKEN_HEADER),
    authorization: str | None = Header(None, alias="Authorization"),
    edit_token: str | None = Header(None, alias=EDIT_TOKEN_HEADER),
):
    account = await _require_account(account_token, authorization)
    if not edit_token:
        raise HTTPException(status_code=403, detail="The trip edit token is required to claim an anonymous trip.")
    token_hash = hashlib.sha256(edit_token.encode("utf-8")).hexdigest()
    claimed = await claim_trip(request.trip_id, token_hash, account.id)
    if not claimed:
        claimed = await claim_multi_city_trip(request.trip_id, token_hash, account.id)
    if not claimed:
        raise HTTPException(status_code=403, detail="Trip not found or the edit token is invalid.")
    return {"claimed": True, "trip_id": request.trip_id, "account_id": account.id}


@router.get("/trips", response_model=list[SavedTripSummary])
async def get_saved_trip_history(
    account_token: str | None = Header(None, alias=ACCOUNT_TOKEN_HEADER),
    authorization: str | None = Header(None, alias="Authorization"),
):
    account = await _require_account(account_token, authorization)
    return [SavedTripSummary(**summary) for summary in await list_saved_trip_summaries(account.id)]


@router.get("/preferences", response_model=PreferenceMemory)
async def get_preference_memory(
    account_token: str | None = Header(None, alias=ACCOUNT_TOKEN_HEADER),
    authorization: str | None = Header(None, alias="Authorization"),
):
    account = await _require_account(account_token, authorization)
    return await get_preferences(account.id)


@router.put("/preferences", response_model=PreferenceMemory)
async def save_preference_memory(
    update: PreferenceMemoryUpdate,
    account_token: str | None = Header(None, alias=ACCOUNT_TOKEN_HEADER),
    authorization: str | None = Header(None, alias="Authorization"),
):
    account = await _require_account(account_token, authorization)
    return await update_preferences(account.id, update)


@router.post("/preferences/disable", response_model=PreferenceMemory)
async def disable_preference_memory(
    account_token: str | None = Header(None, alias=ACCOUNT_TOKEN_HEADER),
    authorization: str | None = Header(None, alias="Authorization"),
):
    account = await _require_account(account_token, authorization)
    return await update_preferences(account.id, PreferenceMemoryUpdate(memory_enabled=False))


@router.delete("/preferences", response_model=PreferenceMemory)
async def delete_preference_memory(
    account_token: str | None = Header(None, alias=ACCOUNT_TOKEN_HEADER),
    authorization: str | None = Header(None, alias="Authorization"),
):
    account = await _require_account(account_token, authorization)
    return await delete_preferences(account.id)


@router.delete("/me")
async def delete_current_account(
    response: Response,
    account_token: str | None = Header(None, alias=ACCOUNT_TOKEN_HEADER),
    authorization: str | None = Header(None, alias="Authorization"),
):
    account = await _require_account(account_token, authorization)
    await delete_saved_trips(account.id)
    await delete_account(account.id)
    response.delete_cookie("yatraai-account")
    return {"deleted": True}

