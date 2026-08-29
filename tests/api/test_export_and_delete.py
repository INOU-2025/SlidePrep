"""Real filesystem-only tests for export/export-mask/delete — none of these
endpoints touch Celery, so no dispatch stubbing/eager mode is needed here.
"""

import os
import shutil
import uuid

import pytest


def test_export_404_before_file_exists(client, upload_dir):
    resp = client.get("/jobs/nonexistent-job/export")
    assert resp.status_code == 404


def test_export_mask_404_before_file_exists(client, upload_dir):
    resp = client.get("/jobs/nonexistent-job/export/mask")
    assert resp.status_code == 404


def test_export_serves_real_file(client, upload_dir):
    job_id = "job-export-test"
    processed_dir = os.path.join(upload_dir, job_id, "processed")
    os.makedirs(processed_dir, exist_ok=True)
    ome_path = os.path.join(processed_dir, "stitched_slide.ome.tif")
    with open(ome_path, "wb") as f:
        f.write(b"fake ome tiff bytes")

    resp = client.get(f"/jobs/{job_id}/export")
    assert resp.status_code == 200
    assert resp.content == b"fake ome tiff bytes"
    assert resp.headers["content-type"] == "image/tiff"


def test_export_mask_serves_real_file(client, upload_dir):
    job_id = "job-mask-test"
    processed_dir = os.path.join(upload_dir, job_id, "processed")
    os.makedirs(processed_dir, exist_ok=True)
    open(os.path.join(processed_dir, "stitched_slide.ome.tif"), "wb").close()
    mask_path = os.path.join(processed_dir, "stitched_slide_inpaint_mask.tif")
    with open(mask_path, "wb") as f:
        f.write(b"fake mask bytes")

    resp = client.get(f"/jobs/{job_id}/export/mask")
    assert resp.status_code == 200
    assert resp.content == b"fake mask bytes"


@pytest.fixture
def real_results_dir():
    """delete_job touches the real data/results — a hardcoded literal in
    routes.py, not a configurable constant like UPLOAD_DIR. Rather than
    refactor production code purely to ease testing, use a random per-test
    job_id and clean up afterward regardless of pass/fail."""
    job_id = f"test-{uuid.uuid4().hex[:8]}"
    yield job_id
    for p in (
        os.path.join("data", "results", f"{job_id}_panorama.dzi"),
        os.path.join("data", "results", f"{job_id}_panorama_files"),
    ):
        if os.path.isdir(p):
            shutil.rmtree(p, ignore_errors=True)
        elif os.path.exists(p):
            os.remove(p)


def test_delete_removes_upload_dir_and_results(client, upload_dir, real_results_dir):
    job_id = real_results_dir
    job_dir = os.path.join(upload_dir, job_id)
    os.makedirs(job_dir, exist_ok=True)
    with open(os.path.join(job_dir, "tile.tif"), "wb") as f:
        f.write(b"x")

    results_dir = os.path.join("data", "results")
    os.makedirs(results_dir, exist_ok=True)
    dzi_path = os.path.join(results_dir, f"{job_id}_panorama.dzi")
    dzi_files_dir = os.path.join(results_dir, f"{job_id}_panorama_files")
    with open(dzi_path, "wb") as f:
        f.write(b"<xml/>")
    os.makedirs(dzi_files_dir, exist_ok=True)

    resp = client.delete(f"/jobs/{job_id}")
    assert resp.status_code == 200
    assert not os.path.exists(job_dir)
    assert not os.path.exists(dzi_path)
    assert not os.path.exists(dzi_files_dir)


def test_delete_nonexistent_job_is_a_no_op(client, upload_dir):
    resp = client.delete("/jobs/never-existed")
    assert resp.status_code == 200
