/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.SwUomWebPackagingFilter = publicWidget.Widget.extend({
    selector: ".oe_website_sale",

    start() {
        this._applyPackagingFilter();
        return this._super(...arguments);
    },

    _getAllowedIds() {
        const input = this.el.querySelector("input[name='sw_web_allowed_packaging_ids']");
        const raw = (input?.value || "").trim();
        if (!raw) return [];
        return raw
            .split(",")
            .map((v) => parseInt(v.trim(), 10))
            .filter((n) => Number.isInteger(n) && n > 0);
    },

    _applyPackagingFilter() {
        const allowedIds = this._getAllowedIds();
        if (!allowedIds.length) {
            // Sin selección => comportamiento estándar (mostrar todos)
            return;
        }

        // Soporta distintos nombres según implementación de web/UoM
        const packagingFields = this.el.querySelectorAll(
            "input[name='packaging_id'], select[name='packaging_id'], input[name='uom_id'], select[name='uom_id'], input[name='uom'], select[name='uom']"
        );

        packagingFields.forEach((field) => {
            if (field.tagName === "SELECT") {
                Array.from(field.options).forEach((opt) => {
                    const id = parseInt(opt.value || "0", 10);
                    if (id && !allowedIds.includes(id)) {
                        opt.hidden = true;
                    }
                });

                // Si el valor actual no está permitido, seleccionar primero válido
                const current = parseInt(field.value || "0", 10);
                if (current && !allowedIds.includes(current)) {
                    const firstAllowed = Array.from(field.options).find((opt) =>
                        allowedIds.includes(parseInt(opt.value || "0", 10))
                    );
                    if (firstAllowed) {
                        field.value = firstAllowed.value;
                        field.dispatchEvent(new Event("change", { bubbles: true }));
                    }
                }
            } else {
                const id = parseInt(field.value || "0", 10);
                const container = field.closest("label, .form-check, .radio, .o_variant_pills, .o_wsale_product_packaging_line") || field;
                if (id && !allowedIds.includes(id)) {
                    container.classList.add("d-none");
                }
            }
        });
    },
});