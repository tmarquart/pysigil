class SigilError(Exception):
    """Base class for Sigil errors."""


class UnknownScopeError(SigilError):
    pass


class SigilLoadError(SigilError):
    """Raised when a backend fails to parse its file."""


class SigilMetaError(SigilError):
    """Raised when preference metadata is malformed."""


class SigilWriteError(SigilError):
    """Raised when attempting to write and the target is read-only."""


class ReadOnlyScopeError(SigilError):
    """Raised when attempting to modify the read-only core scope."""


class SigilSecretsError(SigilError):
    """Raised for errors in the secrets subsystem."""


class UnknownProviderError(SigilError):
    """Raised when a provider is not registered."""


class DevLinkNotFound(SigilError):
    """Raised when a development link is missing."""


class DuplicateProviderError(SigilError):
    """Raised when attempting to create a provider that already exists."""


class ConflictError(SigilError):
    """Raised when concurrent modifications conflict."""


class UnknownFieldError(SigilError):
    """Raised when a field key is unknown."""


class DuplicateFieldError(SigilError):
    """Raised when attempting to add a field that already exists."""


class ValidationError(SigilError):
    """Raised when value validation fails."""


class PolicyError(SigilError):
    """Raised when policy prevents an operation."""


class IOFailureError(SigilError):
    """Raised for unexpected IO failures."""
