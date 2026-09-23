/** @odoo-module **/

function showNotice(notice, message, type = "info") {
    notice.className = `alert alert-${type}`;
    notice.replaceChildren(document.createTextNode(message));
}

async function loadRemoteOptions(button) {
    const notice = document.getElementById("sce_remote_options_notice");
    const target = document.getElementById(button.dataset.target);
    if (!notice || !target) {
        return;
    }
    showNotice(notice, "Consultando opciones en tu Odoo...", "info");
    button.disabled = true;
    try {
        const response = await fetch("/my/sce/remote-options", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                jsonrpc: "2.0",
                method: "call",
                params: {
                    option_type: button.dataset.optionType,
                    account_id: document.querySelector("input[name='account_id']")?.value,
                },
                id: Date.now(),
            }),
        });
        const payload = await response.json();
        const result = payload.result || {};
        if (!result.ok) {
            showNotice(notice, result.error || "No se pudieron consultar las opciones.", "danger");
            return;
        }
        notice.className = "alert alert-info";
        notice.replaceChildren();
        if (!result.items.length) {
            notice.append(document.createTextNode("No se encontraron opciones en tu Odoo."));
            return;
        }
        const title = document.createElement("div");
        title.className = "fw-semibold mb-2";
        title.textContent = "Seleccioná una opción:";
        notice.append(title);
        const options = document.createElement("div");
        options.className = "d-flex flex-wrap gap-2";
        for (const item of result.items) {
            const option = document.createElement("button");
            option.type = "button";
            option.className = "btn btn-sm btn-outline-primary";
            option.textContent = `${item.name}${item.code ? ` [${item.code}]` : ""}`;
            option.addEventListener("click", () => {
                target.value = String(item.id);
                showNotice(notice, `${item.name} seleccionado.`, "success");
            });
            options.append(option);
        }
        notice.append(options);
    } catch (error) {
        showNotice(notice, "No se pudo conectar con tu Odoo. Revisá la configuración.", "danger");
    } finally {
        button.disabled = false;
    }
}

document.addEventListener("click", (event) => {
    const button = event.target.closest(".js_sce_remote_options");
    if (button) {
        loadRemoteOptions(button);
    }
});
