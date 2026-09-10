import os

from odoo.exceptions import UserError

try:
    from cryptography.fernet import Fernet, MultiFernet
except ImportError:  # pragma: no cover - deployment configuration error
    Fernet = None
    MultiFernet = None


class CoreSecretService:
    """Encrypt provider credentials without coupling the ML connector to Connect."""

    KEYRING_ENV = "SCE_CORE_KEYRING"

    def __init__(self, keyring=None, environ=None):
        environ = environ if environ is not None else os.environ
        keyring = keyring or environ.get(self.KEYRING_ENV, "")
        keys = [key.strip() for key in keyring.split(",") if key.strip()]
        if not keys:
            raise UserError(
                "No hay keyring operativo para las credenciales de MercadoLibre."
            )
        if Fernet is None:
            raise UserError("La dependencia Python 'cryptography' es obligatoria.")
        try:
            self._cipher = MultiFernet([Fernet(key.encode()) for key in keys])
        except (TypeError, ValueError) as error:
            raise UserError("El keyring de credenciales de MercadoLibre no es válido.") from error

    @classmethod
    def from_runtime(cls):
        return cls()

    def encrypt(self, value):
        if not value:
            raise UserError("No se puede cifrar una credencial vacía.")
        return self._cipher.encrypt(str(value).encode()).decode()

    def decrypt(self, encrypted_value):
        if not encrypted_value:
            raise UserError("La credencial no está disponible.")
        try:
            return self._cipher.decrypt(encrypted_value.encode()).decode()
        except Exception as error:
            raise UserError("No se pudo descifrar la credencial de MercadoLibre.") from error