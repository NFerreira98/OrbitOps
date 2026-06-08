import asyncio
import json
from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.bungie.manifest import ManifestManager

router = APIRouter(prefix="/api", tags=["catalog"])
manifest = ManifestManager()

BUNGIE_ROOT = "https://www.bungie.net"


class CatalogItem(BaseModel):
    hash: int
    name: str
    icon: str | None
    flavorText: str | None
    tierType: int
    itemType: int
    itemSubType: int
    classType: int
    collectibleHash: int | None
    sourceString: str | None


class CatalogResponse(BaseModel):
    items: list[CatalogItem]
    total: int


@router.get("/catalog", response_model=CatalogResponse)
async def get_catalog(
    tier: int = Query(6, description="6=Exotic, 5=Legendary"),
    item_type: int | None = Query(None, description="2=Armor, 3=Weapon"),
    class_type: int | None = Query(None, description="0=Titan, 1=Hunter, 2=Warlock"),
    search: str | None = Query(None),
):
    raw_items, source_map = await asyncio.gather(
        manifest.get_catalog_items(
            tier=tier,
            item_type=item_type,
            class_type=class_type,
            search=search,
        ),
        manifest.get_all_collectibles_with_source(),
    )

    items: list[CatalogItem] = []
    for item in raw_items:
        icon = item.get("icon")
        col_hash = item.get("collectibleHash")
        items.append(
            CatalogItem(
                hash=item["hash"],
                name=item["name"],
                icon=f"{BUNGIE_ROOT}{icon}" if icon else None,
                flavorText=item.get("flavorText") or None,
                tierType=item["tierType"],
                itemType=item["itemType"],
                itemSubType=item["itemSubType"],
                classType=item["classType"],
                collectibleHash=col_hash,
                sourceString=source_map.get(col_hash) if col_hash else None,
            )
        )

    items.sort(key=lambda x: x.name)

    return CatalogResponse(items=items, total=len(items))
