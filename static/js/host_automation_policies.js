"use strict";

document.addEventListener("DOMContentLoaded", async () => {
    const controls = document.querySelectorAll(
        ".host-automation-control"
    );

    async function loadPolicy(control) {
        const hostname = control.dataset.hostname;
        const status = control.querySelector(".automation-status");
        const button = control.querySelector(".automation-toggle");

        status.textContent = "Loading";
        status.className = "badge bg-secondary automation-status";
        button.disabled = true;

        try {
            const response = await fetch(
                `/inventory/hosts/${encodeURIComponent(hostname)}/automation-policy`,
                { credentials: "same-origin" }
            );

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const policy = await response.json();

            control.dataset.enabled = String(policy.enabled);

            status.textContent = policy.enabled
                ? "Enabled"
                : "Disabled";

            status.className = policy.enabled
                ? "badge bg-success automation-status"
                : "badge bg-warning text-dark automation-status";

            status.title = policy.reason || "";

            button.textContent = policy.enabled
                ? "Disable"
                : "Enable";

            button.disabled = false;
        } catch (error) {
            status.textContent = "Unavailable";
            status.className = "badge bg-danger automation-status";
            status.title = "Unable to retrieve automation policy";
            button.disabled = true;
        }
    }

    for (const control of controls) {
        await loadPolicy(control);
    }

    document.addEventListener("click", async (event) => {
        const button = event.target.closest(
            ".automation-toggle"
        );

        if (!button) {
            return;
        }

        const control = button.closest(
            ".host-automation-control"
        );

        if (!control) {
            return;
        }

        const hostname = control.dataset.hostname;
        const currentlyEnabled =
            control.dataset.enabled === "true";

        let reason = "";

        if (currentlyEnabled) {
            const entered = window.prompt(
                `Reason for disabling automation on ${hostname}:`
            );

            if (entered === null) {
                return;
            }

            reason = entered.trim();

            if (!reason) {
                window.alert(
                    "A reason is required when disabling automation."
                );
                return;
            }
        } else {
            if (!window.confirm(
                `Enable automation for ${hostname}?`
            )) {
                return;
            }

            reason = "Automation re-enabled by operator";
        }

        button.disabled = true;

        try {
            const response = await fetch(
                `/inventory/hosts/${encodeURIComponent(hostname)}/automation-policy`,
                {
                    method: "PUT",
                    credentials: "same-origin",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        enabled: !currentlyEnabled,
                        reason
                    })
                }
            );

            if (!response.ok) {
                const payload = await response.json().catch(
                    () => ({})
                );

                throw new Error(
                    typeof payload.detail === "string"
                        ? payload.detail
                        : `HTTP ${response.status}`
                );
            }

            await loadPolicy(control);
        } catch (error) {
            window.alert(
                `Unable to update automation policy: ${error.message}`
            );
            await loadPolicy(control);
        }
    });
});
