class SigilError(Exception):
    """Base class for Sigil errors."""

class UnknownScopeError(SigilError):
    pass


class SigilLoadError(SigilError):
    """Raised when a backend fails to parse its file."""
    pass


class SigilMetaError(SigilError):
    """Raised when preference metadata is malformed."""
    pass


class SigilWriteError(SigilError):
    """Raised when attempting to write and the target is read-only."""
    pass


class ReadOnlyScopeError(SigilError):
    """Raised when attempting to modify the read-only core scope."""
    pass


class SigilSecretsError(SigilError):
    """Raised for errors in the secrets subsystem."""
    pass
