from fastapi import APIRouter, UploadFile, File, Form
from typing import List, Optional
import uuid
import os
import shutil
import zipfile
from .schemas import JobResponse, JobStatus
from worker.tasks import process_images_task
from celery.result import AsyncResult

router = APIRouter()

UPLOAD_DIR = "data/uploads"
CONFIG_PATH = os.environ.get("SLIDEPREP_CONFIG", "config/production.json")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/jobs", response_model=JobResponse)
async def create_job(
    files: List[UploadFile] = File(...),
    clean_grid: str = Form("true"),
    grid_width: Optional[str] = Form(None),
    grid_height: Optional[str] = Form(None),
    overlap: Optional[str] = Form(None),
    pixel_size: Optional[str] = Form(None),
    direction: Optional[str] = Form(None),
    suffix_filter: Optional[str] = Form(None),
):
    clean_grid_bool = clean_grid.lower() == 'true'

    job_id = str(uuid.uuid4())
    job_dir = os.path.join(UPLOAD_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)

    # Save uploaded files
    for file in files:
        file_path = os.path.join(job_dir, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Extract zip archives
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

    # Build per-job config overrides from form fields
    stitching_overrides = {}
    if grid_width:  stitching_overrides['width']      = int(grid_width)
    if grid_height: stitching_overrides['height']     = int(grid_height)
    if overlap:     stitching_overrides['overlap']    = float(overlap)
    if pixel_size:  stitching_overrides['pixel_size'] = float(pixel_size)
    if direction:   stitching_overrides['direction']  = direction

    general_overrides = {}
    if suffix_filter is not None:
        general_overrides['suffix_filter'] = suffix_filter

    task = process_images_task.apply_async(
        args=[job_id, job_dir, job_dir, CONFIG_PATH, clean_grid_bool,
              stitching_overrides, general_overrides],
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

    if status == 'SUCCESS':
        result = task_result.result
        if result and 'result_path' in result:
            result_url = f"/results/{result['result_path']}"
    elif status == 'FAILURE':
        error = str(task_result.result)
    elif status == 'PROCESSING':
        info = task_result.info
        if isinstance(info, dict):
            message = info.get('status')
            progress = info.get('progress')

    return JobStatus(job_id=job_id, status=status, result_url=result_url, error=error, message=message, progress=progress)

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
