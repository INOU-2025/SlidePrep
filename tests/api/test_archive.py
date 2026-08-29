"""Real archive-handling tests: zip extraction, path-traversal rejection,
and size-limit enforcement against the real POST /jobs zip-handling code
path (_validate_zip_members / extractall in api/routes.py).
"""

import io
import os
import zipfile


def _make_zip(entries: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in entries.items():
            zf.writestr(name, content)
    return buf.getvalue()


def test_valid_zip_extracted_and_flattened(client, upload_dir, mock_dispatch):
    zip_bytes = _make_zip({
        "tiles/TileScan_001_s000_ch00.tif": b"a" * 100,
        "tiles/TileScan_001_s001_ch00.tif": b"b" * 100,
        "__MACOSX/._junk": b"ignoreme",
    })
    resp = client.post(
        "/jobs",
        files=[("files", ("tiles.zip", zip_bytes, "application/zip"))],
        data={"pixel_size": "0.63"},
    )
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]
    job_dir = os.path.join(upload_dir, job_id)
    written = set(os.listdir(job_dir))
    assert written == {"TileScan_001_s000_ch00.tif", "TileScan_001_s001_ch00.tif"}
    mock_dispatch.assert_called_once()


def test_zip_path_traversal_rejected(client, upload_dir, mock_dispatch):
    zip_bytes = _make_zip({"../../evil.tif": b"x" * 10})
    resp = client.post(
        "/jobs",
        files=[("files", ("evil.zip", zip_bytes, "application/zip"))],
        data={"pixel_size": "0.63"},
    )
    assert resp.status_code == 400
    assert "escapes" in resp.json()["detail"]
    mock_dispatch.assert_not_called()
    # rejected before extraction and the job dir is cleaned up, not left
    # half-written with an escaped member on disk somewhere
    assert os.listdir(upload_dir) == []


def test_zip_member_exceeding_size_limit_rejected(client, upload_dir, small_limits, mock_dispatch):
    zip_bytes = _make_zip({"tile.tif": b"x" * 2048})  # exceeds small_limits' 1024
    resp = client.post(
        "/jobs",
        files=[("files", ("big.zip", zip_bytes, "application/zip"))],
        data={"pixel_size": "0.63"},
    )
    assert resp.status_code == 400
    mock_dispatch.assert_not_called()


def test_zip_total_contents_exceeding_budget_rejected(client, upload_dir, small_limits, mock_dispatch):
    # small_limits: MAX_TOTAL_UPLOAD_BYTES=4096; 5 members * 900B = 4500 > 4096
    zip_bytes = _make_zip({f"t{i}.tif": b"x" * 900 for i in range(5)})
    resp = client.post(
        "/jobs",
        files=[("files", ("many.zip", zip_bytes, "application/zip"))],
        data={"pixel_size": "0.63"},
    )
    assert resp.status_code == 400
    mock_dispatch.assert_not_called()


def test_bad_zip_file_ignored_not_crashed(client, upload_dir, mock_dispatch):
    """A .zip-named file that isn't actually a valid zip is swallowed by the
    existing BadZipFile except-pass — this test just confirms that doesn't
    crash the request, matching current (documented) behavior rather than
    asserting a stricter contract this change isn't meant to introduce."""
    resp = client.post(
        "/jobs",
        files=[("files", ("notreallyazip.zip", b"not a zip file", "application/zip"))],
        data={"pixel_size": "0.63"},
    )
    assert resp.status_code == 200
    mock_dispatch.assert_called_once()
