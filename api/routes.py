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

# Starlette's default form parser caps a multipart request at 1000 files, which a
# multi-channel whole-slide tile set easily exceeds. FastAPI's `File(...)`/`Form(...)`
# injection calls `request.form()` with no way to override that limit, so the form is
# parsed manually here instead.
MAX_UPLOAD_FILES = 100_000

@router.post("/jobs", response_model=JobResponse)
async def create_job(request: Request):
    form = await request.form(max_files=MAX_UPLOAD_FILES)
    files: List[Any] = form.getlist("files")
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

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

    for file in files:
        file_path = os.path.join(job_dir, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        if file.filename.endswith('.zip'):
            try:
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(job_dir)
                os.remove(file_path)

                macosx_path = os.path.join(job_dir, "__MACOSX")
                if os.path.exists(macosx_path):
                    shutil.rmtree(macosx_path)

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

                for root, dirs, files_in_dir in os.walk(job_dir, topdown=False):
                    if root == job_dir:
                        continue
                    if not os.listdir(root):
                        os.rmdir(root)
            except zipfile.BadZipFile:
                pass

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
