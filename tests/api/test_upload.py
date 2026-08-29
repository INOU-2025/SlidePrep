"""Real upload-path tests: validation, sanitization, and limit enforcement
against the real POST /jobs code path, up to (not including) task dispatch
— see conftest.py's mock_dispatch for why dispatch itself is stubbed here.
"""

import os


def test_missing_files_rejected(client, upload_dir, mock_dispatch):
    resp = client.post("/jobs", data={"pixel_size": "0.63"})
    assert resp.status_code == 400
    mock_dispatch.assert_not_called()


def test_missing_pixel_size_rejected(client, upload_dir, mock_dispatch):
    resp = client.post(
        "/jobs",
        files=[("files", ("tile.tif", b"tiledata", "image/tiff"))],
        data={"grid_width": "1", "grid_height": "1"},
    )
    assert resp.status_code == 400
    assert "pixel_size" in resp.json()["detail"]
    mock_dispatch.assert_not_called()
    assert os.listdir(upload_dir) == []


def test_too_many_files_rejected(client, upload_dir, small_limits, mock_dispatch):
    files = [("files", (f"t{i}.tif", b"x", "image/tiff")) for i in range(10)]
    resp = client.post("/jobs", files=files, data={"pixel_size": "0.63"})
    assert resp.status_code == 400
    assert "Too many files" in resp.json()["detail"]
    mock_dispatch.assert_not_called()


def test_oversized_file_rejected(client, upload_dir, small_limits, mock_dispatch):
    big = b"x" * 2048  # exceeds small_limits' 1024-byte MAX_FILE_SIZE_BYTES
    resp = client.post(
        "/jobs",
        files=[("files", ("big.tif", big, "image/tiff"))],
        data={"pixel_size": "0.63"},
    )
    assert resp.status_code == 400
    mock_dispatch.assert_not_called()
    # job dir cleaned up on rejection, not left half-written
    assert os.listdir(upload_dir) == []


def test_successful_upload_sanitizes_traversal_filenames(client, upload_dir, mock_dispatch):
    resp = client.post(
        "/jobs",
        files=[("files", ("../../evil.tif", b"tiledata", "image/tiff"))],
        data={"pixel_size": "0.63"},
    )
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]
    job_dir = os.path.join(upload_dir, job_id)
    assert os.listdir(job_dir) == ["evil.tif"]
    mock_dispatch.assert_called_once()


def test_successful_upload_dispatches_with_overrides(client, upload_dir, mock_dispatch):
    resp = client.post(
        "/jobs",
        files=[("files", ("tile.tif", b"tiledata", "image/tiff"))],
        data={"pixel_size": "0.63", "grid_width": "2", "grid_height": "3", "overlap": "0.15"},
    )
    assert resp.status_code == 200
    mock_dispatch.assert_called_once()
    _, kwargs = mock_dispatch.call_args
    stitching_overrides = kwargs["args"][5]
    assert stitching_overrides == {"width": 2, "height": 3, "overlap": 0.15, "pixel_size": 0.63}
