"""Custom errors for a JVC Projector."""


class JvcProjectorError(Exception):
    """Projector Error."""


class JvcProjectorConnectError(JvcProjectorError):
    """Projector Connect Timeout."""


class JvcProjectorCommandError(JvcProjectorError):
    """Projector Command Error."""


class JvcProjectorAuthError(JvcProjectorError):
    """Projector Password Invalid Error."""
