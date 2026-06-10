import httpx
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import WebIntelligenceCache


# --- Trigger conditions (from assessment) ---
SCRAPE_TRIGGERS = [
    "review", "trustpilot", "g2", "twitter", "post publicly",
    "capterra", "glassdoor", "reddit"
]

CACHE_HOURS = 6


def should_scrape(subject: str, body: str, sentiment_score: float, category: str) -> bool:
    """Check if web intelligence scraping should be triggered."""
    text = f"{subject or ''} {body or ''}".lower()

    keyword_match = any(trigger in text for trigger in SCRAPE_TRIGGERS)
    sentiment_trigger = sentiment_score is not None and sentiment_score < -0.6
    category_trigger = category in ["Complaint"] and sentiment_score is not None and sentiment_score < -0.5

    return keyword_match or sentiment_trigger or category_trigger


async def get_cached_intelligence(
    target_entity: str,
    db: AsyncSession
) -> Optional[dict]:
    """Check if we have fresh cached data for this entity."""
    result = await db.execute(
        select(WebIntelligenceCache)
        .where(WebIntelligenceCache.target_entity == target_entity)
        .where(WebIntelligenceCache.expires_at > datetime.now(timezone.utc))
        .order_by(WebIntelligenceCache.scraped_at.desc())
    )
    cached = result.scalar_one_or_none()

    if cached:
        return cached.scraped_data
    return None


async def save_to_cache(
    target_entity: str,
    source_url: str,
    scraped_data: dict,
    db: AsyncSession
):
    """Save scrape results to cache with 6-hour expiry."""
    cache_entry = WebIntelligenceCache(
        source_url=source_url,
        target_entity=target_entity,
        scraped_data=scraped_data,
        scraped_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=CACHE_HOURS),
    )
    db.add(cache_entry)
    await db.flush()


async def check_robots_txt(base_url: str) -> bool:
    """Check robots.txt compliance before scraping."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{base_url}/robots.txt")
            if response.status_code == 200:
                robots_content = response.text.lower()
                # Check if scraping is disallowed for all agents
                if "user-agent: *" in robots_content and "disallow: /" in robots_content:
                    return False
            return True
    except Exception:
        return True  # Allow if robots.txt unreachable


async def scrape_g2_rating(company_name: str) -> dict:
    """
    Scrape G2 rating for a company.
    Returns rating, review count, and recent themes.
    """
    allowed = await check_robots_txt("https://www.g2.com")
    if not allowed:
        return {
            "source": "G2",
            "error": "Blocked by robots.txt",
            "company": company_name,
        }

    try:
        search_url = f"https://www.g2.com/search?query={company_name.replace(' ', '+')}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get(search_url, headers=headers)

        if response.status_code != 200:
            return {
                "source": "G2",
                "error": f"HTTP {response.status_code}",
                "company": company_name,
            }

        soup = BeautifulSoup(response.text, "html.parser")

        # Try to find rating elements
        rating_elem = soup.find("span", {"class": lambda x: x and "rating" in x.lower()})
        rating = rating_elem.text.strip() if rating_elem else "N/A"

        return {
            "source": "G2",
            "company": company_name,
            "rating": rating,
            "url": search_url,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "status": "scraped",
        }

    except Exception as e:
        return {
            "source": "G2",
            "error": str(e),
            "company": company_name,
            "status": "failed",
        }


async def scrape_trustpilot_rating(company_name: str) -> dict:
    """
    Scrape Trustpilot rating for a company.
    """
    allowed = await check_robots_txt("https://www.trustpilot.com")
    if not allowed:
        return {
            "source": "Trustpilot",
            "error": "Blocked by robots.txt",
            "company": company_name,
        }

    try:
        slug = company_name.lower().replace(" ", "-")
        url = f"https://www.trustpilot.com/review/{slug}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)

        if response.status_code != 200:
            return {
                "source": "Trustpilot",
                "error": f"HTTP {response.status_code}",
                "company": company_name,
                "status": "failed",
            }

        soup = BeautifulSoup(response.text, "html.parser")

        # Try to find TrustScore
        score_elem = soup.find("span", {"data-rating-typography": True})
        if not score_elem:
            score_elem = soup.find("p", {"class": lambda x: x and "score" in str(x).lower()})

        score = score_elem.text.strip() if score_elem else "N/A"

        # Try to find review count
        count_elem = soup.find("span", {"class": lambda x: x and "count" in str(x).lower()})
        count = count_elem.text.strip() if count_elem else "N/A"

        return {
            "source": "Trustpilot",
            "company": company_name,
            "score": score,
            "review_count": count,
            "url": url,
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "status": "scraped",
        }

    except Exception as e:
        return {
            "source": "Trustpilot",
            "error": str(e),
            "company": company_name,
            "status": "failed",
        }


async def get_web_intelligence(
    company_name: str,
    db: AsyncSession,
    force_refresh: bool = False,
) -> dict:
    """
    Main entry point — gets web intelligence for a company.
    Checks cache first, scrapes if needed.
    Fails gracefully if scraping fails.
    """
    if not force_refresh:
        cached = await get_cached_intelligence(company_name, db)
        if cached:
            cached["from_cache"] = True
            return cached

    # Scrape both sources concurrently
    g2_task = scrape_g2_rating(company_name)
    trustpilot_task = scrape_trustpilot_rating(company_name)

    g2_result, trustpilot_result = await asyncio.gather(
        g2_task, trustpilot_task,
        return_exceptions=True
    )

    # Handle exceptions gracefully
    if isinstance(g2_result, Exception):
        g2_result = {"source": "G2", "error": str(g2_result), "status": "failed"}
    if isinstance(trustpilot_result, Exception):
        trustpilot_result = {"source": "Trustpilot", "error": str(trustpilot_result), "status": "failed"}

    intelligence = {
        "company": company_name,
        "g2": g2_result,
        "trustpilot": trustpilot_result,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "from_cache": False,
    }

    # Save to cache
    try:
        await save_to_cache(
            target_entity=company_name,
            source_url=f"multi:{company_name}",
            scraped_data=intelligence,
            db=db,
        )
    except Exception:
        pass  # Don't fail if cache write fails

    return intelligence