from __future__ import annotations

import sys
import types

from pysigil.secrets import EnvSecretProvider, KeyringProvider


def test_keyring_roundtrip(monkeypatch):
    store = {}

    class DummyKeyring:
        class Keyring:  # stand-in for fail.Keyring
            pass

    dummy = types.SimpleNamespace(
        get_keyring=lambda: DummyKeyring(),
        set_password=lambda dom, key, val: store.__setitem__((dom, key), val),
        get_password=lambda dom, key: store.get((dom, key)),
    )
    monkeypatch.setitem(sys.modules, "keyring", dummy)
    monkeypatch.setitem(sys.modules, "keyring.backends", types.SimpleNamespace(fail=DummyKeyring))

    p = KeyringProvider()
    assert p.available()
    p.set("secret.api", "val")
    assert p.get("secret.api") == "val"


def test_env_provider(monkeypatch):
    monkeypatch.setenv("SIGIL_SECRET_APP_SECRET_TOKEN", "abc")
    p = EnvSecretProvider("app")
    assert p.get("secret.token") == "abc"
    assert not p.can_write()


# @pytest.mark.skipif(not EncryptedFileProvider(Path("x"))._have_crypto, reason="cryptography missing")
# def test_encrypted_file_locked(tmp_path, monkeypatch):
#     path = tmp_path / "vault.enc.json"
#     p = EncryptedFileProvider(path, master_key="pw")
#     p.set("secret.token", "one")
#
#     locked = EncryptedFileProvider(path)
#     assert locked.get("secret.token") is None
#     with pytest.raises(SigilSecretsError):
#         locked.set("secret.token", "two")
#
#     monkeypatch.setenv("SIGIL_MASTER_PWD", "pw")
#     unlocked = EncryptedFileProvider(path, prompt=False)
#     assert unlocked.get("secret.token") == "one"
#     unlocked.set("secret.token", "two")
#     assert unlocked.get("secret.token") == "two"
#     monkeypatch.delenv("SIGIL_MASTER_PWD")

def test_secret_precedence_env_overrides_files(tmp_path, monkeypatch):
    user = tmp_path / "user.ini"
    user.write_text("[global]\nsecret.token=from_user\n")
    monkeypatch.setenv("SIGIL_SECRET_APP_SECRET_TOKEN", "from_env")
    from pysigil.core import Sigil

    s = Sigil("app", user_scope=user, project_scope=tmp_path / "p.ini")
    assert s.get_pref("secret.token") == "from_env"

