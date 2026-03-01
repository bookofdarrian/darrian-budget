"""
ebay_search.py — eBay Browse API helpers for the Sole Alert Bot.
Reuses the same logic already in pages/3_business_tracker.py.
Drop this in /opt/sole-alert/ on CT100.
"""

import base64
import logging
import requests

log = logging.getLogger(__name__)

EBAY_TOKEN_URL  = "https://api.ebay.com/identity/v1/oauth2/token"
EBAY_SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"
SNEAKERS_CATEGORY = "15709"   # eBay sneakers category ID


def get_ebay_token(client_id: str, client_secret: str) -> str | None:
    """Exchange eBay client credentials for an OAuth application token."""
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    try:
        r = requests.post(
            EBAY_TOKEN_URL,
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data="grant_type=client_credentials&scope=https%3A%2F%2Fapi.ebay.com%2Foauth%2Fapi_scope",
            timeout=15,
        )
        if r.status_code == 200:
            return r.json().get("access_token")
        log.warning("eBay token request failed: HTTP %s — %s", r.status_code, r.text[:200])
        return None
    except Exception as e:
        log.error("eBay token error: %s", e)
        return None


def ebay_search(query: str, token: str, limit: int = 20) -> list[dict]:
    """
    Search eBay active listings (Buy It Now) in the sneakers category.

    Returns:
        List of dicts: {title, price, condition, item_url, source}
    """
    if not token:
        return []
    try:
        r = requests.get(
            EBAY_SEARCH_URL,
            headers={"Authorization": f"Bearer {token}"},
            params={
                "q": query,
                "category_ids": SNEAKERS_CATEGORY,
                "filter": "buyingOptions:{FIXED_PRICE}",
                "sort": "newlyListed",
                "limit": limit,
                "fieldgroups": "MATCHING_ITEMS",
            },
            timeout=15,
        )
        if r.status_code != 200:
            log.warning("eBay search failed: HTTP %s — %s", r.status_code, r.text[:200])
            return []

        items = r.json().get("itemSummaries", [])
        results = []
        for item in items:
            price_info = item.get("price", {})
            try:
                price = float(price_info.get("value", 0))
            except (TypeError, ValueError):
                price = 0.0
            results.append({
                "title":     item.get("title", ""),
                "price":     price,
                "condition": item.get("condition", ""),
                "item_url":  item.get("itemWebUrl", ""),
                "source":    "eBay",
            })
        return results

    except requests.exceptions.Timeout:
        log.error("eBay search timed out for query: %s", query)
        return []
    except Exception as e:
        log.error("eBay search error for '%s': %s", query, e)
        return []


def ebay_avg_price(query: str, token: str, limit: int = 20) -> float:
    """Return average active listing price on eBay. 0.0 if no results."""
    results = ebay_search(query, token, limit=limit)
    prices = [r["price"] for r in results if r["price"] > 0]
    return round(sum(prices) / len(prices), 2) if prices else 0.0


def ebay_low_price(query: str, token: str, limit: int = 20) -> float:
    """Return lowest active listing price on eBay. 0.0 if no results."""
    results = ebay_search(query, token, limit=limit)
    prices = [r["price"] for r in results if r["price"] > 0]
    return min(prices) if prices else 0.0


if __name__ == "__main__":
    # Quick test — run: EBAY_CLIENT_ID=xxx EBAY_CLIENT_SECRET=yyy python ebay_search.py
    import os
    logging.basicConfig(level=logging.INFO)
    cid = os.environ.get("EBAY_CLIENT_ID", "")
    csc = os.environ.get("EBAY_CLIENT_SECRET", "")
    if not cid or not csc:
        print("Set EBAY_CLIENT_ID and EBAY_CLIENT_SECRET env vars to test.")
    else:
        tok = get_ebay_token(cid, csc)
        if tok:
            test_query = "Jordan 1 Retro High OG Chicago size 10"
            print(f"\nSearching eBay for: {test_query}\n")
            results = ebay_search(test_query, tok, limit=10)
            for r in results[:5]:
                print(f"  ${r['price']:>7.2f}  {r['condition']:<20}  {r['title'][:55]}")
            print(f"\n  Avg: ${ebay_avg_price(test_query, tok):.2f}  |  Low: ${ebay_low_price(test_query, tok):.2f}")
        else:
            print("Failed to get eBay token — check your credentials.")
