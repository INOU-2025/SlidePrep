"""FastAPI routes for job submission, status polling, and file management."""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from typing import Any, List
import uuid
import os
import shutil
import zipfile
from .schemas import JobResponse, JobStatus
from worker.tasks import process_images_task
from celery.result import AsyncResult
from src.utils.stitching_utils import mosaic_mask_path

router = APIRouter()

UPLOAD_DIR = "data/uploads"
CONFIG_PATH = os.environ.get("SLIDEPREP_CONFIG", "config/production.json")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# NOT a security limit — a framework-parsing ceiling only. Starlette's default form
# parser caps a multipart request at 1000 files, which a multi-channel whole-slide
# tile set easily exceeds. FastAPI's `File(...)`/`Form(...)` injection calls
# `request.form()` with no way to override that limit, so the form is parsed
# manually here instead, with this raised so parsing itself doesn't reject a
# legitimate large upload before it's even been counted. Deliberately far above
# MAX_FILES_PER_JOB below (100_000 vs. 5000) — this constant must never be used as
# a rejection threshold; that's what MAX_FILES_PER_JOB is for, applied afterward,
# once `files` is a real, counted list (see create_job below).
MAX_UPLOAD_FILES = 100_000

# Configurable upload limits — env-var-with-default, matching this module's existing
# convention (CONFIG_PATH above). Sized from this pipeline's own real acquisition
# (686 tile positions x 2 channels = 1372 files): a few thousand files and a few tens
# of gigabytes per job comfortably bounds legitimate use while still being a real
# ceiling. Nothing in nginx or FastAPI enforces any of these on its own — see
# client/nginx.conf's client_max_body_size for the matching reverse-proxy-level cap.
MAX_FILE_SIZE_BYTES = int(os.environ.get("SLIDEPREP_MAX_FILE_SIZE_BYTES", str(500 * 1024 * 1024)))          # 500 MB per tile file
MAX_TOTAL_UPLOAD_BYTES = int(os.environ.get("SLIDEPREP_MAX_TOTAL_UPLOAD_BYTES", str(30 * 1024 * 1024 * 1024)))  # 30 GB per job
# THE actual security-motivated file-count quota (unlike MAX_UPLOAD_FILES above,
# which only lets Starlette parse a large request — it enforces nothing). Checked
# against the real file count, both up front (len(files)) and after zip extraction.
MAX_FILES_PER_JOB = int(os.environ.get("SLIDEPREP_MAX_FILES_PER_JOB", "5000"))
_COPY_CHUNK_BYTES = 1024 * 1024


def _sanitize_filename(filename: str) -> str:
    """Strips any directory-traversal capability from a client-supplied filename.

    Tile filenames carry real meaning for this pipeline — the worker derives
    each processed tile's output name from the uploaded filename's stem
    (worker/tasks.py), and Ashlar later parses each tile's row/column/channel
    back out of that same name via the configured stitching.pattern — so this
    preserves the client's filename rather than replacing it with a
    server-generated one outright. os.path.basename neutralizes '../'
    sequences and absolute-path prefixes (no separator can survive it); the
    server-generated job_id directory is what actually isolates each upload,
    this only prevents an individual filename from escaping it.
    """
    name = os.path.basename((filename or "").replace("\x00", "")).strip()
    if not name or name in (".", ".."):
        raise ValueError(f"Invalid or empty filename: {filename!r}")
    return name


def _copy_with_limit(fileobj, dst_path: str, max_bytes: int) -> int:
    """Streams fileobj to dst_path in chunks, aborting (without ever buffering
    the whole thing in memory or writing past the limit) once max_bytes is
    exceeded. Returns bytes written."""
    written = 0
    with open(dst_path, "wb") as buffer:
        while True:
            chunk = fileobj.read(_COPY_CHUNK_BYTES)
            if not chunk:
                break
            written += len(chunk)
            if written > max_bytes:
                raise ValueError(
                    f"{os.path.basename(dst_path)!r} exceeds the size limit of {max_bytes} bytes"
                )
            buffer.write(chunk)
    return written


