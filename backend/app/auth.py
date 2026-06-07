from fastapi import APIRouter, HTTPException, Query
from app.bungie.api import BungieAPI

router = APIRouter(prefix="/auth", tags=["auth"])
bungie_api = BungieAPI()


@router.get("/login")
def login():
    """Returns the Bungie OAuth authorization URL."""
    return {"auth_url": bungie_api.get_auth_url()}


@router.post("/token")
async def exchange_token(code: str = Query(...)):
    """Exchanges an auth code for tokens and resolves Destiny memberships in one shot."""
    tokens = await bungie_api.get_token(code)
    access_token = tokens.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="No access token in Bungie response")

    memberships = await bungie_api.get_memberships(access_token)

    destiny_memberships = memberships.get("destinyMemberships", [])
    primary_id = memberships.get("primaryMembershipId")
    bungie_net_user = memberships.get("bungieNetUser", {})

    # Pick primary membership, fall back to first
    primary = next(
        (m for m in destiny_memberships if m.get("membershipId") == primary_id),
        destiny_memberships[0] if destiny_memberships else None,
    )

    return {
        "access_token": access_token,
        "refresh_token": tokens.get("refresh_token"),
        "expires_in": tokens.get("expires_in"),
        "bungie_membership_id": tokens.get("membership_id"),
        "display_name": bungie_net_user.get("uniqueName") or bungie_net_user.get("displayName"),
        "destiny_memberships": destiny_memberships,
        "primary_membership": primary,
    }
