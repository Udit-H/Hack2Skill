import os
import mimetypes
from typing import Optional
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv


env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)


class DraftStorageService:
    """Stores generated draft files in S3 and returns downloadable links."""

    def __init__(self, bucket_name: Optional[str] = None, region_name: Optional[str] = None):
        self.bucket_name = bucket_name or os.getenv("S3_BUCKET_NAME")
        self.region_name = region_name or os.getenv("AWS_REGION", "us-east-1")
        self.s3 = boto3.client("s3", region_name=self.region_name)

    @staticmethod
    def build_s3_key(session_id: str, filename: str) -> str:
        return f"drafts/{session_id}/{filename}"

    def upload_draft(self, file_path: str, session_id: str, filename: str) -> str:
        """Upload generated draft file to S3 and return S3 key."""
        if not self.bucket_name:
            raise RuntimeError("S3_BUCKET_NAME is not configured")

        s3_key = self.build_s3_key(session_id, filename)
        content_type = mimetypes.guess_type(filename)[0] or "application/pdf"

        self.s3.upload_file(
            Filename=file_path,
            Bucket=self.bucket_name,
            Key=s3_key,
            ExtraArgs={
                "ContentType": content_type,
                "ContentDisposition": f'attachment; filename="{filename}"',
            },
        )

        return s3_key

    def generate_presigned_download_url(self, session_id: str, filename: str, expires_in: int = 3600) -> str:
        """Generate presigned GET URL for a stored draft in S3."""
        if not self.bucket_name:
            raise RuntimeError("S3_BUCKET_NAME is not configured")

        s3_key = self.build_s3_key(session_id, filename)
        return self.s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket_name, "Key": s3_key},
            ExpiresIn=expires_in,
        )

    def object_exists(self, session_id: str, filename: str) -> bool:
        """Check whether a draft object exists in S3."""
        if not self.bucket_name:
            return False

        s3_key = self.build_s3_key(session_id, filename)
        try:
            self.s3.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError:
            return False
