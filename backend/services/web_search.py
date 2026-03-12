"""
Web Search Service
Uses Serper.dev API (Google Search wrapper) for:
  - Company news and reputation research
  - Litigation history searches
  - Regulatory/sector updates
"""
import httpx
from typing import List
from config import SERPER_API_KEY

SERPER_URL = "https://google.serper.dev/search"


async def _serper_search(query: str, num: int = 5) -> List[dict]:
    """Call Serper API and return list of result dicts."""
    if not SERPER_API_KEY:
        # Return mock data if key not configured
        return [
            {
                "title": f"[Demo] {query}",
                "snippet": "Configure SERPER_API_KEY to get real web search results.",
                "link": "https://serper.dev",
            }
        ]
    if not query or not query.strip():
        return []
    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {"q": query, "num": num, "gl": "in", "hl": "en"}
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.post(SERPER_URL, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            results = []
            for item in data.get("organic", []):
                results.append({
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "link": item.get("link", ""),
                    "date": item.get("date", ""),
                })
            return results
        except Exception as e:
            return [{"title": "Search failed", "snippet": str(e), "link": ""}]


async def search_news(query: str) -> List[dict]:
    """General news search."""
    return await _serper_search(query, num=6)


async def search_litigation(company_name: str) -> List[dict]:
    """Search for litigation, court cases, legal disputes."""
    queries = [
        f"{company_name} India court case lawsuit NCLT DRT insolvency",
        f"{company_name} SEBI enforcement action penalty India",
        f'"{company_name}" eCourt India legal dispute NPA',
    ]
    results = []
    for q in queries[:2]:  # Limit API calls
        results.extend(await _serper_search(q, num=3))
    return results


async def search_regulatory(sector: str) -> List[dict]:
    """Search for sector-specific regulatory updates."""
    if not sector:
        return []
    queries = [
        f"RBI SEBI regulation {sector} India 2024 2025",
        f"{sector} sector NPA stress India banking 2024",
    ]
    results = []
    for q in queries:
        results.extend(await _serper_search(q, num=3))
    return results
