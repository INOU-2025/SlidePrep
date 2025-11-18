from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI(title="SlidePrep Service")

# Mount static files for results
os.makedirs("data/results", exist_ok=True)
app.mount("/results", StaticFiles(directory="data/results"), name="results")

from .routes import router

app.include_router(router)

@app.get("/")
def read_root():
    return {"message": "Welcome to SlidePrep Service"}
