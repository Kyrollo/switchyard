from __future__ import annotations

import time
import uuid
from typing import Dict, List, Optional
from ..domain.entities import VirtualKey
from ..core.security import hash_api_key


class VirtualKeyManager:
    """Manages virtual API keys, token budgets, and access control."""

    def __init__(self) -> None:
        self._keys: Dict[str, VirtualKey] = {}
        self._hash_to_id: Dict[str, str] = {}
        self._init_default_key()

    def _init_default_key(self) -> None:
        default_raw = "sk_live_switchyard_enterprise_2026"
        key_hash = hash_api_key(default_raw)
        key = VirtualKey(
            id="key_default_admin",
            name="Primary Admin Virtual Key",
            key_prefix="sk_live_switchyard...",
            key_hash=key_hash,
            rpm_limit=1000,
            tpm_limit=200000,
            monthly_budget_usd=1000.0,
            budget_spent_usd=42.50,
            allowed_models=["*"],
            is_active=True,
        )
        self._keys[key.id] = key
        self._hash_to_id[key_hash] = key.id

    def create_key(
        self,
        name: str,
        rpm_limit: int = 600,
        tpm_limit: int = 100000,
        monthly_budget_usd: float = 500.0,
        allowed_models: Optional[List[str]] = None,
    ) -> tuple[VirtualKey, str]:
        raw_token = f"sk_live_{uuid.uuid4().hex}"
        key_hash = hash_api_key(raw_token)
        key_id = f"key_{uuid.uuid4().hex[:10]}"

        key = VirtualKey(
            id=key_id,
            name=name,
            key_prefix=f"{raw_token[:12]}...",
            key_hash=key_hash,
            rpm_limit=rpm_limit,
            tpm_limit=tpm_limit,
            monthly_budget_usd=monthly_budget_usd,
            budget_spent_usd=0.0,
            allowed_models=allowed_models or ["*"],
            is_active=True,
        )

        self._keys[key.id] = key
        self._hash_to_id[key_hash] = key.id
        return key, raw_token

    def get_by_hash(self, key_hash: str) -> Optional[VirtualKey]:
        key_id = self._hash_to_id.get(key_hash)
        if key_id:
            return self._keys.get(key_id)
        return None

    def list_keys(self) -> List[VirtualKey]:
        return list(self._keys.values())

    def revoke_key(self, key_id: str) -> bool:
        if key_id in self._keys:
            self._keys[key_id].is_active = False
            return True
        return False

    def record_spend(self, key_id: str, cost_usd: float) -> None:
        if key_id in self._keys:
            self._keys[key_id].budget_spent_usd = round(
                self._keys[key_id].budget_spent_usd + cost_usd, 4
            )


key_manager = VirtualKeyManager()
