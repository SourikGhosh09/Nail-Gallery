"""Public catalogue: search, filtering, combined queries, sort, pagination."""
from __future__ import annotations

import pytest

from helpers import create_category, create_nail


@pytest.fixture
def catalogue(auth_client):
    """Seed a small, known catalogue and return the client + category ids."""
    chrome = create_category(auth_client, "Chrome").json()["item"]["id"]
    bridal = create_category(auth_client, "Bridal").json()["item"]["id"]
    create_nail(auth_client, "Midnight Chrome", chrome, price=849,
                description="Deep graphite chrome with a liquid mirror shine.")
    create_nail(auth_client, "Royal Pink Chrome", chrome, price=799,
                description="Glossy pink mirror finish with pearl accents.")
    create_nail(auth_client, "Soft Pink Bridal", bridal, price=1299,
                description="Delicate blush tones with subtle pearl accents.")
    return auth_client, {"chrome": chrome, "bridal": bridal}


def _totals(client, query):
    return client.get(f"/api/nail-arts{query}").json()


def test_search_by_name_partial_and_case_insensitive(catalogue):
    client, _ = catalogue
    assert _totals(client, "?search=chrome")["total"] == 2
    assert _totals(client, "?search=CHROME")["total"] == 2   # case-insensitive
    assert _totals(client, "?search=chrom")["total"] == 2    # partial match


def test_search_matches_description(catalogue):
    client, _ = catalogue
    # "pearl" appears only in descriptions, not names.
    result = _totals(client, "?search=pearl")
    names = {item["name"] for item in result["items"]}
    assert result["total"] == 2
    assert names == {"Royal Pink Chrome", "Soft Pink Bridal"}


def test_filter_by_category(catalogue):
    client, _ = catalogue
    result = _totals(client, "?category=chrome")
    assert result["total"] == 2
    assert all(item["category"]["slug"] == "chrome" for item in result["items"])


def test_combined_search_and_filter(catalogue):
    client, _ = catalogue
    result = _totals(client, "?search=midnight&category=chrome")
    assert result["total"] == 1
    assert result["items"][0]["name"] == "Midnight Chrome"


def test_search_with_no_matches_is_empty(catalogue):
    client, _ = catalogue
    assert _totals(client, "?search=zzz-nothing")["total"] == 0


def test_sort_price_ascending(catalogue):
    client, _ = catalogue
    prices = [item["price"] for item in _totals(client, "?sort=price_asc")["items"]]
    assert prices == sorted(prices)
    assert prices[0] == 799.0


def test_sort_price_descending(catalogue):
    client, _ = catalogue
    prices = [item["price"] for item in _totals(client, "?sort=price_desc")["items"]]
    assert prices == sorted(prices, reverse=True)


def test_pagination(catalogue):
    client, _ = catalogue
    page1 = _totals(client, "?page=1&page_size=2")
    assert page1["total"] == 3
    assert page1["pages"] == 2
    assert len(page1["items"]) == 2
    assert page1["has_next"] is True
    assert page1["has_prev"] is False

    page2 = _totals(client, "?page=2&page_size=2")
    assert len(page2["items"]) == 1
    assert page2["has_next"] is False
    assert page2["has_prev"] is True


def test_detail_endpoint_returns_item_and_related(catalogue):
    client, _ = catalogue
    resp = client.get("/api/nail-arts/midnight-chrome")
    assert resp.status_code == 200
    body = resp.json()
    assert body["item"]["name"] == "Midnight Chrome"
    # Related designs come from the same (Chrome) category, excluding itself.
    related_names = {r["name"] for r in body["related"]}
    assert "Royal Pink Chrome" in related_names
    assert "Midnight Chrome" not in related_names
    assert "Soft Pink Bridal" not in related_names


def test_detail_endpoint_404_for_unknown(catalogue):
    client, _ = catalogue
    assert client.get("/api/nail-arts/does-not-exist").status_code == 404


def test_inactive_design_is_hidden_publicly(catalogue):
    client, ids = catalogue
    # Deactivate one chrome design.
    target = client.get("/api/nail-arts/royal-pink-chrome").json()["item"]["id"]
    client.patch(f"/api/admin/nail-arts/{target}/status?status=inactive")
    assert _totals(client, "?search=chrome")["total"] == 1
    # Its detail page is now a 404 for the public.
    assert client.get("/api/nail-arts/royal-pink-chrome").status_code == 404


def test_inactive_category_hides_its_designs(catalogue):
    client, ids = catalogue
    client.patch(f"/api/admin/categories/{ids['chrome']}/status?status=inactive")
    # Both chrome designs disappear from the public catalogue.
    assert _totals(client, "?search=chrome")["total"] == 0
    assert _totals(client, "?category=chrome")["total"] == 0
    # Bridal is unaffected.
    assert _totals(client, "?category=bridal")["total"] == 1


def test_public_categories_endpoint_reports_counts(catalogue):
    client, _ = catalogue
    cats = {c["name"]: c for c in client.get("/api/categories").json()["items"]}
    assert cats["Chrome"]["design_count"] == 2
    assert cats["Chrome"]["active_design_count"] == 2
    assert cats["Bridal"]["design_count"] == 1
