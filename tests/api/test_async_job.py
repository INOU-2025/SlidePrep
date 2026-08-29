"""Real end-to-end asynchronous execution: POST /jobs dispatches through the
real celery apply_async() call in routes.py, the real task body runs (via
Celery's own eager-execution mode — task_always_eager, not a mock of the
task), and the result is read back for real through GET /jobs/{id} against
a real Redis-backed result store.

This is NOT a substitute for proving the out-of-process broker/worker
distribution works (a separate worker process really consuming from a real
queue) — see the coverage report in the implementation plan for that gap.
What this does prove: the real task body (worker/tasks.py) executes
correctly end to end — real stitching via ashlar, real DZI generation via
vips — and real Celery progress/result state is produced and readable.

To stay GPU/heavy-data-free, jobs are dispatched with clean_grid=false
(the passthrough pipeline skips binarization/grid detection/inpainting
entirely — no classifier, no LaMa) and 1-2 tiny synthetic tiles.

Requires vips (DZI generation) and a reachable Redis (result backend) —
both present in CI; skipped locally otherwise, matching test_dzi.py's
existing skip-if precedent.
"""

import os
import shutil

import numpy as np
import pytest
import tifffile

import api.routes as routes_module
from worker.celery_app import celery_app, REDIS_URL


def _redis_reachable() -> bool:
    try:
        import redis
        redis.from_url(REDIS_URL, socket_connect_timeout=1).ping()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not shutil.which("vips") or not _redis_reachable(),
    reason="requires vips (DZI generation) and a reachable Redis backend",
)


@pytest.fixture
def celery_eager():
    """Make apply_async() run the real task synchronously, in-process,
    through Celery's real task-binding machinery (self.update_state etc.
    all work correctly) — the real task body, not a mock of it.

    Deliberately does NOT set task_eager_propagates: that would make
    apply_async() itself raise on task failure, which doesn't match real
    (non-eager) dispatch semantics — production apply_async() never raises
    for a task-internal failure, it's always readable via AsyncResult
    afterward, and task_store_eager_result is what makes eager mode honor
    that same contract instead of just short-circuiting the caller.
    """
    original = dict(celery_app.conf)
    celery_app.conf.update(
        task_always_eager=True,
        task_store_eager_result=True,
    )
    try:
        yield
    finally:
        celery_app.conf.update(**original)


@pytest.fixture
def upload_dir(tmp_path, monkeypatch):
    """Overrides conftest.py's upload_dir: worker/tasks.py derives its DZI
    output directory as UPLOAD_DIR/../../results (a relative literal, not a
    configurable constant) — matching production's data/uploads + data/results
    sibling layout. A plain tmp_path/uploads has no such sibling, so vips
    would be asked to write into a directory that doesn't exist. Mirror the
    real topology instead of merely pointing UPLOAD_DIR anywhere convenient.
    """
    data_dir = tmp_path / "data"
    (data_dir / "uploads").mkdir(parents=True)
    (data_dir / "results").mkdir(parents=True)
    monkeypatch.setattr(routes_module, "UPLOAD_DIR", str(data_dir / "uploads"))
    return str(data_dir / "uploads")


def _write_tiles(dest_dir, n=2):
    # 300x300 — small enough to stay fast, but the stitched mosaic still
    # comfortably exceeds vips dzsave's default 254px tile size; anything
    # much smaller than that makes vips fail with "tile size out of range"
    # regardless of how correct the rest of the pipeline is.
    paths = []
    for series in range(n):
        img = np.full((300, 300), 80 + series * 60, dtype=np.uint8)
        p = os.path.join(dest_dir, f"TileScan_001_s{series:03d}_ch00.tif")
        tifffile.imwrite(p, img)
        paths.append(p)
    return paths


def test_async_job_runs_for_real_and_status_reports_success(client, upload_dir, celery_eager, tmp_path):
    stage_dir = tmp_path / "stage"
    stage_dir.mkdir()
    tile_paths = _write_tiles(stage_dir, n=2)

    files = [
        ("files", (os.path.basename(p), open(p, "rb").read(), "image/tiff"))
        for p in tile_paths
    ]
    resp = client.post(
        "/jobs",
        files=files,
        data={
            "pixel_size": "0.63",
            "clean_grid": "false",
            "grid_width": "1",
            "grid_height": "2",
        },
    )
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]

    status_resp = client.get(f"/jobs/{job_id}")
    assert status_resp.status_code == 200
    body = status_resp.json()
    assert body["status"] == "SUCCESS", body
    assert body["result_url"] is not None
    # tile_count here is the DZI pyramid's own output tile count (worker/tasks.py),
    # not the input tile count — just confirm the pyramid actually has content.
    assert body["tile_count"] > 0
    assert body["width"] is not None and body["height"] is not None

    # DZI output lands under UPLOAD_DIR/../../results — resolved relative to
    # our monkeypatched UPLOAD_DIR (tmp_path/data/uploads), i.e. tmp_path/data/results.
    results_dir = tmp_path / "data" / "results"
    assert (results_dir / f"{job_id}_panorama.dzi").exists()
    assert (results_dir / f"{job_id}_panorama_files").is_dir()


def test_async_job_failure_surfaces_via_status_endpoint(client, upload_dir, celery_eager):
    """A job with no images the worker recognizes (worker/tasks.py raises
    ValueError("No images found...")) must surface as a real FAILURE status
    through the real result backend — not raise back through POST /jobs
    itself, matching production's non-blocking dispatch contract."""
    resp = client.post(
        "/jobs",
        files=[("files", ("notes.txt", b"not an image", "text/plain"))],
        data={"pixel_size": "0.63", "clean_grid": "false"},
    )
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]

    status_resp = client.get(f"/jobs/{job_id}")
    assert status_resp.status_code == 200
    body = status_resp.json()
    assert body["status"] == "FAILURE"
    assert "No images found" in body["error"]
