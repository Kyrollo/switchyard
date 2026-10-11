from __future__ import annotations

from typing import Any
from ..core.llm import llm_client


class BaseAIPipeline:
    """Base class for verified production AI pipelines."""
    def __init__(self) -> None:
        self.llm = llm_client

    async def execute(self, prompt: str, **kwargs: Any) -> str:
        messages = [{"role": "user", "content": prompt}]
        return await self.llm.complete(messages, **kwargs)
