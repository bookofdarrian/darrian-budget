"""
mercari_search.py — Mercari US search via internal API endpoint.
No API key required. Drop this in /opt/sole-alert/ on CT100.
"""

import requests
import logging

log = logging.getLogger(__name__)

MERCARI_URL = "https://api.mercari.com/v2/entities:search"

HEADERS = {
    "Content-Type": "application/json",
    "X-Platform": "web",
    "Accept": "application/json, text/plain, */*",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "DPR": "2",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": "https://www.mercari.com",
    "Referer": "https://www.mercari.com/",
}


def mercari_search(query: str, limit: int = 30, status: str = "on_sale") -> list[dict]:
    """
    Search Mercari US for active listings.

    Args:
        query:  Search term, e.g. "Jordan 1 Chicago size 10"
        limit:  Max results (Mercari pages at 30; use multiples of 30 for more)
        status: "on_sale" | "sold_out" | "all"

    Returns:
        List of dicts: {name, price, condition, item_url, source}
    """
    status_map = {
        "on_sale":  ["STATUS_ON_SALE"],
        "sold_out": ["STATUS_SOLD_OUT"],
        "all":      ["STATUS_ON_SALE", "STATUS_SOLD_OUT"],
    }

    payload = {
        "userId": "",
        "pageSize": min(limit, 120),   # Mercari caps at 120
        "pageToken": "",
        "searchSessionId": "",
        "indexRouting": "INDEX_ROUTING_UNSPECIFIED",
        "thumbnailTypes": [],
        "searchCondition": {
            "keyword": query,
            "excludeKeyword": "",
            "sort": "SORT_SCORE",
            "order": "ORDER_DESC",
            "status": status_map.get(status, ["STATUS_ON_SALE"]),
            "sizeId": [],
            "brandId": [],
            "sellerId": [],
            "priceMin": 0,
            "priceMax": 0,
            "itemConditionId": [],
            "shippingPayerId": [],
            "shippingFromArea": [],
            "shippingMethod": [],
            "categoryId": [],
            "color": [],
            "hasCoupon": False,
            "attributes": [],
            "itemTypes": [],
            "skuIds": [],
        },
        "defaultDatasets": ["DATASET_TYPE_MERCARI", "DATASET_TYPE_BEYOND"],
        "serviceFrom": "suruga",
        "withItemBrand": True,
        "withItemSize": True,
        "withItemPromotions": False,
        "withItemSizes": True,
        "withShopname": False,
    }

    try:
        r = requests.post(MERCARI_URL, headers=HEADERS, json=payload, timeout=20)
        if r.status_code != 200:
            log.warning("Mercari returned HTTP %s: %s", r.status_code, r.text[:200])
            return []

        data = r.json()
        items = data.get("items", [])
        results = []

        for item in items:
            price_raw = item.get("price", 0)
            try:
                price = int(price_raw)
            except (TypeError, ValueError):
                price = 0

            item_id = item.get("id", "")
            results.append({
                "name":      item.get("name", ""),
                "price":     price,
                "condition": item.get("itemCondition", {}).get("name", ""),
                "status":    item.get("status", ""),
                "item_url":  f"https://www.mercari.com/us/item/{item_id}/",
                "source":    "Mercari",
            })

        return results

    except requests.exceptions.Timeout:
        log.error("Mercari request timed out for query: %s", query)
        return []
    except Exception as e:
        log.error("Mercari search error for '%s': %s", query, e)
        return []


def mercari_avg_price(query: str, limit: int = 20) -> float:
    """Return average price of active Mercari listings for a query. 0.0 if no results."""
    results = mercari_search(query, limit=limit, status="on_sale")
    prices = [r["price"] for r in results if r["price"] > 0]
    return round(sum(prices) / len(prices), 2) if prices else 0.0


def mercari_low_price(query: str, limit: int = 20) -> float:
    """Return lowest active listing price on Mercari. 0.0 if no results."""
    results = mercari_search(query, limit=limit, status="on_sale")
    prices = [r["price"] for r in results if r["price"] > 0]
    return min(prices) if prices else 0.0


if __name__ == "__main__":
    # Quick test — run: python mercari_search.py
    import json
    logging.basicConfig(level=logging.INFO)
    test_query = "Jordan 1 Retro High OG Chicago size 10"
    print(f"\nSearching Mercari for: {test_query}\n")
    results = mercari_search(test_query, limit=10)
    if results:
        for r in results[:5]:
            print(f"  ${r['price']:>6}  {r['condition']:<20}  {r['name'][:60]}")
        print(f"\n  Avg: ${mercari_avg_price(test_query):.2f}  |  Low: ${mercari_low_price(test_query):.2f}")
    else:
        print("  No results — Mercari endpoint may have changed. Check mercarius on GitHub.")
