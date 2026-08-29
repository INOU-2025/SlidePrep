"""Shared fixtures for API-level (FastAPI TestClient) tests.

These exercise the real `api.app.app` — real upload validation, real zip
extraction, real filesystem export/delete — with two exceptions handled
deliberately, not accidentally:

- `mock_dispatch` stubs Celery's `apply_async` for tests that only care
  about what happens *before* dispatch (upload/archive validation, export,
  delete). Those tests never claim to cover async execution; stubbing this
  call here keeps them from needing Redis at all.
- `celery_eager` (used only by test_async_job.py) does the opposite: it
  makes `apply_async` run the real task synchronously through Celery's own
  eager-execution machinery, so that file is testing the real task body,
  not a mock of it.
"""

import os
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

import api.routes as routes_module
from api.app import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def upload_dir(tmp_path, monkeypatch):
    """Point UPLOAD_DIR at a throwaway directory instead of the real data/uploads."""
    d = tmp_path / "uploads"
    d.mkdir()
    monkeypatch.setattr(routes_module, "UPLOAD_DIR", str(d))
    return str(d)


@pytest.fixture
def small_limits(monkeypatch):
    """Shrink the upload size/count limits so limit-enforcement tests run
    fast while still exercising the real enforcement code in routes.py,
    not a simulation of it."""
    monkeypatch.setattr(routes_module, "MAX_FILE_SIZE_BYTES", 1024)
    monkeypatch.setattr(routes_module, "MAX_TOTAL_UPLOAD_BYTES", 4096)
    monkeypatch.setattr(routes_module, "MAX_FILES_PER_JOB", 5)


@pytest.fixture
def mock_dispatch(monkeypatch):
    """Stub the Celery dispatch call for tests that only exercise
    upload/archive/export/delete. See module docstring.

    Replaces the *name* `process_images_task` in routes_module's namespace
    with an inert stand-in, rather than patching an attribute onto the real
    (module-level singleton) Celery task object — mutating that shared
    object, even temporarily, left it in a state that made a later, real
    eager-mode execution (test_async_job.py) silently fail to persist its
    result to the backend. Swapping the name binding instead means these
    tests never touch the real task/app machinery at all.
    """
    fake_task = MagicMock()
    fake_task.id = "fake-task-id"
    stub = MagicMock()
    stub.apply_async = MagicMock(return_value=fake_task)
    monkeypatch.setattr(routes_module, "process_images_task", stub)
    return stub.apply_async
