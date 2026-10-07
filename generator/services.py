import logging
from concurrent.futures import ThreadPoolExecutor

from django.core.files.base import ContentFile
from django.db import connections
from django.utils import timezone

from .models import Job, Certificate
from .pdf import render_certificate_pdf

logger = logging.getLogger(__name__)
executor = ThreadPoolExecutor(max_workers=4)


def process_job(job_id):
    job = Job.objects.get(pk=job_id)
    job.status = Job.Status.PROCESSING
    job.started_at = timezone.now()
    job.save(update_fields=["status", "started_at"])

    pending = job.certificates.filter(status=Certificate.Status.PENDING)
    for cert in pending.iterator():
        try:
            pdf = render_certificate_pdf(
                recipient_name=cert.recipient_name,
                course_name=job.course_name,
                issued_by=job.issued_by,
                issued_date=job.issued_date,
            )
            cert.file.save(f"{cert.id}.pdf", ContentFile(pdf), save=False)
            cert.status = Certificate.Status.SUCCESS
            cert.generated_at = timezone.now()
        except Exception as exc:  
            logger.exception("Certificate %s failed", cert.id)
            cert.status = Certificate.Status.FAILED
            cert.error_message = f"generation failed: {exc}"[:1000]
        cert.save()

    succeeded = job.certificates.filter(status=Certificate.Status.SUCCESS).count()
    failed = job.certificates.filter(status=Certificate.Status.FAILED).count()

    if failed == 0:
        job.status = Job.Status.COMPLETED
    elif succeeded == 0:
        job.status = Job.Status.FAILED
    else:
        job.status = Job.Status.COMPLETED_WITH_ERRORS
    job.finished_at = timezone.now()
    job.save(update_fields=["status", "finished_at"])


def run(job_id):
    try:
        process_job(job_id)
    except Exception:
        logger.exception("Job %s crashed", job_id)
        Job.objects.filter(pk=job_id).update(
            status=Job.Status.FAILED, finished_at=timezone.now()
        )
    finally:
        connections.close_all()  

def enqueue_job(job_id):
    executor.submit(run, job_id)