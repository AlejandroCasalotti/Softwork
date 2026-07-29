/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.SwUomWebPackagingFilter = publicWidget.Widget.extend({
    selector: ".oe_website_sale",

    start() {
        this._applyPackagingFilter();
        this._bindReapplyHooks();
        return this._super(...arguments);
    },

    _bindReapplyHooks() {
        // Reaplicar cuando Odoo recompone DOM por combinación/qty
        if (this._observer) {
            this._observer.disconnect();
        }
        this._observer = new MutationObserver(() => this._applyPackagingFilter());
        this._observer.observe(this.el, { childList: true, subtree: true });

        this.el.addEventListener("change", (ev) => {
            const t = ev.target;
            if (!t) return;
            if (["uom_id", "uom", "packaging_id", "add_qty", "quantity"].includes(t.name)) {
                setTimeout(() => this._applyPackagingFilter(), 0);
            }
        });
    },

    _getAllowedIds() {
        const input =
            this.el.querySelector("input[name='sw_web_allowed_uom_ids']") ||
            this.el.querySelector("input[name='sw_web_allowed_packaging_ids']");
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

        // Selectores posibles para UoM/embalaje visibles
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

        // Filtro exacto para tu HTML: <li class="o_variant_pills ..."><input type="radio" name="uom_id" value="..">
        const uomPills = this.el.querySelectorAll("li.o_variant_pills input[type='radio'][name='uom_id']");
        uomPills.forEach((input) => {
            const id = parseInt(input.value || "0", 10);
            const li = input.closest("li.o_variant_pills");
            if (!li || !id) return;

            if (allowedIds.includes(id)) {
                li.classList.remove("d-none");
                li.removeAttribute("aria-hidden");
                input.disabled = false;
            } else {
                li.classList.add("d-none");
                li.setAttribute("aria-hidden", "true");
                input.disabled = true;
                input.checked = false;
            }
        });

        // Garantizar selección válida visible
        const checked = this.el.querySelector("li.o_variant_pills input[type='radio'][name='uom_id']:checked");
        if (!checked || !allowedIds.includes(parseInt(checked.value || "0", 10))) {
            const firstAllowed = this.el.querySelector(
                "li.o_variant_pills:not(.d-none) input[type='radio'][name='uom_id']"
            );
            if (firstAllowed) {
                firstAllowed.checked = true;
                firstAllowed.dispatchEvent(new Event("change", { bubbles: true }));
            }
        }
    },
});