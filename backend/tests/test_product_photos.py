from app.config import settings
import json
from PIL import Image
from helpers import create_category, create_nail, make_png


def test_multiple_photos_append_remove_and_public_gallery(auth_client):
    cid = create_category(auth_client, "Gallery").json()["item"]["id"]
    data = {"name": "Many Photos", "description": "Several angles", "price": "500", "category_id": str(cid)}
    response = auth_client.post("/api/admin/nail-arts", data=data, files=[
        ("images", ("one.png", make_png(), "image/png")),
        ("images", ("two.png", make_png((10, 20, 30)), "image/png")),
    ])
    assert response.status_code == 201, response.text
    item = response.json()["item"]
    assert len(item["images"]) == 2
    cover = item["image_path"]
    page = auth_client.get(f"/nail/{item['slug']}")
    assert page.status_code == 200
    for photo in item["images"]:
        assert photo["image_url"] in page.text
    assert "product-gallery.js" in page.text
    assert "multiple" in auth_client.get(f"/admin/nail-arts/{item['id']}/edit").text
    response = auth_client.put(f"/api/admin/nail-arts/{item['id']}", data=data,
                               files=[("images", ("three.png", make_png(), "image/png"))])
    assert len(response.json()["item"]["images"]) == 3
    response = auth_client.put(f"/api/admin/nail-arts/{item['id']}", data={**data, "remove_images": cover})
    updated = response.json()["item"]
    assert len(updated["images"]) == 2
    assert updated["image_path"] == item["images"][1]["image_path"]
    assert not (settings.upload_path / cover).exists()
    paths = [photo["image_path"] for photo in updated["images"]]
    auth_client.delete(f"/api/admin/nail-arts/{item['id']}?hard=true")
    assert all(not (settings.upload_path / path).exists() for path in paths)


def test_invalid_batch_preserves_existing_photos_and_cleans_uploads(auth_client):
    cid = create_category(auth_client, "Validation").json()["item"]["id"]
    item = create_nail(auth_client, "Original", cid, image=make_png()).json()["item"]
    before = set(settings.upload_path.iterdir())
    response = auth_client.put(f"/api/admin/nail-arts/{item['id']}",
        data={"name": "Original", "description": "Keep", "price": "500", "category_id": str(cid), "remove_images": item["image_path"]},
        files=[("images", ("good.png", make_png(), "image/png")),
               ("images", ("bad.png", b"invalid", "image/png"))])
    assert response.status_code == 422
    assert set(settings.upload_path.iterdir()) == before
    assert auth_client.get(f"/api/admin/nail-arts/{item['id']}").json()["item"]["image_path"] == item["image_path"]


def test_reorder_cover_and_crop_are_persisted(auth_client):
    cid = create_category(auth_client, "Editing").json()["item"]["id"]
    data = {"name": "Editable", "description": "Angles", "price": "100", "category_id": str(cid)}
    item = auth_client.post("/api/admin/nail-arts", data=data, files=[
        ("images", ("one.png", make_png(), "image/png")),
        ("images", ("two.png", make_png(), "image/png")),
        ("images", ("three.png", make_png(), "image/png")),
    ]).json()["item"]
    paths = [photo["image_path"] for photo in item["images"]]
    order = [paths[2], paths[0], paths[1]]
    response = auth_client.put(f"/api/admin/nail-arts/{item['id']}", data={**data, "image_order": order,
        "photo_edits": json.dumps({paths[2]: {"x": 0.25, "y": 0.25, "width": 0.5, "height": 0.5, "rotation": 90}})})
    assert response.status_code == 200, response.text
    updated = auth_client.get(f"/api/admin/nail-arts/{item['id']}").json()["item"]
    assert updated["image_path"] != paths[2]
    assert [photo["image_path"] for photo in updated["images"]][1:] == paths[:2]
    with Image.open(settings.upload_path / paths[0]) as original, Image.open(settings.upload_path / updated["image_path"]) as cropped:
        assert cropped.size == (original.height // 2, original.width // 2)
    assert not (settings.upload_path / paths[2]).exists()
    page = auth_client.get(f"/admin/nail-arts/{item['id']}/edit")
    assert "Make cover" in page.text
    assert "photo-editor.js" in page.text


def test_invalid_order_and_crop_leave_photos_unchanged(auth_client):
    cid = create_category(auth_client, "Invalid edits").json()["item"]["id"]
    item = create_nail(auth_client, "Unchanged", cid, image=make_png()).json()["item"]
    data = {"name": item["name"], "description": "Keep", "price": "100", "category_id": str(cid)}
    before = set(settings.upload_path.iterdir())
    for extra in (
        {"image_order": [item["image_path"], item["image_path"]]},
        {"image_order": ["someone-elses.png"]},
        {"photo_edits": "[]"},
        {"photo_edits": json.dumps({"someone-elses.png": {}})},
        {"photo_edits": json.dumps({item["image_path"]: {"x": 0, "y": 0, "width": 2, "height": 1}})},
    ):
        response = auth_client.put(f"/api/admin/nail-arts/{item['id']}", data={**data, **extra},
            files=[("images", ("new.png", make_png(), "image/png"))])
        assert response.status_code == 422, response.text
        assert set(settings.upload_path.iterdir()) == before
        assert auth_client.get(f"/api/admin/nail-arts/{item['id']}").json()["item"]["images"] == item["images"]
