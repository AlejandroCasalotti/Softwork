from decimal import Decimal, InvalidOperation, ROUND_DOWN, ROUND_HALF_UP

from odoo.exceptions import ValidationError


class PricePolicyCalculator:
    PRECISION = Decimal("0.01")

    @staticmethod
    def _decimal(value, label):
        try:
            result = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError) as error:
            raise ValidationError("%s debe ser numérico." % label) from error
        if not result.is_finite():
            raise ValidationError("%s debe ser finito." % label)
        return result

    @classmethod
    def calculate(
        cls,
        base_price,
        adjustment_percent=0,
        adjustment_fixed=0,
        commercial_rounding="none",
        safety_enabled=False,
        max_decrease_percent=20,
        previous_price=None,
    ):
        price = cls._decimal(base_price, "El precio base")
        if price <= 0:
            raise ValidationError("El precio base debe ser mayor que cero.")
        percent = cls._decimal(adjustment_percent, "El ajuste porcentual")
        fixed = cls._decimal(adjustment_fixed, "El ajuste fijo")
        price = price * (Decimal("1") + percent / Decimal("100")) + fixed
        if commercial_rounding not in {"none", "10", "100", "1000"}:
            raise ValidationError("El redondeo comercial no está soportado.")
        if commercial_rounding != "none":
            quantum = Decimal(commercial_rounding)
            price = (price / quantum).to_integral_value(rounding=ROUND_DOWN) * quantum
        price = price.quantize(cls.PRECISION, rounding=ROUND_HALF_UP)
        if price <= 0:
            raise ValidationError("Los ajustes producen un precio no válido.")
        blocked = False
        if safety_enabled and previous_price not in (None, False, ""):
            previous = cls._decimal(previous_price, "El precio anterior")
            decrease = cls._decimal(max_decrease_percent, "La baja máxima permitida")
            if previous <= 0 or decrease < 0 or decrease > 100:
                raise ValidationError("La configuración de protección de precio no es válida.")
            minimum = previous * (Decimal("1") - decrease / Decimal("100"))
            blocked = price < minimum
        return {
            "price": price,
            "blocked": blocked,
            "previous_price": previous_price,
        }