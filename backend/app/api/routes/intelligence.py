from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.db.database import get_db
from app.db.models import WebIntelligenceCache
from app.scraper.scraper import get_web_intelligence

router = APIRouter()


@router.get("/intelligence/reputation")
async def get_reputation(
    company: str = Query(..., description="Company name to look up"),
    force_refresh: bool = Query(False, description="Force fresh scrape"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current public sentiment for a company.
    Checks cache first — scrapes if cache expired or force_refresh=true.
    """
    result = await get_web_intelligence(
        company_name=company,
        db=db,
        force_refresh=force_refresh,
    )
    return result


@router.get("/intelligence/cache")
async def get_cache_status(
    db: AsyncSession = Depends(get_db)
):
    """Show all cached web intelligence entries."""
    result = await db.execute(
        select(WebIntelligenceCache)
        .order_by(desc(WebIntelligenceCache.scraped_at))
    )
    entries = result.scalars().all()

    return {
        "total_cached": len(entries),
        "entries": [
            {
                "id": e.id,
                "target_entity": e.target_entity,
                "scraped_at": str(e.scraped_at),
                "expires_at": str(e.expires_at),
                "source_url": e.source_url,
            }
            for e in entries
        ]
    }