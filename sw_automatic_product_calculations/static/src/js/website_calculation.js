/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { jsonrpc } from "@web/core/network/rpc_service";

publicWidget.registry.SwWebsiteCalculation = publicWidget.Widget.extend({
    selector: ".o_sw_calc_box",
    events: {
        "click .o_sw_calc_add_to_cart": "_onClickCalculateAndAdd",
        "change .o_sw_calc_method": "_onChangeMethod",
    },

    start() {
        this._toggleHeightVisibility();
        return this._super(...arguments);
    },

    _getSelectedMethodType() {
        const methodSelect = this.el.querySelector(".o_sw_calc_method");
        if (!methodSelect) {
            return "m2";
        }
        const selected = methodSelect.options[methodSelect.selectedIndex];
        return selected?.dataset?.methodType || "m2";
    },

    _onChangeMethod() {
        this._toggleHeightVisibility();
    },

    _toggleHeightVisibility() {
        const methodType = this._getSelectedMethodType();
        const heightWrap = this.el.querySelector(".o_sw_calc_height_wrap");
        const totalLabel = this.el.querySelector(".o_sw_calc_total_label");
        if (totalLabel) {
            totalLabel.textContent = methodType === "m3" ? "Total m³" : "Total m²";
        }
        if (!heightWrap) {
            return;
        }
        if (methodType === "m3") {
            heightWrap.classList.remove("d-none");
        } else {
            heightWrap.classList.add("d-none");
        }
    },

    _showResult(message) {
        const result = this.el.querySelector(".o_sw_calc_result");
        const error = this.el.querySelector(".o_sw_calc_error");
        if (error) {
            error.classList.add("d-none");
            error.textContent = "";
        }
        if (result) {
            result.textContent = message;
            result.classList.remove("d-none");
        }
    },

    _showError(message) {
        const result = this.el.querySelector(".o_sw_calc_result");
        const error = this.el.querySelector(".o_sw_calc_error");
        if (result) {
            result.classList.add("d-none");
            result.textContent = "";
        }
        if (error) {
            error.textContent = message;
            error.classList.remove("d-none");
        }
    },

    async _onClickCalculateAndAdd(ev) {
        ev.preventDefault();

        const productTemplateId = parseInt(this.el.dataset.productTemplateId || "0", 10);
        const methodId = parseInt(this.el.querySelector(".o_sw_calc_method")?.value || "0", 10);
        const length = parseFloat(this.el.querySelector(".o_sw_calc_length")?.value || "0");
        const width = parseFloat(this.el.querySelector(".o_sw_calc_width")?.value || "0");
        const height = parseFloat(this.el.querySelector(".o_sw_calc_height")?.value || "0");
        const totalSurface = parseFloat(this.el.querySelector(".o_sw_calc_total_surface")?.value || "0");

        try {
            const response = await jsonrpc("/sw/calculation/add_to_cart", {
                product_template_id: productTemplateId,
                method_id: methodId,
                length,
                width,
                height,
                total_surface: totalSurface,
            });

            if (!response || !response.ok) {
                this._showError((response && response.message) || "No se pudo realizar el cálculo.");
                return;
            }

            const lines = (response.added_lines || [])
                .map((l) => `${l.product_name}: ${l.qty}`)
                .join(" | ");

            const message = `Total ${response.method_type}: ${response.total_surface}. Agregado al carrito. ${lines}`;
            this._showResult(message);

            window.location.reload();
        } catch (e) {
            this._showError("Error al comunicarse con el servidor.");
        }
    },
});

export default publicWidget.registry.SwWebsiteCalculation;