import pytest
from rest_framework.test import APIClient

from .services import process_job


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def create_job(api_client):
    def _create(recipients):
        data = {
            "course_name": "Python Basics",
            "issued_by": "Acme Academy",
            "issued_date": "2026-10-01",
            "recipients": recipients,
        }
        response = api_client.post("/jobs/", data, format="json")
        return response, response.data.get("job_id")
    return _create


@pytest.fixture
def create_and_process(create_job):
    def _run(recipients):
        _, job_id = create_job(recipients)
        process_job(job_id)
        return job_id
    return _run