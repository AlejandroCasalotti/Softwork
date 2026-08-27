class SceConnectError(Exception):
    """Base error for SCE Connect services."""


class ConfigurationError(SceConnectError):
    pass


class AuthenticationError(SceConnectError):
    pass


class PermissionError(SceConnectError):
    pass


class DatabaseError(SceConnectError):
    pass


class NetworkError(SceConnectError):
    pass


class ApiError(SceConnectError):
    pass


class OperationBlocked(SceConnectError):
    pass


class SecretStorageError(SceConnectError):
    pass
