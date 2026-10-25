import shutil
import unittest

from app.services import assembly
from tests.conftest import make_project, run_story


def _need_ffmpeg():
    if not (assembly.find_ffmpeg() and assembly.find_ffprobe()):
        raise unittest.SkipTest("ffmpeg/ffprobe not installed")


def _story(client, **kw):
    pid = make_project(client)["id"]
    run_story(client, pid, duration_seconds=20, **kw)
    return pid


def test_export_requires_story(client):
    pid = make_project(client)["id"]
    r = client.post(f"/projects/{pid}/exports", json={})
    assert r.status_code == 409 and r.json()["error"]["code"] == "conflict"
    assert client.post("/projects/prj_missing/exports", json={}).status_code == 404


def test_export_rejects_bad_options(client):
    pid = _story(client)
    for bad in ({"aspect_ratio": "4:3"}, {"resolution": "4k"}, {"caption_languages": ["??"]},
                {"renderer": "remote_video_api"}, {"title": "   "}):
        assert client.post(f"/projects/{pid}/exports", json=bad).status_code == 422, bad
    r = client.post(f"/projects/{pid}/exports", json={"caption_languages": ["ta"]})  # story has English only
    assert r.status_code == 422 and "ta" in r.json()["error"]["message"]


def test_export_without_ffmpeg_is_a_clear_error(client, monkeypatch):
    pid = _story(client)
    monkeypatch.setattr(assembly, "find_ffmpeg", lambda: None)
    r = client.post(f"/projects/{pid}/exports", json={})
    assert r.status_code == 503 and r.json()["error"]["code"] == "ffmpeg_not_found"


def test_full_export_and_download(client, settings):
    _need_ffmpeg()
    pid = _story(client, target_language="ta", subtitle_languages=["en"])
    job = client.post(f"/projects/{pid}/exports", json={"renderer": "storyboard_preview",
                                                        "resolution": "480p", "aspect_ratio": "1:1"}).json()
    assert job["status"] == "completed", job
    assert job["progress"] == 100 and job["kind"] == "export" and job["progress_kind"] == "stage_based"
    exports = client.get(f"/projects/{pid}/exports").json()
    assert len(exports) == 1
    manifest = exports[0]["manifest"]
    assert manifest["is_ai_generated_video"] is False and manifest["kind"] == "storyboard_preview"
    assert (manifest["width"], manifest["height"]) == (480, 480)
    assert abs(manifest["measured_duration_seconds"] - 20) <= 1
    names = {f["name"] for f in exports[0]["files"]}
    assert {"video.mp4", "captions_ta.srt", "captions_en.vtt", "manifest.json"} <= names
    video = client.get(exports[0]["files"][0]["url"] if exports[0]["files"][0]["kind"] == "video"
                       else f"/projects/{pid}/exports/{job['id']}/files/video.mp4")
    assert video.status_code == 200 and video.headers["content-type"] == "video/mp4" and len(video.content) > 1000
    srt = client.get(f"/projects/{pid}/exports/{job['id']}/files/captions_ta.srt?download=1")
    assert srt.status_code == 200 and "attachment" in srt.headers["content-disposition"]
    assert client.get(f"/projects/{pid}/exports/{job['id']}/files/..%2Fsecret").status_code == 404
    assert client.get(f"/projects/{pid}/exports/{job['id']}/files/not_listed.mp4").status_code == 404


def test_default_procedural_export_creates_downloadable_video(client):
    _need_ffmpeg()
    pid = _story(client)
    job = client.post(f"/projects/{pid}/exports", json={"resolution": "480p"}).json()
    assert job["status"] == "completed", job
    exports = client.get(f"/projects/{pid}/exports").json()
    assert len(exports) == 1
    manifest = exports[0]["manifest"]
    assert manifest["kind"] == "procedural_2d_animation"
    assert manifest["is_ai_generated_video"] is False
    assert manifest["video_codec"] == "h264" and manifest["audio_codec"] == "aac"
    assert manifest["measured_duration_seconds"] > 0
    video = next(file for file in exports[0]["files"] if file["kind"] == "video")
    response = client.get(video["url"])
    assert response.status_code == 200 and len(response.content) > 1000


def test_unavailable_requested_narration_warns_and_video_continues(client, monkeypatch):
    from app.services import local_audio

    _need_ffmpeg()
    pid = _story(client, target_language="ta")

    def unavailable(*_args):
        raise local_audio.AudioGenerationError("No installed Windows speech voice matches language 'ta'.")

    monkeypatch.setattr(local_audio, "synthesize_windows_speech", unavailable)
    job = client.post(f"/projects/{pid}/exports", json={"resolution": "480p", "narration": True}).json()
    assert job["status"] == "completed", job
    export = client.get(f"/projects/{pid}/exports").json()[0]
    assert export["manifest"]["audio"] == "silent_placeholder"
    assert any("Narration was requested but is unavailable" in warning
               for warning in export["manifest"]["warnings"])


def test_default_export_request_is_the_procedural_renderer():
    from app.schemas.export import ExportRequest

    assert ExportRequest().renderer.value == "procedural_2d"
    assert ExportRequest().narration is False and ExportRequest().background_music is False


def test_failed_export_leaves_no_files_and_downloads_404(client, settings, monkeypatch):
    _need_ffmpeg()
    pid = _story(client)

    def boom(**_kw):
        raise assembly.AssemblyError("simulated FFmpeg failure")
    monkeypatch.setattr(assembly, "assemble", boom)
    job = client.post(f"/projects/{pid}/exports", json={"resolution": "480p"}).json()
    assert job["status"] == "failed" and "simulated FFmpeg failure" in job["error_message"]
    assert client.get(f"/projects/{pid}/exports").json() == []
    assert not (settings.projects_dir / pid / "exports" / job["id"]).exists()
    assert client.get(f"/projects/{pid}/exports/{job['id']}/files/video.mp4").status_code == 404


def test_interrupted_jobs_are_failed_on_startup(settings):
    from fastapi.testclient import TestClient
    from app.main import create_app
    from app.services import jobs as job_svc
    with TestClient(create_app(settings)) as c:
        pid = make_project(c)["id"]
        db = c.app.state.session_factory()
        try:
            job_id = job_svc.create_job(db, pid, "export").id
        finally:
            db.close()
    with TestClient(create_app(settings)) as c2:
        j = c2.get(f"/jobs/{job_id}").json()
        assert j["status"] == "failed" and "restarted" in j["error_message"]
