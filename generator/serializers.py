from rest_framework import serializers
from .models import Job

MAX_RECIPIENTS=5000

class JobCreateSerializer(serializers.ModelSerializer):
    recipients=serializers.ListField(
        child=serializers.DictField(),
        allow_empty=False,
        max_length=MAX_RECIPIENTS,
        write_only=True
    )

    class Meta:
        model=Job
        fields=["course_name", "issued_by", "issued_date", "recipients"]