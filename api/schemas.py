from pydantic import BaseModel
from typing import Optional

class JobResponse(BaseModel):
    job_id: str
    status: str
    message: str = ""

class JobStatus(BaseModel):
    job_id: str
    status: str
    result_url: Optional[str] = None
    error: Optional[str] = None