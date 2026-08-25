"""Category CRUD, duplicate protection, and safe (orphan-free) deletion."""
from __future__ import annotations

from helpers import create_category, create_nail


def test_create_category(auth_client):
    resp = create_category(auth_client, "Bridal", "For the big day.")
    assert resp.status_code == 201, resp.text
    item = resp.json()["item"]
    assert item["name"] == "Bridal"
    assert item["slug"] == "bridal"
    assert item["status"] == "active"
    assert item["design_count"] == 0


def test_duplicate_category_name_is_rejected(auth_client):
    assert create_category(auth_client, "Chrome").status_code == 201
    # Case-insensitive duplicate must be rejected with a 409 conflict.
    dup = create_category(auth_client, "chrome")
    assert dup.status_code == 409
    assert dup.json()["detail"]["errors"]["name"]


def test_blank_category_name_is_validation_error(auth_client):
    resp = create_category(auth_client, "   ")
    assert resp.status_code == 422


def test_update_category(auth_client):
    cid = create_category(auth_client, "Frenchh").json()["item"]["id"]
    resp = auth_client.put(
        f"/api/admin/categories/{cid}",
        data={"name": "French", "description": "Classic tips.", "status": "active"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["item"]["name"] == "French"
    assert resp.json()["item"]["slug"] == "french"


def test_rename_onto_existing_name_is_rejected(auth_client):
    create_category(auth_client, "Party")
    cid = create_category(auth_client, "Minimal").json()["item"]["id"]
    resp = auth_client.put(
        f"/api/admin/categories/{cid}",
        data={"name": "party", "status": "active"},
    )
    assert resp.status_code == 409


def test_delete_empty_category_succeeds(auth_client):
    cid = create_category(auth_client, "Temporary").json()["item"]["id"]
    resp = auth_client.delete(f"/api/admin/categories/{cid}")
    assert resp.status_code == 200
    # It is really gone.
    assert auth_client.get(f"/api/admin/categories/{cid}").status_code == 404


def test_delete_category_with_designs_is_blocked(auth_client):
    """Orphan prevention: cannot delete a category that still holds designs."""
    cid = create_category(auth_client, "Gel").json()["item"]["id"]
    create_nail(auth_client, "Glossy Gel", cid)
    resp = auth_client.delete(f"/api/admin/categories/{cid}")
    assert resp.status_code == 409
    detail = resp.json()["detail"]
    assert detail["requires_action"] is True
    assert detail["design_count"] == 1
    assert set(detail["options"]) == {"deactivate", "reassign"}
    # Category and its design must still exist untouched.
    assert auth_client.get(f"/api/admin/categories/{cid}").status_code == 200


def test_delete_category_with_deactivate_action(auth_client):
    cid = create_category(auth_client, "Seasonal").json()["item"]["id"]
    create_nail(auth_client, "Winter Frost", cid)
    resp = auth_client.delete(f"/api/admin/categories/{cid}?action=deactivate")
    assert resp.status_code == 200
    # Still exists but is now inactive (hidden from the public site).
    got = auth_client.get(f"/api/admin/categories/{cid}")
    assert got.status_code == 200
    assert got.json()["item"]["status"] == "inactive"


def test_delete_category_with_reassign_moves_designs(auth_client):
    src = create_category(auth_client, "OldCat").json()["item"]["id"]
    dst = create_category(auth_client, "NewCat").json()["item"]["id"]
    nail_id = create_nail(auth_client, "Movable Design", src).json()["item"]["id"]

    resp = auth_client.delete(
        f"/api/admin/categories/{src}?action=reassign&target_category_id={dst}"
    )
    assert resp.status_code == 200
    # Source category is deleted...
    assert auth_client.get(f"/api/admin/categories/{src}").status_code == 404
    # ...and the design now belongs to the destination category.
    moved = auth_client.get(f"/api/admin/nail-arts/{nail_id}").json()["item"]
    assert moved["category_id"] == dst


def test_reassign_requires_a_different_target(auth_client):
    cid = create_category(auth_client, "Solo").json()["item"]["id"]
    create_nail(auth_client, "Only Design", cid)
    # Reassigning to itself (or with no target) is refused.
    resp = auth_client.delete(
        f"/api/admin/categories/{cid}?action=reassign&target_category_id={cid}"
    )
    assert resp.status_code == 422


def test_new_category_appears_on_public_endpoint(auth_client):
    """Categories are DB-driven: a new one shows up publicly automatically."""
    create_category(auth_client, "Holographic")
    names = [c["name"] for c in auth_client.get("/api/categories").json()["items"]]
    assert "Holographic" in names


def test_inactive_category_hidden_from_public_endpoint(auth_client):
    cid = create_category(auth_client, "HiddenCat").json()["item"]["id"]
    auth_client.patch(f"/api/admin/categories/{cid}/status?status=inactive")
    names = [c["name"] for c in auth_client.get("/api/categories").json()["items"]]
    assert "HiddenCat" not in names
