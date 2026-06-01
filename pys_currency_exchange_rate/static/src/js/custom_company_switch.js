/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { SwitchCompanyMenu } from "@web/webclient/switch_company_menu/switch_company_menu";
import { useService } from "@web/core/utils/hooks";

patch(SwitchCompanyMenu.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
    },

    logIntoCompany() {
        if (this.isCompanyAllowed) {
            this.orm.call(
                "res.company",
                "call_auto_rate_sync",
                [this.props.company.id],
                {}
            );
        }
        return super.logIntoCompany(...arguments);
    },
});
