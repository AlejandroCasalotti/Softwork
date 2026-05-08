/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { rpc } from "@web/core/network/rpc";
import { PaymentForm } from '@payment/interactions/payment_form';

patch(PaymentForm.prototype, {
    async selectPaymentOption(ev) {
        let res = super.selectPaymentOption(ev);
        const checked_Radio = this.el.querySelector(
            'input[name="o_payment_radio"]:checked'
        );

        const pathParts = window.location.pathname.split("/");
        const orderId = pathParts[3] || "";

        this.paymentContext.providerId = this._getProviderId(checked_Radio);

        const amountView = document.querySelector('h2[data-id="total_amount"]');
        const vdamountBox = document.querySelector('b[data-id="total_amount"]');

        const el = document.querySelector("#o_payment_summary_reference");
        let sale_order_name = "";
        if (el) {
            sale_order_name = el.innerHTML.trim();
        }

        const data = await rpc("/update/order_line", {
            provider_id: this.paymentContext.providerId,
            sale_order_id: sale_order_name || "",
            orderId: orderId || "",
        });

        if (data && data.order) {
            const newAmount = data.order.amount_total;
            const currency = data.order.currency;

            if (vdamountBox) {
                vdamountBox.textContent = `${currency} ${newAmount.toFixed(2)}`;
                amountView.textContent = `${currency} ${newAmount.toFixed(2)}`;
            }

            const amountBox = document.querySelector('#o_payment_summary_amount');

            if (amountBox) {
                amountBox.textContent = `${currency} ${newAmount.toFixed(2)}`;
            }
            this._updateOrderLine(data);
        }

        if (checked_Radio) {
            document.querySelectorAll(".provider-charge").forEach(el => {
                el.classList.add("d-none");
            });

            const parent = checked_Radio.closest(".d-flex");
            if (parent) {
                const chargeBox = parent.querySelector(".provider-charge");
                if (chargeBox) {
                    chargeBox.classList.remove("d-none");
                    const formattedAmount = parseFloat(data.order.charged_amount).toFixed(2);
                    chargeBox.textContent = `+ ${data.order.currency} ${formattedAmount}`;
                }
            }
        }
        return res;
    },

    _updateOrderLine(result) {
        const tbody = document.querySelector(".o_cart_products_table tbody");
        if (!tbody) return;
        let html = "";

        for (const line of result.order.order_lines) {
            html += `
            <tr>
                <td class="td-img ps-0">
                    ${line.image_128
                    ? `<img src="data:image/png;base64,${line.image_128}" class="o_image_64_max img rounded" alt="${line.name_short}"/>`
                    : ""
                }
                </td>
                <td class="td-product_name td-qty w-100" name="website_sale_cart_summary_product_name">
                    <h6>
                        ${parseInt(line.product_uom_qty)} x ${line.name_short}
                    </h6>
                </td>
                <td class="#{o_cart_sum_padding_top} td-price pe-0 text-end w-100" name="website_sale_cart_summary_line_price">
                    <span style="margin-right: 3px;">${line.currency}</span><span>${line.price_subtotal}</span>
                </td>
            </tr>
            `;
        }

        const subtotal_amount_el = document.querySelector('[name="o_order_total_untaxed"] span.monetary_field');
        if (subtotal_amount_el && result.order.amount_untaxed !== undefined) {
            subtotal_amount_el.textContent = `${result.order.currency} ${result.order.amount_untaxed}`;
        }

        const total_amount_el = document.querySelector(".o_cart_total strong.monetary_field");
        if (total_amount_el && result.order.amount_total !== undefined) {
            total_amount_el.textContent = `${result.order.currency} ${result.order.amount_total}`;
            this.paymentContext.amount = result.order.amount_total
        }

        if (tbody && html) {
            tbody.innerHTML = html;
        }
    }
});
