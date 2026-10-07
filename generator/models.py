from django.db import models

# Create your models here.
import uuid
from django.db import models

class Job(models.Model):
    class Status(models.TextChoices):
        PENDING="pending"
        PROCESSING="processing"
        COMPLETED="completed"
        COMPLETED_WITH_ERRORS="completed_with_errors"
        FAILED="failed"

    id=models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    course_name=models.CharField(max_length=255)
    issued_by=models.CharField(max_length=255)
    issued_date=models.DateField()
    status=models.CharField(max_length=30, choices=Status.choices, default=Status.PENDING, db_index=True)
    total_count=models.PositiveIntegerField(default=0)
    created_at=models.DateTimeField(auto_now_add=True)
    started_at=models.DateTimeField(null=True, blank=True)
    finished_at=models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering=['-created_at']

class Certificate(models.Model):
    class Status(models.TextChoices):
        PENDING="pending"
        PROCESSING="processing"
        SUCCESS="success"
        FAILED="failed"

    id=models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job=models.ForeignKey(Job, on_delete=models.CASCADE, related_name="certificates")
    row_index=models.PositiveIntegerField()
    recipient_name=models.CharField(max_length=255, blank=True)
    recipient_email=models.CharField(max_length=255, blank=True)
    raw_data=models.JSONField(default=dict)
    status=models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    file=models.FileField(upload_to="certificates/%Y/%m/", blank=True)
    error_message=models.TextField(blank=True)
    created_at=models.DateTimeField(auto_now_add=True)
    generated_at=models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering=['row_index']
        indexes=[models.Index(fields=["job","status"])]
        constraints=[models.UniqueConstraint(fields=["job","row_index"],
                                             name="unique_row_per_job") ,
        ]