def _validate_zip_members(
    zip_ref: zipfile.ZipFile, dest_dir: str, remaining_total_bytes: int, remaining_file_budget: int,
) -> tuple[int, int]:
    """Validates every member BEFORE any extraction happens — a partially
    extracted, mixed-trust archive is worse than rejecting it outright.

    Checks, per member: its resolved path stays within dest_dir (path
    traversal — an entry like '../../x' must not escape the job directory),
    and its declared uncompressed size respects MAX_FILE_SIZE_BYTES (using
    zip metadata, so this never has to decompress anything to reject an
    oversized entry — closes the "zip bomb" gap a whole-request size check
    alone would miss). MAX_FILE_SIZE_BYTES applies here, per extracted tile —
    not to the zip container itself, which legitimately bundles many tiles
    and is instead bounded only by the job's remaining total-size budget.

    Returns (total_declared_bytes, file_count) for the caller's running totals.
    """
    dest_root = os.path.realpath(dest_dir)
    total_declared = 0
    file_count = 0
    for member in zip_ref.infolist():
        if member.is_dir():
            continue
        member_path = os.path.realpath(os.path.join(dest_dir, member.filename))
        if member_path != dest_root and not member_path.startswith(dest_root + os.sep):
            raise ValueError(f"Zip entry escapes target directory: {member.filename!r}")
        if member.file_size > MAX_FILE_SIZE_BYTES:
            raise ValueError(
                f"Zip entry {member.filename!r} exceeds the per-file size limit of {MAX_FILE_SIZE_BYTES} bytes"
            )
        total_declared += member.file_size
        file_count += 1
    if total_declared > remaining_total_bytes:
        raise ValueError(f"Zip contents exceed the total upload size limit of {MAX_TOTAL_UPLOAD_BYTES} bytes per job")
    if file_count > remaining_file_budget:
        raise ValueError(f"Zip contents exceed the {MAX_FILES_PER_JOB}-file limit per job")
    return total_declared, file_count

@router.post("/jobs", response_model=JobResponse)
async def create_job(request: Request):
    form = await request.form(max_files=MAX_UPLOAD_FILES)
    files: List[Any] = form.getlist("files")
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")
    if len(files) > MAX_FILES_PER_JOB:
        raise HTTPException(
            status_code=400,
            detail=f"Too many files: {len(files)} exceeds the limit of {MAX_FILES_PER_JOB} per job",
        )

    clean_grid_bool = str(form.get("clean_grid", "true")).lower() == 'true'
    grid_width = form.get("grid_width")
    grid_height = form.get("grid_height")
    overlap = form.get("overlap")
    pixel_size = form.get("pixel_size")
    direction = form.get("direction")
    suffix_filter = form.get("suffix_filter")
    grid_angle = form.get("grid_angle")
    detection_threshold = form.get("detection_threshold")

    job_id = str(uuid.uuid4())
    job_dir = os.path.join(UPLOAD_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)

    try:
        remaining_total_bytes = MAX_TOTAL_UPLOAD_BYTES
        remaining_file_budget = MAX_FILES_PER_JOB

        for file in files:
            safe_name = _sanitize_filename(file.filename)
            file_path = os.path.join(job_dir, safe_name)
            is_zip = safe_name.lower().endswith('.zip')

            # A zip is a bundle of many tiles, not one — its own raw upload is
            # bounded only by the remaining total-size budget, not the tighter
            # per-tile MAX_FILE_SIZE_BYTES (which _validate_zip_members applies
            # to each of its members individually, before extraction).
            write_limit = remaining_total_bytes if is_zip else min(MAX_FILE_SIZE_BYTES, remaining_total_bytes)
            written = _copy_with_limit(file.file, file_path, write_limit)

            if is_zip:
                try:
                    with zipfile.ZipFile(file_path, 'r') as zip_ref:
                        declared_bytes, _declared_count = _validate_zip_members(
                            zip_ref, job_dir, remaining_total_bytes, remaining_file_budget
                        )
                        zip_ref.extractall(job_dir)
                    os.remove(file_path)

                    macosx_path = os.path.join(job_dir, "__MACOSX")
                    if os.path.exists(macosx_path):
                        shutil.rmtree(macosx_path)

                    extracted_count = 0
                    for root, dirs, files_in_dir in os.walk(job_dir):
                        if root == job_dir:
                            continue
                        for filename in files_in_dir:
                            src_path = os.path.join(root, filename)
                            dst_path = os.path.join(job_dir, filename)
                            if os.path.exists(dst_path):
                                base, ext = os.path.splitext(filename)
                                dst_path = os.path.join(job_dir, f"{base}_{uuid.uuid4().hex[:8]}{ext}")
                            shutil.move(src_path, dst_path)
                            extracted_count += 1

                    for root, dirs, files_in_dir in os.walk(job_dir, topdown=False):
                        if root == job_dir:
                            continue
                        if not os.listdir(root):
                            os.rmdir(root)

                    remaining_file_budget -= extracted_count
                    remaining_total_bytes -= declared_bytes
                except zipfile.BadZipFile:
                    pass
            else:
                remaining_total_bytes -= written
                remaining_file_budget -= 1
    except ValueError as e:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise HTTPException(status_code=400, detail=str(e))

    stitching_overrides = {}
    if grid_width:  stitching_overrides['width']      = int(grid_width)
    if grid_height: stitching_overrides['height']     = int(grid_height)
    if overlap:     stitching_overrides['overlap']    = float(overlap)
    if pixel_size:  stitching_overrides['pixel_size'] = float(pixel_size)
    if direction:   stitching_overrides['direction']  = direction

    general_overrides = {}
    if suffix_filter is not None:
        general_overrides['suffix_filter'] = suffix_filter

    grid_detection_overrides = {}
    if grid_angle:          grid_detection_overrides['angles']    = [float(grid_angle)]
    if detection_threshold: grid_detection_overrides['threshold'] = float(detection_threshold)

    task = process_images_task.apply_async(
        args=[job_id, job_dir, job_dir, CONFIG_PATH, clean_grid_bool,
              stitching_overrides, general_overrides, grid_detection_overrides],
        task_id=job_id
    )

    return JobResponse(job_id=job_id, status="QUEUED", message="Job submitted successfully")

