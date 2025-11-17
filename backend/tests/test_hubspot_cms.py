from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.routers import hubspot as hubspot_router

client = TestClient(app)


def test_cms_test_blog_post_invokes_hubspot(monkeypatch):
  captured = {}

  def fake_create_blog_post(user_id, payload):
    captured["user_id"] = user_id
    captured["payload"] = payload
    return {"id": "123", "name": payload["name"]}

  monkeypatch.setattr(hubspot_router.hubspot_client, "create_blog_post", fake_create_blog_post)

  response = client.post("/api/hubspot/cms/test-blog-post", json={"user_id": "user_123"})
  assert response.status_code == 200
  body = response.json()
  assert body["status"] == "success"
  assert body["hubspot_response"]["id"] == "123"
  assert captured["user_id"] == "user_123"
  assert captured["payload"] == hubspot_router.CMS_BLOG_POST_SAMPLE


def test_cms_test_blog_post_propagates_errors(monkeypatch):
  def fake_create_blog_post(user_id, payload):
    raise HTTPException(status_code=401, detail="Not connected")

  monkeypatch.setattr(hubspot_router.hubspot_client, "create_blog_post", fake_create_blog_post)

  response = client.post("/api/hubspot/cms/test-blog-post", json={"user_id": "user_456"})
  assert response.status_code == 401
  assert response.json()["detail"] == "Not connected"


def test_blog_authors_endpoint(monkeypatch):
  expected = {"results": [{"id": 1, "name": "Author"}]}

  def fake_list_blog_authors(user_id):
    assert user_id == "user_abc"
    return expected

  monkeypatch.setattr(hubspot_router.hubspot_client, "list_blog_authors", fake_list_blog_authors)

  response = client.post("/api/hubspot/blog-authors", json={"user_id": "user_abc"})
  assert response.status_code == 200
  assert response.json() == expected


def test_blog_authors_endpoint_propagates_errors(monkeypatch):
  def fake_list_blog_authors(user_id):
    raise HTTPException(status_code=403, detail="Forbidden")

  monkeypatch.setattr(hubspot_router.hubspot_client, "list_blog_authors", fake_list_blog_authors)

  response = client.post("/api/hubspot/blog-authors", json={"user_id": "user_xyz"})
  assert response.status_code == 403
  assert response.json()["detail"] == "Forbidden"


def test_schedule_blog_post(monkeypatch):
  expected = {"status": "scheduled"}

  def fake_schedule_blog_post(user_id, post_id, publish_date):
    assert user_id == "user_abc"
    assert post_id == "123"
    assert publish_date == "2025-09-01T12:00:00Z"
    return expected

  monkeypatch.setattr(hubspot_router.hubspot_client, "schedule_blog_post", fake_schedule_blog_post)

  response = client.post(
    "/api/hubspot/blogs/posts/schedule",
    json={"user_id": "user_abc", "post_id": "123", "publish_date": "2025-09-01T12:00:00Z"},
  )
  assert response.status_code == 200
  assert response.json() == expected


def test_schedule_blog_post_propagates_errors(monkeypatch):
  def fake_schedule_blog_post(user_id, post_id, publish_date):
    raise HTTPException(status_code=422, detail="Invalid date")

  monkeypatch.setattr(hubspot_router.hubspot_client, "schedule_blog_post", fake_schedule_blog_post)

  response = client.post(
    "/api/hubspot/blogs/posts/schedule",
    json={"user_id": "user_abc", "post_id": "bad", "publish_date": "oops"},
  )
  assert response.status_code == 422
  assert response.json()["detail"] == "Invalid date"


def test_list_blogs(monkeypatch):
  expected = {"results": [{"id": "1"}]}

  def fake_list_blogs(user_id):
    assert user_id == "user_blog"
    return expected

  monkeypatch.setattr(hubspot_router.hubspot_client, "list_blogs", fake_list_blogs)

  response = client.post("/api/hubspot/blogs", json={"user_id": "user_blog"})
  assert response.status_code == 200
  assert response.json() == expected


def test_list_blogs_propagates_errors(monkeypatch):
  def fake_list_blogs(user_id):
    raise HTTPException(status_code=500, detail="HubSpot failure")

  monkeypatch.setattr(hubspot_router.hubspot_client, "list_blogs", fake_list_blogs)

  response = client.post("/api/hubspot/blogs", json={"user_id": "user_blog"})
  assert response.status_code == 500
  assert response.json()["detail"] == "HubSpot failure"


def test_tests_catalog_endpoint():
  response = client.get("/api/hubspot/tests/catalog")
  assert response.status_code == 200
  payload = response.json()
  assert "results" in payload


def test_tests_run(monkeypatch):
  entry = {"key": "sample-test", "method": "GET", "path": "/crm/v3/objects/contacts"}

  monkeypatch.setattr(hubspot_router, "HUBSPOT_TEST_MAP", {"sample-test": entry})
  monkeypatch.setattr(hubspot_router, "HUBSPOT_TESTS", [entry])
  monkeypatch.setattr(hubspot_router, "HUBSPOT_TEST_SAMPLES", {"sample-test": {"path": "/crm/v3/objects/contacts"}})

  def fake_execute_raw(user_id, method, path, **kwargs):
    assert user_id == "user123"
    assert method == "GET"
    assert path == entry["path"]
    return {"ok": True}

  monkeypatch.setattr(hubspot_router.hubspot_client, "execute_raw", fake_execute_raw)

  response = client.post("/api/hubspot/tests/run", json={"user_id": "user123", "key": "sample-test"})
  assert response.status_code == 200
  assert response.json()["result"] == {"ok": True}


def test_tests_run_invalid_key():
  response = client.post("/api/hubspot/tests/run", json={"user_id": "user123", "key": "missing"})
  assert response.status_code == 404
