import uuid

from supabase import create_client

from app.config import settings

_client = None


def get_client():
    global _client
    if _client is None:
        _client = create_client(settings.supabase_url, settings.supabase_service_key)
    return _client


def upload_image(file_bytes: bytes, filename: str, content_type: str) -> str:
    """Uploads an image to the configured Supabase storage bucket and returns its public URL."""
    ext = filename.rsplit(".", 1)[-1] if "." in filename else "jpg"
    key = f"{uuid.uuid4().hex}.{ext}"

    client = get_client()
    client.storage.from_(settings.supabase_image_bucket).upload(
        key, file_bytes, {"content-type": content_type}
    )
    return client.storage.from_(settings.supabase_image_bucket).get_public_url(key)
