/** @odoo-module **/

import { registry } from "@web/core/registry";

const oauthResultListener = {
    dependencies: ["notification"],
    start(env, { notification }) {
        const handler = (event) => {
            if (event.origin !== window.location.origin || event.data?.type !== "sce_oauth_result") {
                return;
            }
            const success = event.data.status === "ok";
            notification.add(
                success
                    ? "La cuenta de Mercado Libre quedó conectada correctamente."
                    : event.data.message || "No se pudo completar la conexión con Mercado Libre.",
                {
                    title: success ? "Conexión completada" : "Error de conexión",
                    type: success ? "success" : "danger",
                    sticky: !success,
                }
            );
            if (success) {
                window.setTimeout(() => window.location.reload(), 1200);
            }
        };
        window.addEventListener("message", handler);
        return { stop: () => window.removeEventListener("message", handler) };
    },
};

registry.category("services").add("sce_oauth_result_listener", oauthResultListener);
