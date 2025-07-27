# Storing Secrets

Sigil can store sensitive values in a dedicated secrets chain. By default it tries the
operating system keyring first, then an encrypted JSON file, and finally
environment variables prefixed with `SIGIL_SECRET_<APP>_`.

## Quick start

Install the extras and set a secret value:

```bash
pip install sigil[secrets-crypto]
sigil secret set secret.api_key mysecret --app myapp
```

Retrieve it later:

```bash
sigil secret get secret.api_key --app myapp --reveal
```

## CI usage

For headless environments define the value directly:

```bash
export SIGIL_SECRET_MYAPP_SECRET_API_KEY=mysecret
```

If using an encrypted file provider you can unlock via `SIGIL_MASTER_PWD`.

## Encrypted vault workflow

An encrypted vault lives beside your normal settings file with a `.enc.json`
suffix. Unlock it by running:

```bash
sigil secret unlock --app myapp
```

Rotate or change the master key by writing a new secret after unlocking.

```
```

| Provider        | Security Level |
|-----------------|----------------|
| Keyring         | High           |
| Encrypted file  | Medium         |
| Environment var | Low            |
|
