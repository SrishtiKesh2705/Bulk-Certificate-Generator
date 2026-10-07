from django.shortcuts import render

from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Job, Certificate
from .serializers import JobCreateSerializer
from .validators import validate_recipient
from .services import enqueue_job

from django.db.models import Count, Q
from django.shortcuts import get_object_or_404

from django.http import FileResponse, Http404
from rest_framework.reverse import reverse

class JobCreateView(APIView):
    def post(self, request):
        serializer=JobCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data=serializer.validated_data

        with transaction.atomic():
            job=Job.objects.create(
                course_name=data["course_name"],
                issued_by=data["issued_by"],
                issued_date=data["issued_date"],
                total_count=len(data["recipients"]),
            )

            certificates=[]
            for index, row in enumerate(data["recipients"]):
                error=validate_recipient(row)
                certificates.append(Certificate(
                    job=job,
                    row_index=index,
                    recipient_name=str(row.get("name") or "")[:255],
                    recipient_email=str(row.get("email") or "")[:255],
                    raw_data=row,
                    status=Certificate.Status.FAILED if error else Certificate.Status.PENDING,
                    error_message=error or "",
                ))
            Certificate.objects.bulk_create(certificates, batch_size=500)
        transaction.on_commit(lambda: enqueue_job(job.id))
        return Response(
            {"job_id":job.id, "status":job.status, "total":job.total_count},
            status=status.HTTP_202_ACCEPTED,
        )


class JobDetailView(APIView):
    def get(self, request, job_id):
        job = get_object_or_404(Job, pk=job_id)

        counts = job.certificates.aggregate(
            succeeded=Count("id", filter=Q(status=Certificate.Status.SUCCESS)),
            failed=Count("id", filter=Q(status=Certificate.Status.FAILED)),
        )
        succeeded, failed = counts["succeeded"], counts["failed"]
        processed = succeeded + failed

        failures = job.certificates.filter(
            status=Certificate.Status.FAILED
        ).values("row_index", "recipient_name", "recipient_email", "error_message")

        return Response({
            "job_id": job.id,
            "status": job.status,
            "course_name": job.course_name,
            "total": job.total_count,
            "succeeded": succeeded,
            "failed": failed,
            "pending": job.total_count - processed,
            "progress_percent": round(processed / job.total_count * 100, 1) if job.total_count else 100,
            "created_at": job.created_at,
            "started_at": job.started_at,
            "finished_at": job.finished_at,
            "failures": list(failures),
        })

class JobCertificateListView(APIView):
    def get(self, request, job_id):
        job = get_object_or_404(Job, pk=job_id)
        certificates = job.certificates.filter(status=Certificate.Status.SUCCESS)

        return Response([
            {
                "certificate_id": c.id,
                "row_index": c.row_index,
                "recipient_name": c.recipient_name,
                "recipient_email": c.recipient_email,
                "generated_at": c.generated_at,
                "download_url": reverse(
                    "certificate-download",
                    kwargs={"certificate_id": c.id},
                    request=request,
                ),
            }
            for c in certificates
        ])


class CertificateDownloadView(APIView):
    def get(self, request, certificate_id):
        cert = get_object_or_404(
            Certificate, pk=certificate_id, status=Certificate.Status.SUCCESS
        )
        try:
            file_handle = cert.file.open("rb")
        except FileNotFoundError:
            raise Http404("Certificate file not found")

        return FileResponse(
            file_handle,
            as_attachment=True,
            filename=f"certificate_{cert.row_index}.pdf",
            content_type="application/pdf",
        )