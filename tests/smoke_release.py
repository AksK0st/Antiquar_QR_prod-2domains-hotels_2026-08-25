#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import secrets
import sys
import urllib.error
import urllib.request
from http.cookiejar import CookieJar

BASE = os.environ.get("SMOKE_BASE_URL", "http://localhost:8080").rstrip("/")
ADMIN_USER = os.environ.get("SMOKE_ADMIN_USER", "ci-admin")
ADMIN_PASSWORD = os.environ.get("SMOKE_ADMIN_PASSWORD", "CI-password-123456")
PRIMARY_HOST = os.environ.get("SMOKE_PRIMARY_HOST", "gallery.local")
SECONDARY_HOST = os.environ.get("SMOKE_SECONDARY_HOST", "second.local")
PRIMARY_HOTEL = os.environ.get("SMOKE_PRIMARY_HOTEL", "Галерея")
SECONDARY_HOTEL = os.environ.get("SMOKE_SECONDARY_HOTEL", "Вторая")


def opener(with_cookies: bool = True):
    handlers = [urllib.request.HTTPCookieProcessor(CookieJar())] if with_cookies else []
    return urllib.request.build_opener(*handlers)


def request(
    client,
    method: str,
    path: str,
    *,
    json_body=None,
    data=None,
    headers=None,
    host: str | None = None,
):
    body = data
    request_headers = dict(headers or {})
    if host is not None:
        request_headers["Host"] = host
    if json_body is not None:
        body = json.dumps(json_body).encode()
        request_headers["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE + path, data=body, method=method, headers=request_headers)
    try:
        with client.open(req, timeout=15) as response:
            raw = response.read()
            return response.status, response.headers, raw
    except urllib.error.HTTPError as exc:
        return exc.code, exc.headers, exc.read()


def expect(status: int, actual: int, label: str) -> None:
    if actual != status:
        raise AssertionError(f"{label}: expected HTTP {status}, got {actual}")


def as_json(raw: bytes):
    return json.loads(raw.decode()) if raw else None


def multipart_file(filename: str, content_type: str, data: bytes):
    boundary = "----antiquar-" + secrets.token_hex(12)
    chunks = [
        f"--{boundary}\r\n".encode(),
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode(),
        f"Content-Type: {content_type}\r\n\r\n".encode(),
        data,
        f"\r\n--{boundary}--\r\n".encode(),
    ]
    return b"".join(chunks), {"Content-Type": f"multipart/form-data; boundary={boundary}"}


def main() -> None:
    public = opener()
    auth = opener()

    status, _, body = request(public, "GET", "/health/live")
    expect(200, status, "liveness")
    assert as_json(body)["status"] == "ok"

    status, _, body = request(public, "GET", "/health/ready")
    expect(200, status, "readiness")
    assert as_json(body)["status"] == "ready"

    status, _, body = request(public, "GET", "/")
    expect(200, status, "homepage")
    assert b'<div id="root"></div>' in body

    for host, expected_hotel in (
        (PRIMARY_HOST, PRIMARY_HOTEL),
        (SECONDARY_HOST, SECONDARY_HOTEL),
    ):
        status, _, body = request(public, "GET", "/api/public/site/", host=host)
        expect(200, status, f"site mapping for {host}")
        assert as_json(body)["hotel_name"] == expected_hotel

    status, _, body = request(public, "GET", "/api/public/items/", host=PRIMARY_HOST)
    expect(200, status, "public item list")
    seeded_items = as_json(body)
    assert seeded_items, "seed must provide at least one public item"
    seeded = seeded_items[0]

    status, _, body = request(public, "GET", f"/i/{seeded['public_id']}")
    expect(200, status, "direct immutable SPA route")
    assert b'<div id="root"></div>' in body

    status, _, body = request(public, "GET", f"/api/public/items/by-public-id/{seeded['public_id']}", host=PRIMARY_HOST)
    expect(200, status, "immutable public API lookup")
    assert as_json(body)["id"] == seeded["id"]

    # At least one seeded image must be publicly retrievable through a
    # content-versioned immutable URL used by the frontend.
    image_ok = False
    for item in seeded_items[:10]:
        primary = item.get("primary_image")
        if not primary:
            continue
        path = f"/api/public/images/by-id/{primary['id']}/v/{primary['content_version']}"
        status, headers, _ = request(public, "GET", path)
        if status == 200:
            assert "immutable" in headers.get("Cache-Control", "")
            assert headers.get("ETag"), "immutable image must expose ETag"
            image_ok = True
            break
    assert image_ok, "no seeded public image could be retrieved"

    unauth = opener(with_cookies=False)
    status, _, _ = request(unauth, "GET", "/api/admin/items/")
    expect(401, status, "admin API without session")

    # Expired session inserted by CI bootstrap must be rejected.
    status, _, _ = request(
        unauth,
        "GET",
        "/api/admin/auth/me",
        headers={"Cookie": "admin_session=ci-expired-session-token"},
    )
    expect(401, status, "expired admin session")

    status, _, _ = request(
        auth, "POST", "/api/admin/auth/login", json_body={"username": ADMIN_USER, "password": "wrong-password"}
    )
    expect(401, status, "wrong password")

    status, _, body = request(
        auth,
        "POST",
        "/api/admin/auth/login",
        json_body={"username": ADMIN_USER, "password": ADMIN_PASSWORD},
    )
    expect(200, status, "admin login")
    assert as_json(body)["authenticated"] is True

    status, headers, _ = request(auth, "GET", "/api/admin/auth/me")
    expect(200, status, "admin me")
    assert headers.get("Cache-Control") == "no-store"

    status, _, body = request(auth, "GET", "/api/admin/sites/")
    expect(200, status, "admin sites")
    configured_sites = as_json(body)["sites"]
    assert {site["hotel_name"] for site in configured_sites} == {PRIMARY_HOTEL, SECONDARY_HOTEL}

    suffix = secrets.token_hex(5)
    shared_collection_slug = f"ci-{suffix}"
    shared_item_slug = f"ci-item-{suffix}"

    collection_payload = {
        "hotel_name": PRIMARY_HOTEL,
        "slug": shared_collection_slug,
        "name": "CI Primary Collection",
        "description": "created by release smoke test",
        "location": None,
    }
    status, _, body = request(auth, "POST", "/api/admin/collections/", json_body=collection_payload)
    expect(201, status, "create primary collection")
    collection = as_json(body)

    secondary_collection_payload = dict(collection_payload)
    secondary_collection_payload.update({
        "hotel_name": SECONDARY_HOTEL,
        "name": "CI Secondary Collection",
    })
    status, _, body = request(
        auth, "POST", "/api/admin/collections/", json_body=secondary_collection_payload
    )
    expect(201, status, "same collection slug in secondary hotel")
    secondary_collection = as_json(body)

    item_payload = {
        "hotel_name": PRIMARY_HOTEL,
        "slug": shared_item_slug,
        "name": "CI Primary Item",
        "short_description": "smoke",
        "description": "release smoke item",
        "period_from": 1900,
        "period_to": 1901,
        "period_text": "1900–1901",
        "country": "Test",
        "creator": None,
        "material": None,
        "collection_id": collection["id"],
        "location": None,
        "attribution_notes": None,
        "sort_order": 999,
        "is_active": True,
    }
    status, _, body = request(auth, "POST", "/api/admin/items/", json_body=item_payload)
    expect(201, status, "create primary item")
    item = as_json(body)
    immutable_id = item["public_id"]
    original_version = item["version"]

    secondary_item_payload = dict(item_payload)
    secondary_item_payload.update({
        "hotel_name": SECONDARY_HOTEL,
        "name": "CI Secondary Item",
        "collection_id": secondary_collection["id"],
    })
    status, _, body = request(auth, "POST", "/api/admin/items/", json_body=secondary_item_payload)
    expect(201, status, "same item slug in secondary hotel")
    secondary_item = as_json(body)

    # The same slug resolves to different records by domain, and immutable IDs never cross domains.
    status, _, body = request(public, "GET", f"/api/public/items/{shared_item_slug}", host=PRIMARY_HOST)
    expect(200, status, "primary slug isolation")
    assert as_json(body)["id"] == item["id"]
    status, _, body = request(public, "GET", f"/api/public/items/{shared_item_slug}", host=SECONDARY_HOST)
    expect(200, status, "secondary slug isolation")
    assert as_json(body)["id"] == secondary_item["id"]

    status, _, _ = request(
        public, "GET", f"/api/public/items/by-public-id/{immutable_id}", host=PRIMARY_HOST
    )
    expect(200, status, "new item public lookup")
    status, _, _ = request(
        public, "GET", f"/api/public/items/by-public-id/{immutable_id}", host=SECONDARY_HOST
    )
    expect(404, status, "immutable ID blocked on other hotel domain")
    status, _, _ = request(
        public,
        "GET",
        f"/api/public/items/by-public-id/{secondary_item['public_id']}",
        host=PRIMARY_HOST,
    )
    expect(404, status, "secondary immutable ID blocked on primary domain")

    status, _, body = request(public, "GET", "/api/public/items/", host=PRIMARY_HOST)
    expect(200, status, "primary item list isolation")
    primary_ids = {row["id"] for row in as_json(body)}
    assert item["id"] in primary_ids and secondary_item["id"] not in primary_ids
    status, _, body = request(public, "GET", "/api/public/items/", host=SECONDARY_HOST)
    expect(200, status, "secondary item list isolation")
    secondary_ids = {row["id"] for row in as_json(body)}
    assert secondary_item["id"] in secondary_ids and item["id"] not in secondary_ids

    status, _, _ = request(
        public, "GET", f"/api/public/collections/{collection['id']}", host=SECONDARY_HOST
    )
    expect(404, status, "collection blocked on other hotel domain")

    invalid_cross_hotel = dict(secondary_item_payload)
    invalid_cross_hotel.update({
        "slug": f"ci-cross-{suffix}",
        "collection_id": collection["id"],
    })
    status, _, _ = request(auth, "POST", "/api/admin/items/", json_body=invalid_cross_hotel)
    expect(422, status, "cross-hotel collection assignment")

    updated_payload = dict(item_payload)
    updated_payload["slug"] = f"ci-renamed-{suffix}"
    updated_payload["expected_version"] = original_version
    status, _, body = request(auth, "PATCH", f"/api/admin/items/{item['id']}", json_body=updated_payload)
    expect(200, status, "update item")
    updated = as_json(body)
    assert updated["public_id"] == immutable_id
    assert updated["version"] == original_version + 1

    stale_payload = {"name": "stale write", "expected_version": original_version}
    status, _, _ = request(auth, "PATCH", f"/api/admin/items/{item['id']}", json_body=stale_payload)
    expect(409, status, "optimistic locking")

    # Minimal valid 1x1 transparent PNG.
    png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDAT\x08\xd7c\xf8\xcf\xc0\xf0\x1f\x00\x05\x00\x01\xff\x89\x99=\x1d\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    mp, hdr = multipart_file("one.png", "image/png", png)
    status, _, body = request(auth, "POST", f"/api/admin/items/{item['id']}/images/", data=mp, headers=hdr)
    expect(201, status, "upload first image")
    image1 = as_json(body)
    assert image1["is_primary"] is True

    mp, hdr = multipart_file("two.png", "image/png", png)
    status, _, body = request(auth, "POST", f"/api/admin/items/{item['id']}/images/", data=mp, headers=hdr)
    expect(201, status, "upload second image")
    image2 = as_json(body)
    assert image2["is_primary"] is False

    image2_path = f"/api/public/images/by-id/{image2['id']}/v/{image2['content_version']}"
    status, headers, _ = request(public, "GET", image2_path, host=PRIMARY_HOST)
    expect(200, status, "stable public image route")
    status, _, _ = request(public, "GET", image2_path, host=SECONDARY_HOST)
    expect(404, status, "public image blocked on other hotel domain")
    etag = headers.get("ETag")
    assert etag, "stable public image route must return ETag"
    status, _, _ = request(public, "GET", image2_path, headers={"If-None-Match": etag}, host=PRIMARY_HOST)
    expect(304, status, "public image conditional GET")
    status, _, _ = request(
        public,
        "GET",
        f"/api/public/images/by-id/{image2['id']}/v/{image2['content_version'] + 1}",
        host=PRIMARY_HOST,
    )
    expect(404, status, "nonexistent image content version")

    status, _, _ = request(auth, "PATCH", f"/api/admin/items/{item['id']}/images/{image2['id']}/primary")
    expect(200, status, "set primary image")
    status, _, body = request(auth, "GET", f"/api/admin/items/{item['id']}/images/")
    expect(200, status, "list images")
    assert sum(1 for image in as_json(body) if image["is_primary"]) == 1

    bad, bad_headers = multipart_file("bad.txt", "text/plain", b"bad")
    status, _, _ = request(auth, "POST", f"/api/admin/items/{item['id']}/images/", data=bad, headers=bad_headers)
    expect(415, status, "invalid image media type")

    huge, huge_headers = multipart_file("huge.png", "image/png", b"x" * 2048)
    status, _, _ = request(auth, "POST", f"/api/admin/items/{item['id']}/images/", data=huge, headers=huge_headers)
    expect(413, status, "oversized image")

    status, headers, body = request(auth, "GET", f"/api/admin/items/{item['id']}/qr")
    expect(200, status, "QR generation")
    assert headers.get_content_type() == "image/png" and body.startswith(b"\x89PNG")

    current_version = updated["version"]
    status, _, body = request(
        auth,
        "PATCH",
        f"/api/admin/items/{item['id']}",
        json_body={"is_active": False, "expected_version": current_version},
    )
    expect(200, status, "unpublish item")
    unpublished = as_json(body)

    status, _, _ = request(public, "GET", f"/api/public/items/by-public-id/{immutable_id}", host=PRIMARY_HOST)
    expect(410, status, "inactive public item")

    status, _, _ = request(
        auth,
        "DELETE",
        f"/api/admin/items/{item['id']}?confirm_public_id={immutable_id}",
    )
    expect(204, status, "delete item")
    status, _, _ = request(auth, "DELETE", f"/api/admin/collections/{collection['id']}")
    expect(204, status, "delete empty primary collection")

    status, _, body = request(
        auth,
        "PATCH",
        f"/api/admin/items/{secondary_item['id']}",
        json_body={"is_active": False, "expected_version": secondary_item["version"]},
    )
    expect(200, status, "unpublish secondary item")
    status, _, _ = request(
        auth,
        "DELETE",
        f"/api/admin/items/{secondary_item['id']}?confirm_public_id={secondary_item['public_id']}",
    )
    expect(204, status, "delete secondary item")
    status, _, _ = request(
        auth, "DELETE", f"/api/admin/collections/{secondary_collection['id']}"
    )
    expect(204, status, "delete empty secondary collection")

    status, _, _ = request(auth, "POST", "/api/admin/auth/logout")
    expect(204, status, "logout")
    status, _, _ = request(auth, "GET", "/api/admin/auth/me")
    expect(401, status, "session invalid after logout")

    # Rate limiter: consume the IP bucket only after all authenticated checks are finished.
    limiter = opener()
    codes = []
    for _ in range(6):
        code, _, _ = request(
            limiter,
            "POST",
            "/api/admin/auth/login",
            json_body={"username": "rate-limit-user", "password": "wrong-password"},
        )
        codes.append(code)
    assert 429 in codes, f"login limiter never returned 429: {codes}"

    print("release smoke: OK")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"release smoke: FAILED: {exc}", file=sys.stderr)
        raise
