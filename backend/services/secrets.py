"""
Google Secret Manager Service

Fetches secret values from Google Cloud Run environment.
"""

import os
import json
from google.cloud import secretmanager

def get_secret(secret_id: str, version_id: str = "latest") -> str:
    """
    Fetch secret value from Google Secret Manager.
    
    The service account running Cloud Run must have 
    'Secret Manager Secret Accessor' role.
    """
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        # Fallback for dev/local or if env not set
        return ""

    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
    
    try:
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        print(f"[Secrets] Error fetching secret {secret_id}: {e}")
        return ""

def update_config_secret(new_config: dict) -> bool:
    """
    Update the 'APP_CONFIG' secret in Google Secret Manager 
    with a new version (e.g. after updating an access token).
    """
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        return False

    client = secretmanager.SecretManagerServiceClient()
    parent = client.secret_path(project_id, "APP_CONFIG")
    
    payload = json.dumps(new_config).encode("UTF-8")
    
    try:
        client.add_secret_version(
            request={"parent": parent, "payload": { "data": payload }}
        )
        return True
    except Exception as e:
        print(f"[Secrets] Error updating secret 'APP_CONFIG': {e}")
        return False

def get_config_from_secrets() -> dict:
    """
    Fetch the entire config JSON from a single secret named 'APP_CONFIG'.
    Returns a dict that mirrors config.yaml.
    """
    raw = get_secret("APP_CONFIG")
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}
