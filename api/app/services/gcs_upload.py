"""Best-effort audio upload to Google Cloud Storage."""

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def upload_audio_to_gcs(
    audio_bytes: bytes,
    user_id: str,
    question_id: str,
    attempt_id: str,
    mime_type: str,
) -> Optional[str]:
    """Upload audio to GCS. Returns GCS path on success, None on failure. Never raises."""
    try:
        from app.config import get_settings

        settings = get_settings()
        bucket_name = settings.gcs_audio_bucket
        if not bucket_name:
            return None

        ext_map = {
            "audio/webm": "webm",
            "audio/mp4": "m4a",
            "audio/x-m4a": "m4a",
            "audio/mpeg": "mp3",
            "audio/wav": "wav",
            "audio/x-wav": "wav",
        }
        ext = ext_map.get(mime_type, "audio")
        blob_path = f"onsite-prep/{user_id}/{question_id}/{attempt_id}.{ext}"

        def _upload():
            from google.cloud import storage

            client = storage.Client()
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(blob_path)
            blob.upload_from_string(audio_bytes, content_type=mime_type)

        await asyncio.to_thread(_upload)
        logger.info("Uploaded audio to gs://%s/%s", bucket_name, blob_path)
        return f"gs://{bucket_name}/{blob_path}"

    except Exception:
        logger.warning("Failed to upload audio to GCS (best-effort)", exc_info=True)
        return None


async def upload_image_to_gcs(
    image_bytes: bytes,
    user_id: str,
    attempt_id: str,
    filename: str,
    mime_type: str,
    phase_number: int | None = None,
) -> Optional[str]:
    """Upload an image to GCS. Returns GCS path on success, None on failure. Never raises."""
    try:
        from app.config import get_settings

        settings = get_settings()
        bucket_name = settings.gcs_audio_bucket
        if not bucket_name:
            return None

        ext_map = {
            "image/jpeg": "jpg",
            "image/png": "png",
            "image/webp": "webp",
            "image/gif": "gif",
        }
        ext = ext_map.get(mime_type, "jpg")
        phase_prefix = f"phase_{phase_number}_" if phase_number else ""
        # Use a sanitized filename or fall back to index
        import uuid
        safe_name = f"{phase_prefix}{uuid.uuid4().hex[:8]}.{ext}"
        blob_path = f"onsite-prep/{user_id}/{attempt_id}/images/{safe_name}"

        def _upload():
            from google.cloud import storage

            client = storage.Client()
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(blob_path)
            blob.upload_from_string(image_bytes, content_type=mime_type)

        await asyncio.to_thread(_upload)
        logger.info("Uploaded image to gs://%s/%s", bucket_name, blob_path)
        return f"gs://{bucket_name}/{blob_path}"

    except Exception:
        logger.warning("Failed to upload image to GCS (best-effort)", exc_info=True)
        return None
