import os
import base64
import httpx
from fastapi import HTTPException
from urllib.parse import urlencode

BUNGIE_ROOT = "https://www.bungie.net"

class BungieAPI:
    def __init__(self):
        self.api_key = os.getenv("BUNGIE_API_KEY")
        self.client_id = os.getenv("BUNGIE_CLIENT_ID")
        self.client_secret = os.getenv("BUNGIE_CLIENT_SECRET")
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
        self.redirect_uri = f"{frontend_url}/auth/callback"

    def get_auth_url(self) -> str:
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
        }
        return f"{BUNGIE_ROOT}/en/OAuth/Authorize?{urlencode(params)}"

    async def get_token(self, code: str) -> dict:
        b64_auth = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        headers = {
            "Authorization": f"Basic {b64_auth}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
        }
        async with httpx.AsyncClient() as client:
            res = await client.post(f"{BUNGIE_ROOT}/Platform/App/OAuth/Token/", headers=headers, data=data)
            if res.status_code != 200:
                raise HTTPException(status_code=400, detail=f"Token exchange failed: {res.text}")
            return res.json()

    async def get_memberships(self, access_token: str) -> dict:
        headers = {
            "X-API-Key": self.api_key,
            "Authorization": f"Bearer {access_token}",
        }
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{BUNGIE_ROOT}/Platform/User/GetMembershipsForCurrentUser/",
                headers=headers,
            )
            res.raise_for_status()
            return res.json()["Response"]

    async def get_profile(self, membership_type: int, destiny_membership_id: str, access_token: str):
        headers = {
            "X-API-Key": self.api_key,
            "Authorization": f"Bearer {access_token}",
        }
        # 200 = characters, 205 = character equipment
        components = "200,205"
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{BUNGIE_ROOT}/Platform/Destiny2/{membership_type}/Profile/{destiny_membership_id}/?components={components}",
                headers=headers,
            )
            res.raise_for_status()
            return res.json()["Response"]
