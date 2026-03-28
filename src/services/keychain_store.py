from __future__ import annotations

import sys
from typing import Optional

from src.services.credential_store import CredentialStore

_SERVICE_NAME = "lightnovel-pydownloader"


class KeychainStore(CredentialStore):
    def __init__(self):
        self._keyring = None
        self._keyring_errors = ()
        self._loaded = False

    def is_available(self) -> bool:
        if sys.platform != "darwin":
            return False
        if not self._load_backend():
            return False
        backend = self._keyring.get_keyring()
        if backend.__class__.__name__ == "FailKeyring":
            return False
        try:
            self._keyring.get_password(
                _SERVICE_NAME,
                self._credential_key("_availability_probe", "_availability_probe"),
            )
        except self._keyring_errors:
            return False
        return True

    def load_password(self, site: str, account: str) -> Optional[str]:
        if not self.is_available() or not account:
            return None
        try:
            return self._keyring.get_password(_SERVICE_NAME, self._credential_key(site, account))
        except self._keyring_errors:
            return None

    def save_password(self, site: str, account: str, password: str) -> bool:
        if not self.is_available() or not account:
            return False
        try:
            self._keyring.set_password(_SERVICE_NAME, self._credential_key(site, account), password)
            return True
        except self._keyring_errors:
            return False

    def delete_password(self, site: str, account: str) -> bool:
        if not self.is_available() or not account:
            return False
        try:
            self._keyring.delete_password(_SERVICE_NAME, self._credential_key(site, account))
            return True
        except self._keyring_errors:
            return False

    def _load_backend(self) -> bool:
        if self._loaded:
            return self._keyring is not None
        self._loaded = True
        try:
            import keyring
            from keyring.errors import KeyringError, PasswordDeleteError
        except Exception:
            self._keyring = None
            self._keyring_errors = ()
            return False
        self._keyring = keyring
        self._keyring_errors = (KeyringError, PasswordDeleteError)
        return True

    def _credential_key(self, site: str, account: str) -> str:
        return f"{site}:{account}"
