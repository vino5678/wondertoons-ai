import re

from app.core.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient

from tests.conftest import make_project, run_story

TAMIL = re.compile("[\u0b80-\u0bff]")


# ---- health ----
def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and body["database"] == "ok"
    assert body["network_features_enabled"] is False
    assert isinstance(body["ffmpeg_available"], bool)
    assert isinstance(body["ffprobe_available"], bool)
    assert "api_key" not in r.text.lower() and body["external_llm_configured"] is False


def test_cors_allows_vite_frontend_origin(client):
    response = client.options(
        "/projects",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"


def test_openapi_docs_enabled(client):
    assert client.get("/docs").status_code == 200
    paths = client.get("/openapi.json").json()["paths"]
    for p in ("/health", "/projects", "/projects/{project_id}/story", "/projects/{project_id}/exports",
              "/characters", "/jobs/{job_id}"):
        assert p in paths


# ---- projects ----
def test_project_crud_and_invalid_inputs(client):
    p = make_project(client)
    assert client.get(f"/projects/{p['id']}").json()["title"] == "Rainbow"
    assert client.patch(f"/projects/{p['id']}", json={"title": "New"}).json()["title"] == "New"
    assert len(client.get("/projects").json()) == 1
    assert client.post("/projects", json={"title": ""}).status_code == 422
    assert client.post("/projects", json={"title": "   "}).status_code == 422
    assert client.get("/projects/prj_missing").status_code == 404
    assert client.get("/projects/prj_missing").json()["error"]["code"] == "not_found"
    assert client.delete(f"/projects/{p['id']}").status_code == 204
    assert client.get(f"/projects/{p['id']}").status_code == 404


def test_provider_settings_reject_secrets(client):
    r = client.post("/projects", json={"title": "x", "provider_settings": {"video": {"api_key": "abc"}}})
    assert r.status_code == 422


def test_project_persists_across_restart(settings):
    with TestClient(create_app(settings)) as c1:
        pid = make_project(c1)["id"]
    with TestClient(create_app(settings)) as c2:
        assert c2.get(f"/projects/{pid}").status_code == 200


# ---- story, scenes, jobs ----
def test_story_generation_english(client):
    pid = make_project(client)["id"]
    job = run_story(client, pid, duration_seconds=90)
    assert job["status"] == "completed" and job["progress"] == 100 and job["progress_kind"] == "stage_based"
    assert client.get(f"/jobs/{job['id']}").json()["status"] == "completed"
    story = client.get(f"/projects/{pid}/story").json()
    assert story["output_status"] == "mock" and story["provider"] == "mock"
    scenes = story["scenes"]
    assert sum(s["estimated_duration_seconds"] for s in scenes) == 90
    assert len({s["scene_id"] for s in scenes}) == len(scenes)
    assert scenes[0]["previous_scene_id"] is None and scenes[-1]["next_scene_id"] is None
    assert scenes[0]["next_scene_id"] == scenes[1]["scene_id"]
    assert client.get(f"/projects/{pid}/scenes").json() == scenes
    assert client.get(f"/projects/{pid}").json()["has_story"] is True


def test_story_tamil_with_english_subtitles(client):
    pid = make_project(client)["id"]
    run_story(client, pid, target_language="ta", subtitle_languages=["en"])
    scene = client.get(f"/projects/{pid}/scenes").json()[0]
    assert TAMIL.search(scene["narration"]) and set(scene["caption_text"]) == {"ta", "en"}


def test_story_is_deterministic_apart_from_ids(client):
    a, b = make_project(client)["id"], make_project(client)["id"]
    run_story(client, a)
    run_story(client, b)
    strip = lambda sc: [{k: v for k, v in s.items() if not k.endswith("scene_id")} for s in sc]
    assert strip(client.get(f"/projects/{a}/scenes").json()) == strip(client.get(f"/projects/{b}/scenes").json())


def test_story_invalid_inputs(client):
    pid = make_project(client)["id"]
    for bad in ({"prompt": "x"}, {"prompt": "ok prompt", "duration_seconds": 5},
                {"prompt": "ok prompt", "duration_seconds": 99999}, {"prompt": "ok prompt", "target_language": "??"},
                {"prompt": "ok prompt", "age_group": "40-50"}):
        assert client.post(f"/projects/{pid}/story", json=bad).status_code == 422, bad
    r = client.post(f"/projects/{pid}/story", json={"prompt": "ok prompt", "target_language": "fr"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "unsupported_language"
    assert client.post("/projects/prj_missing/story", json={"prompt": "ok prompt"}).status_code == 404
    assert client.get(f"/projects/{pid}/story").status_code == 404  # nothing generated yet


def test_external_provider_is_disabled_without_network_consent(client):
    pid = make_project(client, provider_settings={"story_provider": "external_llm"})["id"]
    job = run_story(client, pid)
    assert job["status"] == "failed"
    assert "network-dependent providers are disabled" in job["error_message"]
    assert client.get(f"/projects/{pid}").json()["has_story"] is False  # no fabricated result


def test_unknown_provider_fails_job(client):
    pid = make_project(client, provider_settings={"story_provider": "nope"})["id"]
    job = run_story(client, pid)
    assert job["status"] == "failed" and "Unknown story provider" in job["error_message"]


def test_unknown_character_fails_job(client):
    pid = make_project(client)["id"]
    job = run_story(client, pid, character_ids=["chr_missing"])
    assert job["status"] == "failed" and "chr_missing" in job["error_message"]


def test_cannot_cancel_finished_job_and_unknown_job_404(client):
    pid = make_project(client)["id"]
    job = run_story(client, pid)
    assert client.post(f"/jobs/{job['id']}/cancel").status_code == 409
    assert client.get("/jobs/job_missing").status_code == 404


def test_cancel_queued_job(settings):
    # Non-inline runner never starts the job if we cancel first: simulate with a queued row.
    from app.services import jobs as job_svc
    with TestClient(create_app(settings)) as c:
        pid = make_project(c)["id"]
        db = c.app.state.session_factory()
        try:
            job = job_svc.create_job(db, pid, "story_generation")
            r = c.post(f"/jobs/{job.id}/cancel")
            assert r.status_code == 200 and r.json()["status"] == "cancelled"
            assert job_svc.advance(db, job.id, status="running") is False  # worker would stop
        finally:
            db.close()


def test_scene_edit_and_rescale(client):
    pid = make_project(client)["id"]
    run_story(client, pid, duration_seconds=60)
    scenes = client.get(f"/projects/{pid}/scenes").json()
    bad = [dict(s) for s in scenes]
    bad[0]["estimated_duration_seconds"] += 30
    assert client.put(f"/projects/{pid}/scenes", json={"scenes": bad}).status_code == 422
    ok = [dict(s) for s in scenes]
    ok[0]["title"] = "Edited"
    assert client.put(f"/projects/{pid}/scenes", json={"scenes": ok}).status_code == 200
    assert client.get(f"/projects/{pid}/scenes").json()[0]["title"] == "Edited"
    r = client.post(f"/projects/{pid}/scenes/plan", json={"total_duration_seconds": 120})
    assert r.status_code == 200 and sum(s["estimated_duration_seconds"] for s in r.json()) == 120
    assert client.get(f"/projects/{pid}/story").json()["total_duration_seconds"] == 120


# ---- characters ----
CHAR = {"name": "Fifi Fox", "appearance": "orange fox with a blue scarf", "personality": "curious",
        "voice_preferences": {"language": "ta", "style": "cheerful"},
        "reference_image_paths": ["fifi/front.png"]}


def test_character_crud(client):
    c = client.post("/characters", json=CHAR)
    assert c.status_code == 201
    cid = c.json()["id"]
    assert client.get(f"/characters/{cid}").json()["voice_preferences"]["language"] == "ta"
    r = client.patch(f"/characters/{cid}", json={"personality": "brave"})
    assert r.json()["personality"] == "brave" and r.json()["name"] == "Fifi Fox"
    assert len(client.get("/characters").json()) == 1
    assert client.delete(f"/characters/{cid}").status_code == 204
    assert client.get(f"/characters/{cid}").status_code == 404


def test_character_invalid_inputs(client):
    for bad in ({**CHAR, "name": ""}, {**CHAR, "appearance": " "},
                {**CHAR, "reference_image_paths": ["../../secret.png"]},
                {**CHAR, "reference_image_paths": ["C:\\x.png"]},
                {**CHAR, "reference_image_paths": ["run.py"]},
                {**CHAR, "voice_preferences": {"language": "??"}}):
        assert client.post("/characters", json=bad).status_code == 422, bad


def test_character_selection_history_and_story_use(client):
    cid = client.post("/characters", json=CHAR).json()["id"]
    pid = make_project(client)["id"]
    assert client.put(f"/projects/{pid}/characters/{cid}?role=hero").status_code == 204
    assert client.put(f"/projects/{pid}/characters/{cid}?role=hero").status_code == 204  # idempotent
    assert client.get(f"/projects/{pid}").json()["selected_character_ids"] == [cid]
    assert client.get(f"/projects/{pid}/characters").json()[0]["id"] == cid
    assert client.get(f"/characters/{cid}/appearances").json()[0]["project_id"] == pid
    run_story(client, pid, character_ids=[cid])
    story = client.get(f"/projects/{pid}/story").json()
    assert story["characters_used"][0]["id"] == cid
    assert "Fifi Fox" in story["scenes"][0]["visual_prompt"]
    assert client.delete(f"/characters/{cid}").status_code == 409
    assert client.delete(f"/characters/{cid}?force=true").status_code == 204
    assert client.delete(f"/projects/{pid}/characters/{cid}").status_code == 204


def test_similarity_check_is_honest(client):
    client.post("/characters", json=CHAR)
    r = client.post("/characters/similarity-check", json={"name": "Fifi Fox", "appearance": CHAR["appearance"]}).json()
    assert r["verdict"] == "possible_duplicate" and r["guarantees_visual_uniqueness"] is False
    r2 = client.post("/characters/similarity-check", json={"name": "Zed", "appearance": "green robot"}).json()
    assert r2["verdict"] == "no_text_match" and "does not prove" in r2["note"]


def test_character_generation_request_is_mock_and_unsaved(client):
    r = client.post("/characters/generation-requests", json={"brief": "a shy forest animal"})
    assert r.status_code == 200 and r.json()["output_status"] == "mock"
    assert client.get("/characters").json() == []


# ---- project deletion removes dependent rows/files ----
def test_delete_project_removes_jobs_and_folder(client, settings):
    pid = make_project(client)["id"]
    job = run_story(client, pid)
    assert (settings.projects_dir / pid).exists()
    client.delete(f"/projects/{pid}")
    assert not (settings.projects_dir / pid).exists()
    assert client.get(f"/jobs/{job['id']}").status_code == 404
