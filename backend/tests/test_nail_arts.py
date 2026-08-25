"""Nail-art CRUD, validation, image-upload rejection, and soft delete."""
from __future__ import annotations

from helpers import create_category, create_nail, make_png


def _category(auth_client, name="Chrome"):
    return create_category(auth_client, name).json()["item"]["id"]


def test_create_nail_with_image(auth_client):
    cid = _category(auth_client)
    resp = create_nail(
        auth_client, "Royal Pink Chrome", cid, price=799,
        description="Glossy mirror chrome finish.", image=make_png(),
        image_alt="Pink chrome nails",
    )
    assert resp.status_code == 201, resp.text
    item = resp.json()["item"]
    assert item["name"] == "Royal Pink Chrome"
    assert item["slug"] == "royal-pink-chrome"
    assert item["price"] == 799.0
    assert item["image_url"].startswith("/media/")
    assert item["image_alt"] == "Pink chrome nails"
    assert item["category"]["id"] == cid


def test_create_nail_without_image_is_allowed(auth_client):
    cid = _category(auth_client)
    resp = create_nail(auth_client, "No Photo Yet", cid)
    assert resp.status_code == 201, resp.text
    assert resp.json()["item"]["image_url"] is None


def test_create_nail_blank_name_is_validation_error(auth_client):
    cid = _category(auth_client)
    resp = create_nail(auth_client, "   ", cid)
    assert resp.status_code == 422
    assert "name" in resp.json()["detail"]["errors"]


def test_create_nail_negative_price_is_validation_error(auth_client):
    cid = _category(auth_client)
    resp = create_nail(auth_client, "Cheapskate", cid, price=-10)
    assert resp.status_code == 422
    assert "price" in resp.json()["detail"]["errors"]


def test_create_nail_nonnumeric_price_is_validation_error(auth_client):
    cid = _category(auth_client)
    resp = auth_client.post(
        "/api/admin/nail-arts",
        data={
            "name": "Bad Price", "description": "x", "price": "abc",
            "category_id": str(cid), "status": "active",
        },
    )
    assert resp.status_code == 422
    assert "price" in resp.json()["detail"]["errors"]


def test_create_nail_nonexistent_category_is_rejected(auth_client):
    resp = create_nail(auth_client, "Orphan Design", category_id=99999)
    assert resp.status_code == 422
    assert "category_id" in resp.json()["detail"]["errors"]


def test_upload_rejects_non_image_content(auth_client):
    cid = _category(auth_client)
    resp = auth_client.post(
        "/api/admin/nail-arts",
        data={"name": "Fake Image", "description": "x", "price": "10",
              "category_id": str(cid), "status": "active"},
        files={"image": ("design.png", b"this is not an image", "image/png")},
    )
    assert resp.status_code == 422
    assert "image" in resp.json()["detail"]["errors"]


def test_upload_rejects_disallowed_extension(auth_client):
    cid = _category(auth_client)
    resp = auth_client.post(
        "/api/admin/nail-arts",
        data={"name": "Script Kiddie", "description": "x", "price": "10",
              "category_id": str(cid), "status": "active"},
        files={"image": ("payload.txt", b"plain text", "text/plain")},
    )
    assert resp.status_code == 422
    assert "image" in resp.json()["detail"]["errors"]


def test_update_nail(auth_client):
    cid = _category(auth_client)
    nail_id = create_nail(auth_client, "Old Name", cid, price=500).json()["item"]["id"]
    resp = auth_client.put(
        f"/api/admin/nail-arts/{nail_id}",
        data={"name": "New Name", "description": "Updated copy.",
              "price": "650", "category_id": str(cid), "status": "active"},
    )
    assert resp.status_code == 200, resp.text
    item = resp.json()["item"]
    assert item["name"] == "New Name"
    assert item["slug"] == "new-name"
    assert item["price"] == 650.0


def test_replace_nail_image(auth_client):
    cid = _category(auth_client)
    created = create_nail(auth_client, "Photo Design", cid, image=make_png((10, 20, 30))).json()["item"]
    original = created["image_url"]
    resp = auth_client.put(
        f"/api/admin/nail-arts/{created['id']}",
        data={"name": "Photo Design", "description": created["description"],
              "price": "500", "category_id": str(cid), "status": "active"},
        files={"image": ("new.png", make_png((90, 80, 70)), "image/png")},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["item"]["image_url"].startswith("/media/")
    assert resp.json()["item"]["image_url"] != original


def test_soft_delete_hides_from_public(auth_client):
    cid = _category(auth_client)
    nail_id = create_nail(auth_client, "Vanishing Act", cid).json()["item"]["id"]
    # Present publicly while active.
    assert auth_client.get("/api/nail-arts?search=Vanishing").json()["total"] == 1
    # Soft delete (deactivate) via DELETE without ?hard.
    resp = auth_client.delete(f"/api/admin/nail-arts/{nail_id}")
    assert resp.status_code == 200
    assert resp.json()["item"]["status"] == "inactive"
    # Gone from the public catalogue, but still in the admin database.
    assert auth_client.get("/api/nail-arts?search=Vanishing").json()["total"] == 0
    assert auth_client.get(f"/api/admin/nail-arts/{nail_id}").status_code == 200


def test_status_toggle_reactivates(auth_client):
    cid = _category(auth_client)
    nail_id = create_nail(auth_client, "Toggle Me", cid).json()["item"]["id"]
    auth_client.patch(f"/api/admin/nail-arts/{nail_id}/status?status=inactive")
    resp = auth_client.patch(f"/api/admin/nail-arts/{nail_id}/status?status=active")
    assert resp.status_code == 200
    assert resp.json()["item"]["status"] == "active"


def test_hard_delete_removes_permanently(auth_client):
    cid = _category(auth_client)
    nail_id = create_nail(auth_client, "Delete Forever", cid).json()["item"]["id"]
    resp = auth_client.delete(f"/api/admin/nail-arts/{nail_id}?hard=true")
    assert resp.status_code == 200
    assert auth_client.get(f"/api/admin/nail-arts/{nail_id}").status_code == 404


def test_dashboard_reports_counts(auth_client):
    cid = _category(auth_client)
    create_nail(auth_client, "Design A", cid)
    create_nail(auth_client, "Design B", cid, status="inactive")
    stats = auth_client.get("/api/admin/dashboard").json()
    assert stats["total_nail_arts"] == 2
    assert stats["active_nail_arts"] == 1
    assert stats["inactive_nail_arts"] == 1
    assert stats["total_categories"] >= 1
    assert len(stats["recent_nail_arts"]) == 2
