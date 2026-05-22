import uuid
from typing import BinaryIO

import httpx

from app.config import settings


async def upload_to_cloudinary(
    file: BinaryIO,
    folder: str,
    filename: str | None = None
) -> str:
    """
    Upload a file to Cloudinary and return the secure_url.
    
    Args:
        file: File-like object (from FastAPI UploadFile.file)
        folder: Cloudinary folder path (e.g. "kastra/{org_id}/projects/{project_id}")
        filename: Optional custom filename (defaults to UUID)
    
    Returns:
        Cloudinary secure_url (HTTPS CDN link)
    """
    if not settings.cloudinary_cloud_name or not settings.cloudinary_api_key or not settings.cloudinary_api_secret:
        raise ValueError("Cloudinary credentials not configured")
    
    public_id = filename or str(uuid.uuid4())
    
    # Cloudinary unsigned upload endpoint
    url = f"https://api.cloudinary.com/v1_1/{settings.cloudinary_cloud_name}/image/upload"
    
    # Generate signature for authenticated upload
    import hashlib
    import time
    timestamp = int(time.time())
    
    # Signature params (alphabetically sorted, excluding file and api_key)
    params_to_sign = f"folder={folder}&public_id={public_id}&timestamp={timestamp}{settings.cloudinary_api_secret}"
    signature = hashlib.sha1(params_to_sign.encode()).hexdigest()
    
    form_data = {
        "file": file,
        "folder": folder,
        "public_id": public_id,
        "timestamp": str(timestamp),
        "api_key": settings.cloudinary_api_key,
        "signature": signature,
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, files={"file": file}, data={
            k: v for k, v in form_data.items() if k != "file"
        })
        response.raise_for_status()
        data = response.json()
        return data["secure_url"]


async def delete_from_cloudinary(public_id: str) -> bool:
    """
    Delete a file from Cloudinary by its public_id.
    
    Args:
        public_id: The Cloudinary public_id (extracted from URL)
    
    Returns:
        True if deleted successfully
    """
    if not settings.cloudinary_cloud_name or not settings.cloudinary_api_key or not settings.cloudinary_api_secret:
        return False
    
    url = f"https://api.cloudinary.com/v1_1/{settings.cloudinary_cloud_name}/image/destroy"
    
    import hashlib
    import time
    timestamp = int(time.time())
    
    params_to_sign = f"public_id={public_id}&timestamp={timestamp}{settings.cloudinary_api_secret}"
    signature = hashlib.sha1(params_to_sign.encode()).hexdigest()
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, data={
            "public_id": public_id,
            "timestamp": str(timestamp),
            "api_key": settings.cloudinary_api_key,
            "signature": signature,
        })
        return response.status_code == 200
