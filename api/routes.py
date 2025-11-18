from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from typing import List
import uuid
import os
import shutil
from .schemas import JobResponse, JobStatus
from worker.tasks import process_images_task
from celery.result import AsyncResult

router = APIRouter()

UPLOAD_DIR = "data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/jobs", response_model=JobResponse)
async def create_job(files: List[UploadFile] = File(...)):
    job_id = str(uuid.uuid4())
    job_dir = os.path.join(UPLOAD_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)
    
    # Save uploaded files
    for file in files:
        file_path = os.path.join(job_dir, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
    # Trigger Celery task
    # We need a config path. For now, we'll use a default one or create a temporary one.
    # Assuming there is a default config.yaml in the root or config folder.
    config_path = "config/default_config.yaml" # You might need to adjust this
    
    task = process_images_task.apply_async(
        args=[job_id, job_dir, job_dir, config_path],
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
    
    if status == 'SUCCESS':
        result = task_result.result
        if result and 'result_path' in result:
            result_url = f"/results/{result['result_path']}"
    elif status == 'FAILURE':
        error = str(task_result.result)
        
    return JobStatus(job_id=job_id, status=status, result_url=result_url, error=error)
