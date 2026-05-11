import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="SlidePrep Service")

_cors_origins = os.environ.get("CORS_ORIGINS", "http://localhost:4200").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for results
os.makedirs("data/results", exist_ok=True)
app.mount("/results", StaticFiles(directory="data/results"), name="results")

from .routes import router

app.include_router(router)

@app.get("/")
def read_root():
    return {"message": "Welcome to SlidePrep Service"}
