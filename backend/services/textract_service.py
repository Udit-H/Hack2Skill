import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import logging
import asyncio
import aiofiles
import base64
import time
from typing import Union, Dict, Optional
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class DocumentIntelligenceService:
    """
    Asynchronous service for Amazon Textract OCR.
    Drop-in replacement for Azure Document Intelligence.

    Supports:
    - Sync analysis: JPEG, PNG, TIFF (raw bytes or file path) — no S3 needed
    - Async analysis: PDF, multi-page TIFF — requires S3 bucket

    Usage:
        service = DocumentIntelligenceService()

        # From file path or bytes (image)
        result = await service.analyze(source="/path/to/image.jpg")

        # From S3 key (PDF)
        result = await service.analyze(source="documents/notice.pdf", is_s3_key=True)

        # From URL — downloads then analyzes
        result = await service.analyze(source="https://example.com/doc.pdf", is_url=True)
    """

    # File types that support synchronous Textract (no S3 required)
    SYNC_SUPPORTED_TYPES = {".jpg", ".jpeg", ".png", ".tiff", ".tif"}

    # File types that require async Textract via S3
    ASYNC_REQUIRED_TYPES = {".pdf"}

    def __init__(
        self,
        region_name: Optional[str] = None,
        s3_bucket: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
    ):
        """
        Initializes the Textract and S3 clients.

        Credentials are resolved in this order:
        1. Explicit kwargs (good for local dev)
        2. Environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
        3. IAM role attached to EC2/ECS (recommended for production)

        Args:
            region_name:            AWS region, defaults to AWS_REGION env var or 'ap-south-1'
            s3_bucket:              S3 bucket name for PDF uploads (required for PDF analysis)
            aws_access_key_id:      Optional explicit AWS key
            aws_secret_access_key:  Optional explicit AWS secret
        """
        self.region = region_name or os.environ.get("AWS_REGION", "ap-south-1")
        self.s3_bucket = s3_bucket or os.environ.get("S3_BUCKET_NAME")

        boto_kwargs = {"region_name": self.region}
        if aws_access_key_id and aws_secret_access_key:
            boto_kwargs["aws_access_key_id"] = aws_access_key_id
            boto_kwargs["aws_secret_access_key"] = aws_secret_access_key

        self.textract = boto3.client("textract", **boto_kwargs)
        self.s3 = boto3.client("s3", **boto_kwargs)

    # -------------------------------------------------------------------------
    # Public API — mirrors the original Azure service interface
    # -------------------------------------------------------------------------

    async def analyze(
        self,
        source: Union[str, bytes, Path],
        is_url: bool = False,
        is_s3_key: bool = False,
        model_id: str = "prebuilt-read",  # kept for interface compatibility, unused
    ) -> Dict:
        """
        Analyzes a document and returns extracted text and metadata.

        Args:
            source:     File path, raw bytes, S3 key string, or URL string
            is_url:     If True, source is treated as a URL (downloads first)
            is_s3_key:  If True, source is an existing S3 object key (skips upload)
            model_id:   Ignored — kept for drop-in compatibility with Azure interface

        Returns:
            {
                "status": "succeeded" | "failed",
                "content": "<full extracted text as single string>",
                "pages": [
                    {
                        "page": 1,
                        "lines": ["line 1 text", "line 2 text", ...],
                        "words": [{"text": "word", "confidence": 0.99}, ...]
                    }
                ],
                "raw_blocks": [...],   # Full Textract Block list for advanced use
                "page_count": 1,
                "confidence_avg": 0.97
            }
        """
        if is_url:
            source = await self._download_url(source)

        # Determine file type to choose sync vs async path
        suffix = self._get_suffix(source, is_s3_key)

        if suffix in self.ASYNC_REQUIRED_TYPES or is_s3_key:
            return await self._analyze_async(source, is_s3_key=is_s3_key)
        else:
            return await self._analyze_sync(source)

    # -------------------------------------------------------------------------
    # Sync path — images only (JPEG, PNG, TIFF)
    # -------------------------------------------------------------------------

    async def _analyze_sync(self, source: Union[str, bytes, Path]) -> Dict:
        """
        Uses Textract's synchronous DetectDocumentText API.
        Suitable for single-page images. No S3 required.
        """
        logger.info("Using synchronous Textract analysis (image input)")
        file_bytes = await self._resolve_to_bytes(source)

        # Run blocking boto3 call in thread pool so we don't block the event loop
        response = await asyncio.to_thread(
            self.textract.detect_document_text,
            Document={"Bytes": file_bytes}
        )

        return self._parse_response(response.get("Blocks", []))

    # -------------------------------------------------------------------------
    # Async path — PDFs via S3
    # -------------------------------------------------------------------------

    async def _analyze_async(
        self, source: Union[str, bytes, Path], is_s3_key: bool = False
    ) -> Dict:
        """
        Uses Textract's asynchronous StartDocumentTextDetection API.
        Required for PDFs. File must be (or will be) in S3.
        """
        if not self.s3_bucket:
            raise ValueError(
                "S3_BUCKET_NAME must be set for PDF analysis. "
                "Pass s3_bucket= to the constructor or set the S3_BUCKET_NAME env var."
            )

        if is_s3_key:
            s3_key = source
            logger.info(f"Using existing S3 object: s3://{self.s3_bucket}/{s3_key}")
        else:
            s3_key = await self._upload_to_s3(source)

        logger.info(f"Starting async Textract job for s3://{self.s3_bucket}/{s3_key}")

        # Start the job
        start_response = await asyncio.to_thread(
            self.textract.start_document_text_detection,
            DocumentLocation={
                "S3Object": {
                    "Bucket": self.s3_bucket,
                    "Name": s3_key,
                }
            }
        )

        job_id = start_response["JobId"]
        logger.info(f"Textract job started: {job_id}")

        # Poll until complete
        blocks = await self._poll_job(job_id)

        return self._parse_response(blocks)

    async def _poll_job(self, job_id: str, max_wait_seconds: int = 300) -> list:
        """
        Polls Textract until the async job completes or times out.
        Handles pagination to collect all blocks across all pages.
        """
        start_time = time.time()

        while True:
            elapsed = time.time() - start_time
            if elapsed > max_wait_seconds:
                raise TimeoutError(
                    f"Textract job {job_id} did not complete within {max_wait_seconds}s"
                )

            logger.info(f"Polling Textract job {job_id} (elapsed: {elapsed:.0f}s)")
            await asyncio.sleep(3)

            response = await asyncio.to_thread(
                self.textract.get_document_text_detection,
                JobId=job_id
            )

            status = response.get("JobStatus")
            logger.info(f"Job status: {status}")

            if status == "FAILED":
                reason = response.get("StatusMessage", "No reason provided")
                raise RuntimeError(f"Textract job failed: {reason}")

            if status == "SUCCEEDED":
                # Collect all blocks, handling pagination
                all_blocks = response.get("Blocks", [])
                next_token = response.get("NextToken")

                while next_token:
                    paginated = await asyncio.to_thread(
                        self.textract.get_document_text_detection,
                        JobId=job_id,
                        NextToken=next_token
                    )
                    all_blocks.extend(paginated.get("Blocks", []))
                    next_token = paginated.get("NextToken")

                logger.info(f"Job succeeded. Total blocks: {len(all_blocks)}")
                return all_blocks

    # -------------------------------------------------------------------------
    # Response parsing — converts Textract Blocks → clean structured output
    # -------------------------------------------------------------------------

    def _parse_response(self, blocks: list) -> Dict:
        """
        Converts Textract Block list into a clean, structured response.

        Textract Block types used here:
        - PAGE:  represents one page (contains child block IDs)
        - LINE:  a line of text (contains WORD children)
        - WORD:  individual word with confidence score
        """
        pages: Dict[int, Dict] = {}
        all_words = []

        for block in blocks:
            block_type = block.get("BlockType")
            page_num = block.get("Page", 1)

            if page_num not in pages:
                pages[page_num] = {"page": page_num, "lines": [], "words": []}

            if block_type == "LINE":
                pages[page_num]["lines"].append(block.get("Text", ""))

            elif block_type == "WORD":
                word_entry = {
                    "text": block.get("Text", ""),
                    "confidence": round(block.get("Confidence", 0) / 100, 4),
                }
                pages[page_num]["words"].append(word_entry)
                all_words.append(word_entry)

        # Sort pages and build full text
        sorted_pages = [pages[p] for p in sorted(pages.keys())]
        full_text = "\n\n".join(
            "\n".join(page["lines"]) for page in sorted_pages
        )

        # Average confidence across all words
        avg_confidence = (
            round(sum(w["confidence"] for w in all_words) / len(all_words), 4)
            if all_words else 0.0
        )

        return {
            "status": "succeeded",
            "content": full_text,
            "pages": sorted_pages,
            "raw_blocks": blocks,
            "page_count": len(sorted_pages),
            "confidence_avg": avg_confidence,
        }

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    async def _upload_to_s3(self, source: Union[str, bytes, Path]) -> str:
        """
        Uploads a local file or bytes to S3 for async Textract processing.
        Returns the S3 object key.
        """
        file_bytes = await self._resolve_to_bytes(source)

        # Generate a unique key using timestamp
        timestamp = int(time.time() * 1000)
        suffix = self._get_suffix(source) or ".pdf"
        s3_key = f"textract-uploads/{timestamp}{suffix}"

        logger.info(f"Uploading document to s3://{self.s3_bucket}/{s3_key}")

        await asyncio.to_thread(
            self.s3.put_object,
            Bucket=self.s3_bucket,
            Key=s3_key,
            Body=file_bytes,
        )

        return s3_key

    async def _download_url(self, url: str) -> bytes:
        """Downloads a file from a URL and returns its bytes."""
        import aiohttp
        logger.info(f"Downloading document from URL: {url}")
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                return await response.read()

    async def _resolve_to_bytes(self, source: Union[str, bytes, Path]) -> bytes:
        """Resolves file path or Path object to raw bytes."""
        if isinstance(source, bytes):
            return source
        async with aiofiles.open(source, "rb") as f:
            return await f.read()

    def _get_suffix(
        self,
        source: Union[str, bytes, Path],
        is_s3_key: bool = False
    ) -> str:
        """Extracts the file extension from a path or S3 key string."""
        if isinstance(source, bytes):
            return ""
        return Path(str(source)).suffix.lower()

    async def _resolve_bytes_to_base64(self, source: Union[bytes, Path, str]) -> str:
        """
        Kept for interface compatibility with the original Azure service.
        Not used internally by Textract.
        """
        file_bytes = await self._resolve_to_bytes(source)
        return base64.b64encode(file_bytes).decode("utf-8")