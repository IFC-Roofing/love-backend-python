"""
S3 upload helpers – store files and return public URLs.
"""
import logging
from typing import Optional

from app.aws.client import get_aws_client
from app.core.config import settings

logger = logging.getLogger(__name__)


def get_s3_client():
    """S3 client for the configured region."""
    return get_aws_client("s3", region_name=settings.s3_region)


def build_public_url(key: str) -> str:
    """Build public URL for an S3 object (bucket must allow public read)."""
    bucket = settings.S3_BUCKET_NAME
    region = settings.s3_region
    return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"


def upload_to_s3(
    key: str,
    body: bytes,
    content_type: str,
    bucket: Optional[str] = None,
) -> str:
    """
    Upload bytes to S3 and return the object URL.

    Does not use ACLs (avoids AccessControlListNotSupported on buckets with
    "Bucket owner enforced" ownership). For public read, add a bucket policy
    that allows s3:GetObject for your bucket (see docs/S3_SETUP.md).

    Args:
        key: S3 object key (e.g. postcards/<id>/front.jpg)
        body: File bytes
        content_type: MIME type (e.g. image/jpeg)
        bucket: Override bucket; defaults to settings.S3_BUCKET_NAME

    Returns:
        Full URL to the object (https://bucket.s3.region.amazonaws.com/key).
    """
    b = bucket or settings.S3_BUCKET_NAME
    if not b:
        raise ValueError("S3_BUCKET_NAME not configured")

    client = get_s3_client()
    client.put_object(
        Bucket=b,
        Key=key,
        Body=body,
        ContentType=content_type,
    )
    url = build_public_url(key)
    logger.info(f"Uploaded S3 key={key} -> {url}")
    return url
