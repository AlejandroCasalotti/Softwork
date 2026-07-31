/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.SwUomWebPackagingFilter = publicWidget.Widget.extend({
    selector: ".oe_website_sale",

    start() {
        const superDef = this._super(...arguments);
        this._applyPackagingFilter();
        this._bindReapplyHooks();
        return superDef;
    },

    _bindReapplyHooks() {
        // Reaplicar cuando Odoo recompone DOM por combinación/qty
        // Evitar múltiples bindings que pueden causar errores de restauración/controlador
        if (this._hooksBound) return;
        this._hooksBound = true;

        if (!this._reapplyFilterDebounced) {
            this._reapplyFilterDebounced = () => {
                clearTimeout(this._reapplyTimer);
                this._reapplyTimer = setTimeout(() => this._applyPackagingFilter(), 30);
            };
        }

        if (this._observer) {
            this._observer.disconnect();
        }
        this._observer = new MutationObserver(() => this._reapplyFilterDebounced());
        this._observer.observe(this.el, { childList: true, subtree: true });

        this.el.addEventListener("change", (ev) => {
            const t = ev.target;
            if (!t) return;
            if (["uom_id", "uom", "packaging_id", "add_qty", "quantity"].includes(t.name)) {
                this._reapplyFilterDebounced();
            }
        });
    },

    destroy() {
        if (this._observer) {
            this._observer.disconnect();
            this._observer = null;
        }
        clearTimeout(this._reapplyTimer);
        return this._super(...arguments);
    },

    _getAllowedIds() {
        const input =
            this.el.querySelector("input[name='sw_web_allowed_uom_ids']") ||
            this.el.querySelector("input[name='sw_web_allowed_packaging_ids']") ||
            this.el.querySelector("input[name='sw_web_allowed_uom_ids_fallback']") ||
            this.el.querySelector("input[name='sw_web_allowed_packaging_ids_fallback']");
        const raw = (input?.value || "").trim();
        if (!raw) return [];

        const ids = raw
            .split(",")
            .map((v) => parseInt(v.trim(), 10))
            .filter((n) => Number.isInteger(n) && n > 0);

        return [...new Set(ids)];
    },

    _isAllowed(id, allowedIds) {
        return Number.isInteger(id) && id > 0 && allowedIds.includes(id);
    },

    _parseCandidateId(node) {
        if (!node) return 0;

        const direct = parseInt(node.value || node.dataset?.value || "0", 10);
        if (Number.isInteger(direct) && direct > 0) return direct;

        const idAttrs = ["data-value_id", "data-value-id", "data-id", "value"];
        for (const attr of idAttrs) {
            const v = parseInt(node.getAttribute?.(attr) || "0", 10);
            if (Number.isInteger(v) && v > 0) return v;
        }

        const forAttr = node.getAttribute?.("for") || "";
        const m = forAttr.match(/-(\d+)(?:\D|$)/);
        if (m) {
            const fromFor = parseInt(m[1], 10);
            if (Number.isInteger(fromFor) && fromFor > 0) return fromFor;
        }

        return 0;
    },

    _restoreAllVisibility() {
        // Restaurar radios UoM
        const uomRadioNodes = this.el.querySelectorAll("input[type='radio'][name='uom_id']");
        uomRadioNodes.forEach((input) => {
            const container =
                input.closest("li.o_variant_pills, li, label, .form-check, .radio, .css_attribute_color, .js_attribute_value") ||
                input;
            container.classList.remove("d-none");
            container.removeAttribute("aria-hidden");
            input.disabled = false;
        });

        // Restaurar labels potencialmente ocultas
        const uomLabels = this.el.querySelectorAll("label[for*='uom'], label.js_attribute_value");
        uomLabels.forEach((label) => label.classList.remove("d-none"));

        // Restaurar inputs/selects de uom/packaging
        const packagingFields = this.el.querySelectorAll(
            "input[name='packaging_id'], select[name='packaging_id'], input[name='uom_id'], select[name='uom_id'], input[name='uom'], select[name='uom']"
        );
        packagingFields.forEach((field) => {
            const container = field.closest("label, .form-check, .radio, .o_variant_pills, .o_wsale_product_packaging_line") || field;
            container.classList.remove("d-none");
            if (field.tagName === "SELECT") {
                Array.from(field.options).forEach((opt) => {
                    opt.hidden = false;
                });
            }
        });
    },

    _getPriceLabelNode() {
        return this.el.querySelector("#sw_web_base_uom_price_label");
    },

    _formatCurrencyLikeVisible(priceNumber, referenceText) {
        if (!Number.isFinite(priceNumber)) return "";
        const normalizedRef = (referenceText || "").trim();
        let decimals = 2;
        if (normalizedRef.includes(",")) {
            const split = normalizedRef.split(",");
            if (split.length > 1) decimals = Math.min(Math.max(split[1].replace(/\D/g, "").length, 0), 4);
        }
        const locale = "es-AR";
        const formatter = new Intl.NumberFormat(locale, {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals,
        });
        return `$ ${formatter.format(priceNumber)}`;
    },

    _extractVisiblePriceValue() {
        const priceNode =
            this.el.querySelector(".oe_price .oe_currency_value") ||
            this.el.querySelector(".oe_website_sale .oe_currency_value") ||
            this.el.querySelector(".product_price .oe_currency_value") ||
            this.el.querySelector(".product_price .text-nowrap");

        if (!priceNode) return { value: NaN, text: "" };
        const txt = (priceNode.textContent || "").trim();
        if (!txt) return { value: NaN, text: "" };

        const normalized = txt
            .replace(/\s/g, "")
            .replace(/\./g, "")
            .replace(",", ".")
            .replace(/[^\d.-]/g, "");

        return { value: parseFloat(normalized), text: txt };
    },

    _getSelectedUomRatio() {
        const selectedRadio = this.el.querySelector("input[type='radio'][name='uom_id']:checked");
        if (!selectedRadio) return 1.0;

        const candidateNodes = [
            selectedRadio,
            selectedRadio.closest("li"),
            selectedRadio.closest("label"),
        ].filter(Boolean);

        for (const node of candidateNodes) {
            const attrs = ["data-sw-ratio", "data-ratio", "data-uom-ratio", "data-factor"];
            for (const attr of attrs) {
                const raw = node.getAttribute?.(attr);
                if (raw) {
                    const v = parseFloat(String(raw).replace(",", "."));
                    if (Number.isFinite(v) && v > 0) return v;
                }
            }
        }

        // fallback: si no hay ratio disponible, no romper cálculo
        return 1.0;
    },

    _renderBaseUomPriceInfo() {
        const labelNode = this._getPriceLabelNode();
        if (!labelNode) return;

        const enabled = (this.el.querySelector("input[name='sw_web_show_base_uom_price']")?.value || "0") === "1";
        const baseUomName = (this.el.querySelector("input[name='sw_web_base_uom_name']")?.value || "").trim();

        if (!enabled || !baseUomName) {
            labelNode.classList.add("d-none");
            labelNode.textContent = "";
            return;
        }

        const { value: visiblePrice, text: visibleText } = this._extractVisiblePriceValue();
        const ratio = this._getSelectedUomRatio();

        if (!Number.isFinite(visiblePrice) || !(ratio > 0)) {
            labelNode.classList.add("d-none");
            labelNode.textContent = "";
            return;
        }

        const basePrice = visiblePrice / ratio;
        const formatted = this._formatCurrencyLikeVisible(basePrice, visibleText);
        if (!formatted) {
            labelNode.classList.add("d-none");
            labelNode.textContent = "";
            return;
        }

        labelNode.textContent = `El precio por ${baseUomName} es de ${formatted}`;
        labelNode.classList.remove("d-none");
    },

    _applyPackagingFilter() {
        const allowedIds = this._getAllowedIds();
        if (!allowedIds.length) {
            // Sin selección => comportamiento estándar (mostrar todos)
            this._restoreAllVisibility();
            this._renderBaseUomPriceInfo();
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

        // Filtro robusto de pills/radios UoM aun si cambia estructura de website_sale
        const uomRadioNodes = this.el.querySelectorAll("input[type='radio'][name='uom_id']");
        uomRadioNodes.forEach((input) => {
            const id = this._parseCandidateId(input);
            const container =
                input.closest("li.o_variant_pills, li, label, .form-check, .radio, .css_attribute_color, .js_attribute_value") ||
                input;

            if (this._isAllowed(id, allowedIds)) {
                container.classList.remove("d-none");
                container.removeAttribute("aria-hidden");
                input.disabled = false;
            } else if (id) {
                container.classList.add("d-none");
                container.setAttribute("aria-hidden", "true");
                input.disabled = true;
                input.checked = false;
            }
        });

        // También ocultar labels de UoM que no estén permitidas aunque no envuelvan al input
        const uomLabels = this.el.querySelectorAll("label[for*='uom'], label.js_attribute_value");
        uomLabels.forEach((label) => {
            const id = this._parseCandidateId(label);
            if (!id) return;
            if (this._isAllowed(id, allowedIds)) {
                label.classList.remove("d-none");
            } else {
                label.classList.add("d-none");
            }
        });

        // Garantizar selección válida visible
        const checked = this.el.querySelector("input[type='radio'][name='uom_id']:checked");
        if (!checked || !this._isAllowed(this._parseCandidateId(checked), allowedIds)) {
            const firstAllowed = Array.from(this.el.querySelectorAll("input[type='radio'][name='uom_id']"))
                .find((node) => this._isAllowed(this._parseCandidateId(node), allowedIds) && !node.disabled);
            if (firstAllowed) {
                firstAllowed.checked = true;
                firstAllowed.dispatchEvent(new Event("change", { bubbles: true }));
            }
        }

        this._renderBaseUomPriceInfo();
    },
});