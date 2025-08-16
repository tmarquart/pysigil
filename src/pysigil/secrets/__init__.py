from __future__ import annotations

import json
import logging
import os
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from ..errors import SigilSecretsError

logger = logging.getLogger("pysigil.secrets")


class SecretProvider(Protocol):
    """Protocol for secret providers."""

    def available(self) -> bool:
        """Return True if the provider can be used at runtime."""

    def can_write(self) -> bool:
        """Return True if the provider currently allows writes."""

    def get(self, dotted_key: str) -> str | None:
        """Return secret value if present or ``None``."""

    def set(self, dotted_key: str, value: str) -> None:
        """Store secret value or raise :class:`SigilSecretsError`."""


class SecretChain:
    """Chain multiple providers with precedence."""

    def __init__(self, providers: Sequence[SecretProvider]):
        self._providers = list(providers)

    def available(self) -> bool:
        return any(p.available() for p in self._providers)

    def can_write(self) -> bool:
        return any(p.available() and p.can_write() for p in self._providers)

    def get(self, dotted_key: str) -> str | None:
        for prov in self._providers:
            if not prov.available():
                logger.debug("provider %s unavailable", prov.__class__.__name__)
                continue
            val = prov.get(dotted_key)
            if val is not None:
                return val
        logger.debug("secret %s not found", dotted_key)
        return None

    def set(self, dotted_key: str, value: str) -> None:
        for prov in self._providers:
            if prov.available() and prov.can_write():
                prov.set(dotted_key, value)
                return
        raise SigilSecretsError("No write-capable secret provider")

    # convenience for CLI
    def unlock(self) -> None:
        for prov in self._providers:
            unlock = getattr(prov, "unlock", None)
            if callable(unlock):
                try:
                    unlock()
                except Exception as exc:  # pragma: no cover - defensive
                    logger.error("unlock failed: %s", exc)


class KeyringProvider:
    """Secrets stored via the system keyring."""

    def __init__(self, domain: str = "sigil") -> None:
        self.domain = domain
        try:
            import keyring  # type: ignore
            from keyring.backends import fail
            self._keyring = keyring
            self._fail = fail
        except Exception:  # pragma: no cover - keyring missing
            self._keyring = None
            self._fail = None

    def available(self) -> bool:
        if self._keyring is None:
            return False
        return not isinstance(self._keyring.get_keyring(), self._fail.Keyring)

    def can_write(self) -> bool:
        return self.available()

    def get(self, dotted_key: str) -> str | None:
        if not self.available():
            return None
        return self._keyring.get_password(self.domain, dotted_key)

    def set(self, dotted_key: str, value: str) -> None:
        if not self.available():
            raise SigilSecretsError("Keyring backend unavailable")
        self._keyring.set_password(self.domain, dotted_key, value)


class EnvSecretProvider:
    """Read-only provider using environment variables."""

    def __init__(self, app_name: str) -> None:
        self._prefix = f"SIGIL_SECRET_{app_name.upper().replace('-', '_')}_"

    def available(self) -> bool:  # pragma: no cover - trivial
        return True

    def can_write(self) -> bool:
        return False

    def get(self, dotted_key: str) -> str | None:
        env_key = self._prefix + dotted_key.replace(".", "_").upper()
        return os.environ.get(env_key)

    def set(self, dotted_key: str, value: str) -> None:
        raise SigilSecretsError("Environment provider is read-only")


class EncryptedFileProvider:
    """AES-GCM encrypted JSON file provider."""

    def __init__(
        self,
        path: Path | str | None,
        *,
        master_key: bytes | str | None = None,
        prompt: bool = True,
        required: bool = True,
    ) -> None:
        self.path = Path(path) if path else None
        self.prompt = prompt
        self.required = required
        self._password: bytes | None = None
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # noqa:F401
            self._have_crypto = True
        except Exception:  # pragma: no cover - cryptography missing
            self._have_crypto = False
        self._discover_password(master_key)

    # ----- basic helpers -----
    def available(self) -> bool:
        return bool(self._have_crypto and self.path and self.path.exists())

    def can_write(self) -> bool:
        return self.available() and self._password is not None

    # ----- discovery & unlocking -----
    def _discover_password(self, master_key: bytes | str | None) -> None:
        if not self._have_crypto:
            return
        password: bytes | None = None
        if master_key is not None:
            password = master_key if isinstance(master_key, bytes) else master_key.encode()
        elif os.environ.get("SIGIL_MASTER_PWD"):
            password = os.environ["SIGIL_MASTER_PWD"].encode()
        else:
            try:
                import keyring  # type: ignore

                val = keyring.get_password("sigil", f"master::{self.path}") if self.path else None
                if val:
                    password = val.encode()
            except Exception:  # pragma: no cover - keyring missing
                pass
        if password is None and self.prompt and os.isatty(0):  # pragma: no cover - interactive
            try:
                import getpass

                password = getpass.getpass("Master password: ").encode()
            except Exception:
                pass
        self._password = password

    def unlock(self) -> None:
        if self._password is None:
            self._discover_password(None)

    # ----- file helpers -----
    def _derive_key(self, salt: bytes) -> bytes:
        from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

        if self._password is None:
            raise SigilSecretsError("Vault locked")
        kdf = Scrypt(salt=salt, length=32, n=2 ** 15, r=8, p=1)
        return kdf.derive(self._password)

    def _decrypt_file(self) -> dict[str, str]:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        if not self.path:
            return {}
        raw = json.loads(self.path.read_text())
        salt = bytes.fromhex(raw["salt"])
        nonce = bytes.fromhex(raw["nonce"])
        cipher = bytes.fromhex(raw["cipher"])
        key = self._derive_key(salt)
        data = AESGCM(key).decrypt(nonce, cipher, None)
        return json.loads(data.decode())

    def _write_file(self, data: dict[str, str]) -> None:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        if not self.path:
            raise SigilSecretsError("No file path configured")
        salt = os.urandom(16)
        key = self._derive_key(salt)
        nonce = os.urandom(12)
        cipher = AESGCM(key).encrypt(nonce, json.dumps(data).encode(), None)
        obj = {
            "kdf": "scrypt",
            "salt": salt.hex(),
            "nonce": nonce.hex(),
            "cipher": cipher.hex(),
        }
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(obj), encoding="utf-8")
        tmp.replace(self.path)

    # ----- public API -----
    def get(self, dotted_key: str) -> str | None:
        if not self.available():
            return None
        if self._password is None:
            logger.debug("vault locked; cannot read %s", dotted_key)
            return None
        try:
            data = self._decrypt_file()
            return data.get(dotted_key)
        except Exception as exc:  # pragma: no cover - corruption
            logger.error("failed to decrypt vault: %s", exc)
            raise SigilSecretsError(str(exc)) from exc

    def set(self, dotted_key: str, value: str) -> None:
        if not self.available():
            raise SigilSecretsError("Vault unavailable")
        if self._password is None:
            logger.warning("vault locked when attempting write")
            raise SigilSecretsError("Vault locked")
        try:
            data = self._decrypt_file() if self.path.exists() else {}
            data[dotted_key] = value
            self._write_file(data)
        except SigilSecretsError:
            raise
        except Exception as exc:  # pragma: no cover - corruption
            logger.error("failed to write vault: %s", exc)
            raise SigilSecretsError(str(exc)) from exc


__all__ = [
    "SecretProvider",
    "SecretChain",
    "KeyringProvider",
    "EnvSecretProvider",
    "EncryptedFileProvider",
]
