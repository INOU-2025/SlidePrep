from fastapi import APIRouter, UploadFile, File, Form
from typing import List
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
    clean_grid: str = Form("true") # Receive as string from FormData
):
    # Convert string boolean to actual boolean
    clean_grid_bool = clean_grid.lower() == 'true'

    job_id = str(uuid.uuid4())
    job_dir = os.path.join(UPLOAD_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)
    
    # Save uploaded files
    for file in files:
        file_path = os.path.join(job_dir, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Check if it is a zip file and extract it
        if file.filename.endswith('.zip'):
            try:
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(job_dir)
                # Optional: remove the zip file after extraction
                os.remove(file_path)
                
                # Clean up __MACOSX directory if it exists (common in mac zips)
                macosx_path = os.path.join(job_dir, "__MACOSX")
                if os.path.exists(macosx_path):
                    shutil.rmtree(macosx_path)
                    
                # Flatten directory structure: move all files from subdirectories to job_dir
                for root, dirs, files_in_dir in os.walk(job_dir):
                    if root == job_dir:
                        continue
                    for filename in files_in_dir:
                        src_path = os.path.join(root, filename)
                        dst_path = os.path.join(job_dir, filename)
                        # Handle duplicate names by renaming
                        if os.path.exists(dst_path):
                            base, ext = os.path.splitext(filename)
                            dst_path = os.path.join(job_dir, f"{base}_{uuid.uuid4().hex[:8]}{ext}")
                        shutil.move(src_path, dst_path)
                
                # Remove empty directories
                for root, dirs, files_in_dir in os.walk(job_dir, topdown=False):
                    if root == job_dir:
                        continue
                    if not os.listdir(root):
                        os.rmdir(root)
            except zipfile.BadZipFile:
                # If it's not a valid zip, we might want to log it or just leave it as is
                pass
            
    # Trigger Celery task
    # We need a config path. For now, we'll use a default one or create a temporary one.
    # Assuming there is a default config.yaml in the root or config folder.
    task = process_images_task.apply_async(
        args=[job_id, job_dir, job_dir, CONFIG_PATH, clean_grid_bool],
        task_id=job_id
    )
    
    return JobResponse(job_id=job_id, status="QUEUED", message="Job submitted successfully")

@router.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    # In a real app, we'd look up the task ID associated with the job ID in a DB.
    # For this MVP, we are using the job_id as the task_id logic or we need to store the mapping.
    # Wait, process_images_task.delay() returns a task_id. We aren't storing it.
    # To fix this for MVP without a DB:
    # We can't easily look up a task by a custom ID unless we force the task ID.
    
    # Let's try to find the task by the job_id if we passed it as an arg, but Celery lookup is by Task ID.
    # IMPROVEMENT: Use job_id as task_id
    # But we already called .delay().
    
    # Let's just return a placeholder for now or we need to implement a simple DB (sqlite).
    # OR, we can just say "Check the results folder".
    
    # Better approach for MVP:
    # When creating the task, we can use `process_images_task.apply_async(args=[...], task_id=job_id)`
    # This way job_id == task_id.
    
    task_result = AsyncResult(job_id)
    
    status = task_result.status
    result_url = None
    error = None
    message = None
    
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
    # Delete upload directory
    job_dir = os.path.join(UPLOAD_DIR, job_id)
    if os.path.exists(job_dir):
        shutil.rmtree(job_dir)
    
    # Delete results
    # Results are stored in data/results with naming convention: {job_id}_panorama.dzi and {job_id}_panorama_files
    results_dir = "data/results"
    dzi_file = os.path.join(results_dir, f"{job_id}_panorama.dzi")
    dzi_files_dir = os.path.join(results_dir, f"{job_id}_panorama_files")
    
    if os.path.exists(dzi_file):
        os.remove(dzi_file)
        
    if os.path.exists(dzi_files_dir):
        shutil.rmtree(dzi_files_dir)
        
    return {"message": "Job deleted successfully"}
