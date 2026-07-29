/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.SwUomWeb = publicWidget.Widget.extend({
    selector: ".oe_website_sale",
    events: {
        "change form.o_wsale_product_form input[name='add_qty']": "_onQtyChange",
        "click form.o_wsale_product_form .js_add_cart_json": "_onBeforeAddToCart",
        "click form.o_wsale_product_form .o_we_buy_now": "_onBeforeAddToCart",
    },

    start() {
        this._refreshAll();
        return this._super(...arguments);
    },

    _getForm() {
        return this.el.querySelector("form.o_wsale_product_form");
    },

    _isEnabled(form) {
        if (!form) return false;
        const flag = form.querySelector("input[name='sw_web_uom_sale_mode']");
        return !!(flag && Number(flag.value || 0) === 1);
    },

    _toFloat(v, d = 0.0) {
        const n = Number(v);
        return Number.isFinite(n) ? n : d;
    },

    _getQtyData(form) {
        const addQty = this._toFloat(form.querySelector("input[name='add_qty']")?.value, 1.0);
        const minQty = this._toFloat(form.querySelector("input[name='sw_web_min_sale_qty']")?.value, 0.0);
        return { addQty, minQty };
    },

    _refreshAll() {
        const form = this._getForm();
        if (!this._isEnabled(form)) return;
        this._updateBuyingTotal(form);
        this._applyUomLabel(form);
        this._forceUomInForm(form);
    },

    _applyUomLabel(form) {
        const uomName = form.querySelector("input[name='sw_web_sale_uom_name']")?.value || "";
        if (!uomName) return;
        let label = form.querySelector(".sw_uom_web_qty_label");
        const qtyWrapper = form.querySelector(".css_quantity");
        if (!qtyWrapper) return;
        if (!label) {
            label = document.createElement("span");
            label.className = "sw_uom_web_qty_label me-2";
            qtyWrapper.parentNode.insertBefore(label, qtyWrapper);
        }
        label.textContent = `${uomName}:`;
    },

    _updateBuyingTotal(form) {
        const totalNode = this.el.querySelector(".sw_uom_web_total_qty");
        const baseUomNode = this.el.querySelector(".sw_uom_web_base_uom");
        if (!totalNode) return;

        const { addQty, minQty } = this._getQtyData(form);
        const totalBase = addQty * minQty;
        totalNode.textContent = totalBase.toFixed(2);

        const baseUom = form.querySelector("input[name='sw_web_base_uom_name']")?.value || "";
        if (baseUomNode && baseUom) {
            baseUomNode.textContent = baseUom;
        }
    },

    _forceUomInForm(form) {
        const uomId = parseInt(form.querySelector("input[name='sw_web_sale_uom_id']")?.value || "0", 10);
        if (!uomId) return;

        let uomInput = form.querySelector("input[name='uom_id']");
        if (!uomInput) {
            uomInput = document.createElement("input");
            uomInput.type = "hidden";
            uomInput.name = "uom_id";
            form.appendChild(uomInput);
        }
        uomInput.value = String(uomId);
    },

    _onQtyChange(ev) {
        const form = ev.currentTarget.closest("form.o_wsale_product_form");
        if (!this._isEnabled(form)) return;
        this._updateBuyingTotal(form);
        this._forceUomInForm(form);
    },

    _onBeforeAddToCart(ev) {
        const form = ev.currentTarget.closest("form.o_wsale_product_form");
        if (!this._isEnabled(form)) return;
        this._forceUomInForm(form);
    },
});