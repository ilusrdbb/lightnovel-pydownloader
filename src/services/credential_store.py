from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class CredentialStore(ABC):
    @abstractmethod
    def is_available(self) -> bool:
        pass

    @abstractmethod
    def load_password(self, site: str, account: str) -> Optional[str]:
        pass

    @abstractmethod
    def save_password(self, site: str, account: str, password: str) -> bool:
        pass

    @abstractmethod
    def delete_password(self, site: str, account: str) -> bool:
        pass
