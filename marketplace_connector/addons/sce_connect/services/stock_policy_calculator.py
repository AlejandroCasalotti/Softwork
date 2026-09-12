from decimal import Decimal, InvalidOperation, ROUND_FLOOR

from odoo.exceptions import ValidationError


class StockPolicyCalculator:
    @staticmethod
    def _decimal(value):
        try:
            result = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError) as error:
            raise ValidationError("La configuración de reserva debe ser numérica.") from error
        if not result.is_finite():
            raise ValidationError("La configuración de reserva debe ser finita.")
        return result

    @classmethod
    def calculate(cls, source_stock, reserve_type, reserve_value):
        stock = cls._decimal(source_stock)
        if stock < 0:
            stock = Decimal("0")
        reserve = cls._decimal(reserve_value or 0)
        if reserve < 0:
            raise ValidationError("La reserva de stock no puede ser negativa.")
        if reserve_type == "none":
            reserve = Decimal("0")
        elif reserve_type == "fixed":
            pass
        elif reserve_type == "percent":
            if reserve > 100:
                raise ValidationError("La reserva porcentual no puede superar el 100%.")
            reserve = stock * reserve / Decimal("100")
        else:
            raise ValidationError("El tipo de reserva no está soportado.")
        return max(Decimal("0"), (stock - reserve).to_integral_value(rounding=ROUND_FLOOR))