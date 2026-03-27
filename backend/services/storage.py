import os
import logging
from google.cloud import storage
from backend.config import DATA_DIR, MASTER_CSV, POSITIONS_CSV, TRADELOG_CSV

logger = logging.getLogger(__name__)

BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME", "stockscreener-data")

def get_storage_client():
    try:
        return storage.Client()
    except Exception as e:
        logger.error(f"[GCS] Failed to create storage client: {e}")
        return None

def download_from_gcs(filename: str):
    """Download a file from GCS to local data directory."""
    client = get_storage_client()
    if not client: return
    
    try:
        bucket = client.bucket(BUCKET_NAME)
        blob = bucket.blob(filename)
        if blob.exists():
            local_path = DATA_DIR / filename
            blob.download_to_filename(str(local_path))
            logger.info(f"[GCS] Downloaded {filename} to {local_path}")
        else:
            logger.info(f"[GCS] {filename} does not exist in bucket yet.")
    except Exception as e:
        logger.error(f"[GCS] Download error for {filename}: {e}")

def upload_to_gcs(filename: str):
    """Upload a local file to GCS."""
    client = get_storage_client()
    if not client: return
    
    try:
        local_path = DATA_DIR / filename
        if not local_path.exists():
            logger.warning(f"[GCS] Local file {local_path} not found for upload.")
            return
            
        bucket = client.bucket(BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_filename(str(local_path))
        logger.info(f"[GCS] Uploaded {filename} to gs://{BUCKET_NAME}")
    except Exception as e:
        logger.error(f"[GCS] Upload error for {filename}: {e}")

def sync_all_from_gcs():
    """Sync all required CSV files from GCS at startup."""
    for f in ["master.csv", "positions.csv", "tradelog.csv"]:
        download_from_gcs(f)
