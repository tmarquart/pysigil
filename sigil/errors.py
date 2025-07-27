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