@router.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    task_result = AsyncResult(job_id)

    status = task_result.status
    result_url = None
    error = None
    message = None
    progress = None
    thumbnail_url = None
    width = None
    height = None
    tile_count = None
    mask_available = None

    if status == 'SUCCESS':
        result = task_result.result
        if result:
            if 'result_path' in result:
                result_url = f"/results/{result['result_path']}"
            if 'thumbnail_path' in result:
                thumbnail_url = f"/results/{result['thumbnail_path']}"
            width = result.get('width')
            height = result.get('height')
            tile_count = result.get('tile_count')
            mask_available = result.get('mask_available')
    elif status == 'FAILURE':
        error = str(task_result.result)
    elif status == 'PROCESSING':
        info = task_result.info
        if isinstance(info, dict):
            message = info.get('status')
            progress = info.get('progress')

    return JobStatus(
        job_id=job_id, status=status, result_url=result_url, error=error,
        message=message, progress=progress, thumbnail_url=thumbnail_url,
        width=width, height=height, tile_count=tile_count,
        mask_available=mask_available,
    )

@router.get("/jobs/{job_id}/export")
async def export_job(job_id: str):
    ome_tiff_path = os.path.join(UPLOAD_DIR, job_id, "processed", "stitched_slide.ome.tif")
    if not os.path.exists(ome_tiff_path):
        raise HTTPException(status_code=404, detail="Export file not found — job may still be processing")
    return FileResponse(
        path=ome_tiff_path,
        media_type="image/tiff",
        filename=f"{job_id}_slide.ome.tif",
    )

@router.get("/jobs/{job_id}/export/mask")
async def export_job_mask(job_id: str):
    ome_tiff_path = os.path.join(UPLOAD_DIR, job_id, "processed", "stitched_slide.ome.tif")
    mask_path = mosaic_mask_path(ome_tiff_path)
    if not os.path.exists(mask_path):
        raise HTTPException(status_code=404, detail="Inpaint mask not found — job may not have run grid removal, or is still processing")
    return FileResponse(
        path=mask_path,
        media_type="image/tiff",
        filename=f"{job_id}_inpaint_mask.tif",
    )

@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    job_dir = os.path.join(UPLOAD_DIR, job_id)
    if os.path.exists(job_dir):
        shutil.rmtree(job_dir)

    results_dir = "data/results"
    dzi_file = os.path.join(results_dir, f"{job_id}_panorama.dzi")
    dzi_files_dir = os.path.join(results_dir, f"{job_id}_panorama_files")

    if os.path.exists(dzi_file):
        os.remove(dzi_file)

    if os.path.exists(dzi_files_dir):
        shutil.rmtree(dzi_files_dir)

    return {"message": "Job deleted successfully"}
