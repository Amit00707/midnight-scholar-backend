"""
Storage Service — AWS S3 (Optional)
=====================================
Handles PDF storage. Disabled gracefully when boto3 is not installed.
"""

from app.core.config import settings

try:
    import boto3
    from botocore.config import Config

    s3_client = boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
        config=Config(signature_version="s3v4"),
    )
    _s3_available = True
except ImportError:
    s3_client = None
    _s3_available = False


def upload_pdf(file_bytes: bytes, s3_key: str) -> str:
    """Upload a PDF file to S3 and return its key."""
    if not _s3_available or not s3_client:
        raise RuntimeError("S3 storage is not configured.")
    s3_client.put_object(
        Bucket=settings.AWS_S3_BUCKET,
        Key=s3_key,
        Body=file_bytes,
        ContentType="application/pdf",
    )
    return s3_key


def generate_signed_url(s3_key: str, expires_in: int = 3600) -> str:
    """Generate a time-limited pre-signed URL for secure PDF streaming."""
    if not _s3_available or not s3_client:
        return ""
    url = s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.AWS_S3_BUCKET, "Key": s3_key},
        ExpiresIn=expires_in,
    )
    return url


def delete_pdf(s3_key: str):
    """Delete a PDF from S3."""
    if not _s3_available or not s3_client:
        return
    s3_client.delete_object(Bucket=settings.AWS_S3_BUCKET, Key=s3_key)
