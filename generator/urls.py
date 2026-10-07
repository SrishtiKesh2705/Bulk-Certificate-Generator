from django.urls import path
from .views import JobCreateView, JobDetailView, JobCertificateListView, CertificateDownloadView

urlpatterns=[
    path("jobs/",JobCreateView.as_view()),
    path("jobs/<uuid:job_id>/",JobDetailView.as_view()),
    path("jobs/<uuid:job_id>/certificates/", JobCertificateListView.as_view()),
    path("certificates/<uuid:certificate_id>/download/",CertificateDownloadView.as_view(),name="certificate-download",
    ),
]