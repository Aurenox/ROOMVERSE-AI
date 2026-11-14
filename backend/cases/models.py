import uuid

from django.conf import settings
from django.db import models


class Game(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    guest = models.CharField(max_length=64, db_index=True, blank=True)
    player = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE, related_name="games")
    case = models.JSONField()
    attempts = models.JSONField(default=list)
    hints = models.JSONField(default=list)
    created = models.DateTimeField(auto_now_add=True)
    deadline = models.DateTimeField(null=True)
    completed = models.DateTimeField(null=True, db_index=True)
    score = models.PositiveSmallIntegerField(default=0, db_index=True)


class Scan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    guest = models.CharField(max_length=64, db_index=True, blank=True)
    player = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE, related_name="scans")
    detections = models.JSONField(default=list)
    source = models.CharField(max_length=16)
    created = models.DateTimeField(auto_now_add=True)


class AIWindow(models.Model):
    key = models.CharField(max_length=80, primary_key=True)
    count = models.PositiveIntegerField(default=0)
    expires = models.DateTimeField(db_index=True)


class AICache(models.Model):
    key = models.CharField(max_length=64, primary_key=True)
    payload = models.JSONField()
    expires = models.DateTimeField(db_index=True)


class RoundArchive(models.Model):
    """Shared fictional virtual rounds; no player identity or uploaded photo."""
    digest = models.CharField(max_length=64, unique=True)
    section = models.CharField(max_length=80, db_index=True)
    payload = models.JSONField()
    created = models.DateTimeField(auto_now_add=True)


class ArchiveFingerprint(models.Model):
    archive = models.ForeignKey(RoundArchive, on_delete=models.CASCADE, related_name="fingerprints")
    section = models.CharField(max_length=80)
    kind = models.CharField(max_length=16)
    digest = models.CharField(max_length=64)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["section", "kind", "digest"], name="unique_archived_content")]


class Profile(models.Model):
    player = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    avatar = models.CharField(max_length=16, default="radar")
    public_score = models.BooleanField(default=False)
    voice_style = models.CharField(max_length=16, default="style:luna")
    voice_rate = models.FloatField(default=0.9)
    gender = models.CharField(max_length=6, choices=[("male", "Male"), ("female", "Female"), ("others", "Others")], default="others")
