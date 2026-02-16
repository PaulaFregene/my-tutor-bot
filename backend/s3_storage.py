"""
S3 Storage Module for PDF Files
Handles upload, download, list, and delete operations for S3
"""

import os
import tempfile
from pathlib import Path
from typing import List, Optional

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

# S3 Configuration
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_S3_BUCKET = os.getenv("AWS_S3_BUCKET")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
USE_S3 = os.getenv("USE_S3", "false").lower() == "true"

# Initialize S3 client (only if S3 is enabled)
s3_client = None
if USE_S3 and AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY and AWS_S3_BUCKET:
    try:
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION,
        )
        print(f"[S3] Initialized S3 client for bucket: {AWS_S3_BUCKET}")
    except Exception as e:
        print(f"[S3 ERROR] Failed to initialize S3 client: {e}")
        s3_client = None
else:
    print("[S3] S3 storage disabled or not configured, using local storage")


def is_s3_enabled() -> bool:
    """Check if S3 storage is enabled and properly configured"""
    return s3_client is not None


def upload_file_to_s3(file_path: Path, s3_key: Optional[str] = None) -> bool:
    """
    Upload a file to S3

    Args:
        file_path: Local path to the file
        s3_key: S3 object key (defaults to filename)

    Returns:
        True if successful, False otherwise
    """
    if not is_s3_enabled():
        print("[S3] S3 not enabled, skipping upload")
        return False

    try:
        if s3_key is None:
            s3_key = f"pdfs/{file_path.name}"

        s3_client.upload_file(
            str(file_path),
            AWS_S3_BUCKET,
            s3_key,
            ExtraArgs={"ContentType": "application/pdf"},
        )
        print(f"[S3] Successfully uploaded {file_path.name} to S3")
        return True
    except ClientError as e:
        print(f"[S3 ERROR] Failed to upload {file_path.name}: {e}")
        return False


def download_file_from_s3(s3_key: str, local_path: Path) -> bool:
    """
    Download a file from S3 to local path

    Args:
        s3_key: S3 object key
        local_path: Local path to save the file

    Returns:
        True if successful, False otherwise
    """
    if not is_s3_enabled():
        print("[S3] S3 not enabled, cannot download")
        return False

    try:
        s3_client.download_file(AWS_S3_BUCKET, s3_key, str(local_path))
        print(f"[S3] Successfully downloaded {s3_key} from S3")
        return True
    except ClientError as e:
        print(f"[S3 ERROR] Failed to download {s3_key}: {e}")
        return False


def list_s3_pdfs() -> List[str]:
    """
    List all PDF files in the S3 bucket

    Returns:
        List of PDF filenames (without the 'pdfs/' prefix)
    """
    if not is_s3_enabled():
        return []

    try:
        response = s3_client.list_objects_v2(Bucket=AWS_S3_BUCKET, Prefix="pdfs/")

        if "Contents" not in response:
            return []

        # Extract filenames without the 'pdfs/' prefix
        files = [
            obj["Key"].replace("pdfs/", "")
            for obj in response["Contents"]
            if obj["Key"].endswith(".pdf")
        ]
        return files
    except ClientError as e:
        print(f"[S3 ERROR] Failed to list PDFs: {e}")
        return []


def delete_file_from_s3(filename: str) -> bool:
    """
    Delete a file from S3

    Args:
        filename: Name of the file to delete

    Returns:
        True if successful, False otherwise
    """
    if not is_s3_enabled():
        print("[S3] S3 not enabled, cannot delete")
        return False

    try:
        s3_key = f"pdfs/{filename}"
        s3_client.delete_object(Bucket=AWS_S3_BUCKET, Key=s3_key)
        print(f"[S3] Successfully deleted {filename} from S3")
        return True
    except ClientError as e:
        print(f"[S3 ERROR] Failed to delete {filename}: {e}")
        return False


def get_s3_file_url(filename: str, expiration: int = 3600) -> Optional[str]:
    """
    Generate a presigned URL for accessing a file in S3

    Args:
        filename: Name of the file
        expiration: URL expiration time in seconds (default: 1 hour)

    Returns:
        Presigned URL or None if failed
    """
    if not is_s3_enabled():
        return None

    try:
        s3_key = f"pdfs/{filename}"
        url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": AWS_S3_BUCKET, "Key": s3_key},
            ExpiresIn=expiration,
        )
        return url
    except ClientError as e:
        print(f"[S3 ERROR] Failed to generate presigned URL for {filename}: {e}")
        return None


def download_s3_pdf_to_temp(filename: str) -> Optional[str]:
    """
    Download a PDF from S3 to a temporary file

    Args:
        filename: Name of the PDF file

    Returns:
        Path to temporary file or None if failed
    """
    if not is_s3_enabled():
        return None

    try:
        # Create a temporary file
        temp_file = tempfile.NamedTemporaryFile(
            delete=False, suffix=".pdf", prefix=f"s3_temp_{filename}_"
        )
        temp_path = Path(temp_file.name)
        temp_file.close()

        # Download from S3
        s3_key = f"pdfs/{filename}"
        if download_file_from_s3(s3_key, temp_path):
            return str(temp_path)
        else:
            # Clean up temp file if download failed
            if temp_path.exists():
                temp_path.unlink()
            return None
    except Exception as e:
        print(f"[S3 ERROR] Failed to download {filename} to temp: {e}")
        return None


def ensure_pdf_local(filename: str, local_dir: Path) -> Optional[Path]:
    """
    Ensure a PDF is available locally, downloading from S3 if necessary

    Args:
        filename: Name of the PDF file
        local_dir: Local directory to store the file

    Returns:
        Path to local file or None if not available
    """
    local_path = local_dir / filename

    # If file exists locally, return it
    if local_path.exists():
        return local_path

    # If S3 is enabled, try to download it
    if is_s3_enabled():
        s3_key = f"pdfs/{filename}"
        if download_file_from_s3(s3_key, local_path):
            return local_path

    return None
