"""CLI script for running the full PipelineService end-to-end on a directory."""

import requests
import time
import sys
import os

API_URL = "http://localhost:8000"

def test_service(image_paths):
    print(f"Uploading {len(image_paths)} images...")
    files = [('files', open(path, 'rb')) for path in image_paths]
    
    response = requests.post(f"{API_URL}/jobs", files=files)
    if response.status_code != 200:
        print(f"Upload failed: {response.text}")
        return
    
    job_id = response.json()['job_id']
    print(f"Job started with ID: {job_id}")
    
    while True:
        status_res = requests.get(f"{API_URL}/jobs/{job_id}")
        status_data = status_res.json()
        status = status_data['status']
        
        print(f"Status: {status}")
        
        if status == 'COMPLETED' or status == 'SUCCESS':
            print(f"Job finished! Result URL: {status_data['result_url']}")
            break
        elif status == 'FAILURE':
            print(f"Job failed: {status_data.get('error')}")
            break
            
        time.sleep(2)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_service.py <path_to_image1> <path_to_image2> ...")
        sys.exit(1)
        
    test_service(sys.argv[1:])
