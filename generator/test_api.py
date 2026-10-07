import pytest

from .models import Job, Certificate
from .pdf import render_certificate_pdf as real_render

pytestmark = pytest.mark.django_db

def test_create_job(create_job):
    response, job_id = create_job([{"name": "Asha"}, {"name": "Ravi"}])
    assert response.status_code == 202
    assert Certificate.objects.filter(job_id=job_id).count() == 2


def test_invalid_request_is_rejected(create_job):
    response, _ = create_job([])
    assert response.status_code == 400
    assert Job.objects.count() == 0


def test_invalid_recipient_is_marked_failed(create_job):
    _, job_id = create_job([{"name": "Asha"}, {"name": ""}])
    bad = Certificate.objects.get(job_id=job_id, row_index=1)
    assert bad.status == "failed"
    assert bad.error_message == "name is required"


def test_certificate_is_generated(create_and_process):
    job_id = create_and_process([{"name": "Asha"}])
    cert = Certificate.objects.get(job_id=job_id)
    assert cert.status == "success"
    assert cert.file.name.endswith(".pdf")


def test_job_status(create_and_process, api_client):
    job_id = create_and_process([{"name": "Asha"}, {"name": ""}])
    data = api_client.get(f"/jobs/{job_id}/").data
    assert data["status"] == "completed_with_errors"
    assert data["succeeded"] == 1
    assert data["failed"] == 1


def test_one_failure_does_not_stop_others(create_and_process, monkeypatch):
    def flaky(**kwargs):
        if kwargs["recipient_name"] == "Ravi":
            raise RuntimeError("boom")
        return real_render(**kwargs)

    monkeypatch.setattr("generator.services.render_certificate_pdf", flaky)
    job_id = create_and_process([{"name": "Asha"}, {"name": "Ravi"}, {"name": "Meera"}])

    certs = Certificate.objects.filter(job_id=job_id)
    assert certs.filter(status="success").count() == 2
    assert "boom" in certs.get(status="failed").error_message


def test_list_and_download(create_and_process, api_client):
    job_id = create_and_process([{"name": "Asha"}])
    listing = api_client.get(f"/jobs/{job_id}/certificates/")
    assert len(listing.data) == 1

    cert = Certificate.objects.get(job_id=job_id)
    download = api_client.get(f"/certificates/{cert.id}/download/")
    assert download.status_code == 200
    assert download["Content-Type"] == "application/pdf"