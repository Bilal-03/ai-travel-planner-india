"""Share links, collaborator invitations, history, conflict checks, and trip copy."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from urllib.parse import quote

from fastapi import APIRouter, Header, HTTPException, Response
from pydantic import BaseModel

from app.config import settings
from app.models.collaboration import (
    CollaborationRole,
    CollaboratorInviteRequest,
    ShareLinkCreateRequest,
    TripCopyRequest,
    TripKind,
)
from app.services.account_service import get_account_for_token
from app.services.collaboration_service import (
    add_collaborator,
    create_share_link,
    list_activity,
    list_collaborators,
    list_share_links,
    list_versions,
    record_audit,
    resolve_share_token,
    revoke_share_link,
)
from app.services.trip_storage import (
    get_multi_city_trip,
    get_multi_city_trip_owner_token_hash,
    get_trip,
    get_trip_owner_token_hash,
    save_multi_city_trip,
    save_trip,
)

router = APIRouter(prefix="/api/trips", tags=["collaboration"])
EDIT_TOKEN_HEADER = "X-Trip-Edit-Token"
SHARE_TOKEN_HEADER = "X-Trip-Share-Token"
ACCOUNT_TOKEN_HEADER = "X-Yatra-Account-Token"


class ShareAccessResponse(BaseModel):
    trip_id: str
    kind: TripKind
    role: CollaborationRole
    version: int


def _hash_edit_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def _kind_for_trip(trip_id: str, requested: TripKind | None = None) -> TripKind:
    if requested:
        return requested
    if await get_trip(trip_id):
        return TripKind.SINGLE
    if await get_multi_city_trip(trip_id):
        return TripKind.MULTI_CITY
    raise HTTPException(status_code=404, detail="Trip not found")


async def _trip_exists(trip_id: str, kind: TripKind) -> bool:
    return bool(await (get_trip(trip_id) if kind == TripKind.SINGLE else get_multi_city_trip(trip_id)))


async def _owner_role(trip_id: str, kind: TripKind, edit_token: str | None) -> CollaborationRole | None:
    expected = await (get_trip_owner_token_hash(trip_id) if kind == TripKind.SINGLE else get_multi_city_trip_owner_token_hash(trip_id))
    if expected and edit_token and hmac.compare_digest(expected, _hash_edit_token(edit_token)):
        return CollaborationRole.OWNER
    return None


async def _require_owner(trip_id: str, kind: TripKind, edit_token: str | None) -> None:
    if await _owner_role(trip_id, kind, edit_token) != CollaborationRole.OWNER:
        raise HTTPException(status_code=403, detail="Only the trip owner can manage collaboration settings.")


async def _require_access(trip_id: str, kind: TripKind, edit_token: str | None, share_token: str | None) -> CollaborationRole:
    owner = await _owner_role(trip_id, kind, edit_token)
    if owner:
        return owner
    role = await resolve_share_token(share_token or "", trip_id, kind)
    if role:
        return role
    raise HTTPException(status_code=403, detail="This collaboration link is missing, expired, or revoked.")


@router.get("/{trip_id}/access", response_model=ShareAccessResponse)
async def get_share_access(
    trip_id: str,
    kind: TripKind | None = None,
    edit_token: str | None = Header(None, alias=EDIT_TOKEN_HEADER),
    share_token: str | None = Header(None, alias=SHARE_TOKEN_HEADER),
):
    resolved = await _kind_for_trip(trip_id, kind)
    role = await _require_access(trip_id, resolved, edit_token, share_token)
    from app.services.collaboration_service import current_version

    return ShareAccessResponse(trip_id=trip_id, kind=resolved, role=role, version=await current_version(trip_id, resolved))


@router.post("/{trip_id}/share-links")
async def create_trip_share_link(
    trip_id: str,
    request: ShareLinkCreateRequest,
    response: Response,
    kind: TripKind | None = None,
    edit_token: str | None = Header(None, alias=EDIT_TOKEN_HEADER),
    account_token: str | None = Header(None, alias=ACCOUNT_TOKEN_HEADER),
):
    resolved = await _kind_for_trip(trip_id, kind)
    await _require_owner(trip_id, resolved, edit_token)
    if not await _trip_exists(trip_id, resolved):
        raise HTTPException(status_code=404, detail="Trip not found")
    account = await get_account_for_token(account_token)
    base_url = f"{settings.frontend_url.rstrip('/')}/trip/{trip_id}"
    link, raw_token = await create_share_link(
        trip_id,
        resolved,
        request.role,
        share_url=base_url,
        created_by=account.id if account else None,
        invite_email=request.invite_email,
        expires_in_hours=request.expires_in_hours,
    )
    link.share_url = f"{base_url}?share={quote(raw_token)}"
    response.headers["Cache-Control"] = "no-store"
    return link


@router.get("/{trip_id}/share-links")
async def get_trip_share_links(
    trip_id: str,
    kind: TripKind | None = None,
    edit_token: str | None = Header(None, alias=EDIT_TOKEN_HEADER),
):
    resolved = await _kind_for_trip(trip_id, kind)
    await _require_owner(trip_id, resolved, edit_token)
    base_url = f"{settings.frontend_url.rstrip('/')}/trip/{trip_id}"
    return await list_share_links(trip_id, resolved, share_url_builder=lambda _: base_url)


@router.delete("/{trip_id}/share-links/{link_id}")
async def delete_trip_share_link(
    trip_id: str,
    link_id: str,
    kind: TripKind | None = None,
    edit_token: str | None = Header(None, alias=EDIT_TOKEN_HEADER),
):
    resolved = await _kind_for_trip(trip_id, kind)
    await _require_owner(trip_id, resolved, edit_token)
    revoked = await revoke_share_link(trip_id, resolved, link_id)
    if not revoked:
        raise HTTPException(status_code=404, detail="Share link not found")
    return {"revoked": True}


@router.post("/{trip_id}/collaborators")
async def invite_trip_collaborator(
    trip_id: str,
    request: CollaboratorInviteRequest,
    kind: TripKind | None = None,
    edit_token: str | None = Header(None, alias=EDIT_TOKEN_HEADER),
    account_token: str | None = Header(None, alias=ACCOUNT_TOKEN_HEADER),
):
    resolved = await _kind_for_trip(trip_id, kind)
    await _require_owner(trip_id, resolved, edit_token)
    account = await get_account_for_token(account_token)
    return await add_collaborator(trip_id, resolved, request.email, request.role, account.id if account else None)


@router.get("/{trip_id}/collaborators")
async def get_trip_collaborators(
    trip_id: str,
    kind: TripKind | None = None,
    edit_token: str | None = Header(None, alias=EDIT_TOKEN_HEADER),
):
    resolved = await _kind_for_trip(trip_id, kind)
    await _require_owner(trip_id, resolved, edit_token)
    return await list_collaborators(trip_id, resolved)


@router.get("/{trip_id}/history")
async def get_trip_history(
    trip_id: str,
    kind: TripKind | None = None,
    edit_token: str | None = Header(None, alias=EDIT_TOKEN_HEADER),
    share_token: str | None = Header(None, alias=SHARE_TOKEN_HEADER),
):
    resolved = await _kind_for_trip(trip_id, kind)
    await _require_access(trip_id, resolved, edit_token, share_token)
    return await list_versions(trip_id, resolved)


@router.get("/{trip_id}/activity")
async def get_trip_activity(
    trip_id: str,
    kind: TripKind | None = None,
    edit_token: str | None = Header(None, alias=EDIT_TOKEN_HEADER),
    share_token: str | None = Header(None, alias=SHARE_TOKEN_HEADER),
):
    resolved = await _kind_for_trip(trip_id, kind)
    await _require_access(trip_id, resolved, edit_token, share_token)
    return await list_activity(trip_id, resolved)


@router.post("/{trip_id}/copy")
async def copy_trip(
    trip_id: str,
    request: TripCopyRequest,
    response: Response,
    kind: TripKind | None = None,
    edit_token: str | None = Header(None, alias=EDIT_TOKEN_HEADER),
    share_token: str | None = Header(None, alias=SHARE_TOKEN_HEADER),
    account_token: str | None = Header(None, alias=ACCOUNT_TOKEN_HEADER),
):
    resolved = await _kind_for_trip(trip_id, request.kind or kind)
    await _require_access(trip_id, resolved, edit_token, share_token)
    account = await get_account_for_token(account_token)
    owner_token = secrets.token_urlsafe(32)
    owner_hash = _hash_edit_token(owner_token)
    if resolved == TripKind.SINGLE:
        source = await get_trip(trip_id)
        if not source:
            raise HTTPException(status_code=404, detail="Trip not found")
        new_id = await save_trip(source.model_copy(deep=True), owner_hash, account.id if account else None)
        copied = await get_trip(new_id)
    else:
        source = await get_multi_city_trip(trip_id)
        if not source:
            raise HTTPException(status_code=404, detail="Multi-city trip not found")
        new_id = await save_multi_city_trip(source.model_copy(deep=True), owner_hash, account.id if account else None)
        copied = await get_multi_city_trip(new_id)
    if not copied:
        raise HTTPException(status_code=500, detail="Trip copy could not be saved")
    response.headers[EDIT_TOKEN_HEADER] = owner_token
    await record_audit("trip_copied", trip_id, account.id if account else None, {"kind": resolved.value})
    return {"trip_id": new_id, "kind": resolved, "trip": copied.model_dump(mode="json")}
