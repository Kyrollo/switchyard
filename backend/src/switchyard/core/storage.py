from __future__ import annotations

class StorageService:
    """S3-compatible local/cloud blob storage interface."""
    def __init__(self) -> None:
        pass

    async def put_object(self, key: str, data: bytes, content_type: str) -> str:
        return f"/storage/{key}"
