import os

from .errors import SecretStorageError
from .log_sanitizer import redact

try:
    from cryptography.fernet import Fernet, InvalidToken
except ImportError:  # pragma: no cover - deployment configuration error
    Fernet = None
    InvalidToken = Exception


class SecretStorage:
    ENV_MASTER_KEY = "SCE_CONNECT_MASTER_KEY"

    def __init__(self, master_key=None, environ=None):
        self._environ = environ if environ is not None else os.environ
        self._master_key = master_key or self._environ.get(self.ENV_MASTER_KEY)
        if not self._master_key:
            raise SecretStorageError(
                f"Falta la clave maestra {self.ENV_MASTER_KEY} en el entorno del proceso Odoo."
            )
        if Fernet is None:
            raise SecretStorageError(
                "La dependencia cryptography es obligatoria para SCE Connect."
            )
        try:
            self._cipher = Fernet(self._master_key.encode() if isinstance(self._master_key, str) else self._master_key)
        except (TypeError, ValueError) as error:
            raise SecretStorageError(
                f"La clave maestra {self.ENV_MASTER_KEY} tiene un formato inválido (debe ser una clave Fernet válida)."
            ) from error

    @classmethod
    def from_environment(cls):
        return cls()

    @staticmethod
    def generate_master_key():
        if Fernet is None:
            raise SecretStorageError("La dependencia cryptography es obligatoria para generar la clave maestra.")
        return Fernet.generate_key().decode()

    def encrypt(self, value):
        if value is None or value == "":
            raise SecretStorageError("No se puede cifrar un secreto vacío.")
        if not isinstance(value, str):
            value = str(value)
        return self._cipher.encrypt(value.encode()).decode()

    def decrypt(self, encrypted_value):
        if not encrypted_value:
            raise SecretStorageError("El secreto no existe o está vacío.")
        try:
            return self._cipher.decrypt(encrypted_value.encode()).decode()
        except (InvalidToken, UnicodeDecodeError, AttributeError) as error:
            raise SecretStorageError("No se pudo descifrar el secreto.") from error

    @staticmethod
    def mask(value):
        if not value:
            return ""
        return "*" * max(8, min(len(value), 32))

    @staticmethod
    def redact(value):
        return redact(value)
