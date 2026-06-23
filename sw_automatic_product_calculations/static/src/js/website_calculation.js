/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.SwWebsiteCalculation = publicWidget.Widget.extend({
    selector: ".o_sw_calc_box",
    events: {
        "click .o_sw_calc_preview": "_onClickPreview",
        "click .o_sw_calc_add_to_cart": "_onClickAddToCart",
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

    _clearMessages() {
        const result = this.el.querySelector(".o_sw_calc_result");
        const error = this.el.querySelector(".o_sw_calc_error");
        if (result) {
            result.classList.add("d-none");
            result.textContent = "";
        }
        if (error) {
            error.classList.add("d-none");
            error.textContent = "";
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

    _collectPayload() {
        const productTemplateId = parseInt(this.el.dataset.productTemplateId || "0", 10);
        const methodId = parseInt(this.el.querySelector(".o_sw_calc_method")?.value || "0", 10);
        const length = parseFloat(this.el.querySelector(".o_sw_calc_length")?.value || "0");
        const width = parseFloat(this.el.querySelector(".o_sw_calc_width")?.value || "0");
        const height = parseFloat(this.el.querySelector(".o_sw_calc_height")?.value || "0");
        const totalSurface = parseFloat(this.el.querySelector(".o_sw_calc_total_surface")?.value || "0");
        return {
            product_template_id: productTemplateId,
            method_id: methodId,
            length,
            width,
            height,
            total_surface: totalSurface,
        };
    },

    _renderLines(lines) {
        const wrap = this.el.querySelector(".o_sw_calc_lines_wrap");
        const body = this.el.querySelector(".o_sw_calc_lines_body");
        const addBtn = this.el.querySelector(".o_sw_calc_add_to_cart");
        if (!wrap || !body || !addBtn) {
            return;
        }

        body.innerHTML = "";
        for (const line of lines || []) {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td>
                    <div class="d-flex align-items-center gap-2">
                        <img src="${line.product_image_url || ""}" alt="${line.product_name || ""}" class="o_sw_calc_product_thumb"/>
                        <div>
                            ${line.product_name}
                            <input type="hidden" class="o_sw_line_product_id" value="${line.product_id}"/>
                        </div>
                    </div>
                </td>
                <td>
                    <input type="number" step="0.01" min="0" class="form-control form-control-sm o_sw_line_qty" value="${line.qty}"/>
                </td>
            `;
            body.appendChild(tr);
        }

        wrap.classList.remove("d-none");
        addBtn.classList.remove("d-none");
    },

    _getEditedLines() {
        const rows = this.el.querySelectorAll(".o_sw_calc_lines_body tr");
        const lines = [];
        rows.forEach((row) => {
            const productId = parseInt(row.querySelector(".o_sw_line_product_id")?.value || "0", 10);
            const qty = parseFloat(row.querySelector(".o_sw_line_qty")?.value || "0");
            if (productId > 0 && qty > 0) {
                lines.push({ product_id: productId, qty });
            }
        });
        return lines;
    },

    async _onClickPreview(ev) {
        ev.preventDefault();
        this._clearMessages();

        try {
            const response = await rpc("/sw/calculation/preview", this._collectPayload());
            if (!response || !response.ok) {
                this._showError((response && response.message) || "No se pudo realizar el cálculo.");
                return;
            }

            this._renderLines(response.added_lines || []);
            this._showResult(`Total ${response.method_type}: ${response.total_surface}. Revisá y ajustá cantidades antes de agregar.`);
        } catch (e) {
            this._showError("Error al comunicarse con el servidor.");
        }
    },

    async _onClickAddToCart(ev) {
        ev.preventDefault();
        this._clearMessages();

        const payload = this._collectPayload();
        payload.lines = this._getEditedLines();

        try {
            const response = await rpc("/sw/calculation/add_to_cart", payload);
            if (!response || !response.ok) {
                this._showError((response && response.message) || "No se pudo agregar al carrito.");
                return;
            }

            this._showResult("Productos agregados al carrito.");
            window.location.reload();
        } catch (e) {
            const debugMessage = (e && (e.message || e.toString())) || "Error desconocido.";
            this._showError(`Error al comunicarse con el servidor. ${debugMessage}`);
        }
    },
});

export default publicWidget.registry.SwWebsiteCalculation;