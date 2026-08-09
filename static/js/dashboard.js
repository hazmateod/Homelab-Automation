document.addEventListener("DOMContentLoaded", () => {

    console.log("HIMP dashboard loaded.");

    initializePluginButtons();
    initializeRestartButton();
    initializeUpdateButtons();

});

function initializePluginButtons() {

    const buttons = document.querySelectorAll(".run-plugin");

    console.log(`Found ${buttons.length} Run buttons.`);

    buttons.forEach(button => {

        button.addEventListener("click", async () => {

            const plugin = button.dataset.plugin;

            const status = document.getElementById(`status-${plugin}`);
            const elapsed = document.getElementById(`elapsed-${plugin}`);

            button.disabled = true;
            button.textContent = "Running...";

            if (status) {
                status.textContent = "Running...";
                status.className = "badge bg-warning text-dark";
            }

            if (elapsed) {
                elapsed.textContent = "--";
            }

            try {

                const response = await fetch(`/api/plugins/${plugin}/run`, {
                    method: "POST"
                });

                const result = await response.json();

                if (result.success) {

                    button.textContent = "Completed";
                    button.classList.remove("btn-primary", "btn-danger");
                    button.classList.add("btn-success");

                    if (status) {
                        status.textContent = "Success";
                        status.className = "badge bg-success";
                    }

                } else {

                    button.textContent = "Failed";
                    button.classList.remove("btn-primary", "btn-success");
                    button.classList.add("btn-danger");

                    if (status) {
                        status.textContent = "Failed";
                        status.className = "badge bg-danger";
                    }

                }

                if (elapsed && result.elapsed !== undefined) {
                    elapsed.textContent = `${result.elapsed.toFixed(3)} sec`;
                }

            } catch (error) {

                console.error(error);

                button.textContent = "Error";
                button.classList.remove("btn-primary", "btn-success");
                button.classList.add("btn-danger");

                if (status) {
                    status.textContent = "Error";
                    status.className = "badge bg-danger";
                }

                if (elapsed) {
                    elapsed.textContent = "--";
                }

            }

        });

    });

}

function initializeRestartButton() {

    const restartButton = document.getElementById("restart-himp");

    if (!restartButton) {
        console.log("Restart button not found.");
        return;
    }

    console.log("Restart button initialized.");

    restartButton.addEventListener("click", async () => {

        const confirmed = confirm(
            "Restart the HIMP service?\n\nThe dashboard will be unavailable for a few seconds."
        );

        if (!confirmed) {
            return;
        }

        restartButton.disabled = true;
        restartButton.textContent = "Restarting...";

        try {

            const response = await fetch("/system/restart", {
                method: "POST"
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            console.log("Restart requested.");

            restartButton.classList.remove("btn-warning");
            restartButton.classList.add("btn-success");
            restartButton.textContent = "Restart Requested";

            setTimeout(() => {
                window.location.reload();
            }, 8000);

        } catch (error) {

            console.error(error);

            restartButton.disabled = false;
            restartButton.classList.remove("btn-success");
            restartButton.classList.add("btn-warning");
            restartButton.textContent = "Restart HIMP";

            alert("Unable to restart the HIMP service.");

        }

    });

}


function initializeUpdateButtons() {

    const buttons = document.querySelectorAll(".update-target");

    console.log(`Found ${buttons.length} Update buttons.`);

    buttons.forEach(button => {

        button.addEventListener("click", async () => {

            const type = button.dataset.updateType;
            const target = button.dataset.target;

            const confirmed = confirm(
                `Update ${type} "${target}"?\n\nThis will update the selected host or group using the HIMP update playbook.`
            );

            if (!confirmed) {
                return;
            }

            const originalText = button.textContent;

            button.disabled = true;
            button.textContent = "Updating...";
            button.classList.remove("btn-primary", "btn-success", "btn-danger");
            button.classList.add("btn-warning", "text-dark");

            try {

                const response = await fetch(
                    `/api/update/${type}/${encodeURIComponent(target)}`,
                    {
                        method: "POST"
                    }
                );

                const result = await response.json();

                if (!response.ok || !result.success) {
                    throw new Error(
                        result.detail
                            ? JSON.stringify(result.detail)
                            : `HTTP ${response.status}`
                    );
                }

                button.classList.remove("btn-warning", "text-dark");
                button.classList.add("btn-success");
                button.textContent = "Updated";

                setTimeout(() => {
                    window.location.reload();
                }, 1500);

            } catch (error) {

                console.error(error);

                button.disabled = false;
                button.classList.remove("btn-warning", "text-dark");
                button.classList.add("btn-danger");
                button.textContent = "Failed";

                setTimeout(() => {
                    button.classList.remove("btn-danger");
                    button.classList.add("btn-primary");
                    button.textContent = originalText;
                }, 3000);

            }

        });

    });

}

/*
 * HIMP Inventory SSH Setup UI
 */

document.addEventListener("DOMContentLoaded", () => {
    const modal = document.getElementById(
        "sshSetupModal"
    );

    if (!modal) {
        return;
    }

    const host = document.getElementById(
        "sshSetupHost"
    );

    const copyCommand = document.getElementById(
        "sshSetupCopyCommand"
    );

    const testCommand = document.getElementById(
        "sshSetupTestCommand"
    );

    const ansibleCommand = document.getElementById(
        "sshSetupAnsibleCommand"
    );

    const copyStatus = document.getElementById(
        "sshSetupCopyStatus"
    );

    function clearStatus() {
        copyStatus.textContent = "";
        copyStatus.classList.add("d-none");
    }

    function showStatus(message) {
        copyStatus.textContent = message;
        copyStatus.classList.remove("d-none");
    }

    function configure(hostname, ip, user) {
        const safeHostname = hostname.trim();
        const safeIp = ip.trim();
        const safeUser = user.trim();

        host.textContent =
            `${safeHostname} (${safeUser}@${safeIp})`;

        copyCommand.value =
            `ssh-copy-id ${safeUser}@${safeIp}`;

        testCommand.value =
            `ssh ${safeUser}@${safeIp}`;

        ansibleCommand.value =
            `ansible ${safeHostname} -i inventory/hosts.yml -m ping`;

        clearStatus();
    }

    function getAddHostValues() {
        return {
            hostname:
                document.getElementById(
                    "addHostHostname"
                ).value,

            ip:
                document.getElementById(
                    "addHostIp"
                ).value,

            user:
                document.getElementById(
                    "addHostUser"
                ).value,
        };
    }

    function getEditHostValues() {
        return {
            hostname:
                document.getElementById(
                    "editHostHostname"
                ).value,

            ip:
                document.getElementById(
                    "editHostIp"
                ).value,

            user:
                document.getElementById(
                    "editHostUser"
                ).value,
        };
    }

    function showSetup(values) {
        if (
            !values.hostname.trim() ||
            !values.ip.trim() ||
            !values.user.trim()
        ) {
            showStatus(
                "Enter the hostname, IP address, and Ansible user before opening SSH setup."
            );
            return;
        }

        configure(
            values.hostname,
            values.ip,
            values.user
        );

        const bootstrapModal =
            bootstrap.Modal.getOrCreateInstance(
                modal
            );

        bootstrapModal.show();
    }

    async function copyToClipboard(
        input,
        label
    ) {
        try {
            if (
                navigator.clipboard &&
                typeof navigator.clipboard.writeText === "function"
            ) {
                await navigator.clipboard.writeText(
                    input.value
                );

                showStatus(
                    `${label} copied to clipboard.`
                );

                return;
            }
        } catch (err) {
            console.warn(
                "Modern clipboard API unavailable:",
                err
            );
        }

        try {
            input.focus();
            input.select();

            const copied =
                document.execCommand("copy");

            if (copied) {
                showStatus(
                    `${label} copied to clipboard.`
                );

                return;
            }
        } catch (err) {
            console.warn(
                "Legacy clipboard fallback failed:",
                err
            );
        }

        input.focus();
        input.select();

        showStatus(
            "Unable to copy automatically. "
            + "The command has been selected so you can copy it manually."
        );
    }

    document.getElementById(
        "showAddHostSshSetupButton"
    ).addEventListener(
        "click",
        () => {
            showSetup(
                getAddHostValues()
            );
        }
    );

    document.getElementById(
        "showEditHostSshSetupButton"
    ).addEventListener(
        "click",
        () => {
            showSetup(
                getEditHostValues()
            );
        }
    );

    document.getElementById(
        "copySshSetupCopyCommand"
    ).addEventListener(
        "click",
        () => {
            copyToClipboard(
                copyCommand,
                "SSH key command"
            );
        }
    );

    document.getElementById(
        "copySshSetupTestCommand"
    ).addEventListener(
        "click",
        () => {
            copyToClipboard(
                testCommand,
                "SSH test command"
            );
        }
    );

    document.getElementById(
        "copySshSetupAnsibleCommand"
    ).addEventListener(
        "click",
        () => {
            copyToClipboard(
                ansibleCommand,
                "Ansible test command"
            );
        }
    );
});

/*
 * HIMP Inventory Host Add UI
 */

document.addEventListener("DOMContentLoaded", () => {
    const modal = document.getElementById("addHostModal");

    if (!modal) {
        return;
    }

    const hostname = document.getElementById("addHostHostname");
    const group = document.getElementById("addHostGroup");
    const ip = document.getElementById("addHostIp");
    const user = document.getElementById("addHostUser");
    const become = document.getElementById("addHostBecome");
    const saveButton = document.getElementById("saveAddHostButton");
    const error = document.getElementById("addHostError");

    function clearError() {
        error.textContent = "";
        error.classList.add("d-none");
    }

    function showError(message) {
        error.textContent = message;
        error.classList.remove("d-none");
    }

    modal.addEventListener("show.bs.modal", () => {
        clearError();

        hostname.value = "";
        group.value = "";
        ip.value = "";
        user.value = "";
        become.checked = false;

        saveButton.disabled = false;
        saveButton.classList.remove("btn-success");
        saveButton.classList.add("btn-primary");
        saveButton.textContent = "Add Host";
    });

    saveButton.addEventListener("click", async () => {
        clearError();

        if (
            !hostname.value.trim() ||
            !group.value.trim() ||
            !ip.value.trim() ||
            !user.value.trim()
        ) {
            showError(
                "Hostname, group, IP address, and Ansible user are required."
            );
            return;
        }

        const payload = {
            hostname: hostname.value.trim(),
            group: group.value.trim(),
            ip: ip.value.trim(),
            user: user.value.trim(),
            become: become.checked,
        };

        const originalText = saveButton.textContent;

        saveButton.disabled = true;
        saveButton.textContent = "Adding...";

        try {
            const response = await fetch(
                "/api/inventory/hosts",
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify(payload),
                }
            );

            const result = await response.json();

            if (!response.ok) {
                throw new Error(
                    result.detail?.error ||
                    result.detail ||
                    `HTTP ${response.status}`
                );
            }

            saveButton.classList.remove("btn-primary");
            saveButton.classList.add("btn-success");
            saveButton.textContent = "Added";

            setTimeout(() => {
                window.location.reload();
            }, 800);
        } catch (err) {
            console.error(err);

            showError(err.message);

            saveButton.disabled = false;
            saveButton.textContent = originalText;
        }
    });
});

/*
 * HIMP Inventory Host Remove / Restore UI
 */

document.addEventListener("DOMContentLoaded", () => {
    const removeModal = document.getElementById(
        "removeHostModal"
    );

    const restoreModal = document.getElementById(
        "restoreHostModal"
    );

    if (!removeModal && !restoreModal) {
        return;
    }

    function showError(element, message) {
        element.textContent = message;
        element.classList.remove("d-none");
    }

    function clearError(element) {
        element.textContent = "";
        element.classList.add("d-none");
    }

    if (removeModal) {
        const removeName = document.getElementById(
            "removeHostName"
        );

        const removeButton = document.getElementById(
            "confirmRemoveHostButton"
        );

        const removeError = document.getElementById(
            "removeHostError"
        );

        let hostname = "";

        removeModal.addEventListener(
            "show.bs.modal",
            (event) => {
                clearError(removeError);

                const button = event.relatedTarget;

                if (!button) {
                    return;
                }

                hostname =
                    button.dataset.hostname || "";

                removeName.textContent = hostname;

                removeButton.disabled = false;
                removeButton.textContent =
                    "Remove Host";
            }
        );

        removeButton.addEventListener(
            "click",
            async () => {
                clearError(removeError);

                if (!hostname) {
                    showError(
                        removeError,
                        "No host was selected."
                    );
                    return;
                }

                removeButton.disabled = true;
                removeButton.textContent =
                    "Removing...";

                try {
                    const response = await fetch(
                        `/api/inventory/hosts/${encodeURIComponent(
                            hostname
                        )}`,
                        {
                            method: "DELETE",
                        }
                    );

                    const result =
                        await response.json();

                    if (!response.ok) {
                        throw new Error(
                            result.detail?.error ||
                            result.detail ||
                            `HTTP ${response.status}`
                        );
                    }

                    removeButton.classList.remove(
                        "btn-danger"
                    );

                    removeButton.classList.add(
                        "btn-success"
                    );

                    removeButton.textContent =
                        "Removed";

                    setTimeout(() => {
                        window.location.reload();
                    }, 800);
                } catch (err) {
                    console.error(err);

                    showError(
                        removeError,
                        err.message
                    );

                    removeButton.disabled = false;
                    removeButton.textContent =
                        "Remove Host";
                }
            }
        );
    }

    if (restoreModal) {
        const restoreName = document.getElementById(
            "restoreHostName"
        );

        const restoreButton = document.getElementById(
            "confirmRestoreHostButton"
        );

        const restoreError = document.getElementById(
            "restoreHostError"
        );

        let hostname = "";

        restoreModal.addEventListener(
            "show.bs.modal",
            (event) => {
                clearError(restoreError);

                const button = event.relatedTarget;

                if (!button) {
                    return;
                }

                hostname =
                    button.dataset.hostname || "";

                restoreName.textContent = hostname;

                restoreButton.disabled = false;
                restoreButton.textContent =
                    "Restore Host";
            }
        );

        restoreButton.addEventListener(
            "click",
            async () => {
                clearError(restoreError);

                if (!hostname) {
                    showError(
                        restoreError,
                        "No host was selected."
                    );
                    return;
                }

                restoreButton.disabled = true;
                restoreButton.textContent =
                    "Restoring...";

                try {
                    const response = await fetch(
                        `/api/inventory/hosts/${encodeURIComponent(
                            hostname
                        )}/restore`,
                        {
                            method: "POST",
                        }
                    );

                    const result =
                        await response.json();

                    if (!response.ok) {
                        throw new Error(
                            result.detail?.error ||
                            result.detail ||
                            `HTTP ${response.status}`
                        );
                    }

                    restoreButton.classList.remove(
                        "btn-success"
                    );

                    restoreButton.classList.add(
                        "btn-primary"
                    );

                    restoreButton.textContent =
                        "Restored";

                    setTimeout(() => {
                        window.location.reload();
                    }, 800);
                } catch (err) {
                    console.error(err);

                    showError(
                        restoreError,
                        err.message
                    );

                    restoreButton.disabled = false;
                    restoreButton.textContent =
                        "Restore Host";
                }
            }
        );
    }
});

/*
 * HIMP Inventory Host Edit UI
 */

document.addEventListener("DOMContentLoaded", () => {
    const modal = document.getElementById("editHostModal");

    if (!modal) {
        return;
    }

    const hostname = document.getElementById(
        "editHostHostname"
    );
    const group = document.getElementById(
        "editHostGroup"
    );
    const ip = document.getElementById(
        "editHostIp"
    );
    const user = document.getElementById(
        "editHostUser"
    );
    const become = document.getElementById(
        "editHostBecome"
    );
    const saveButton = document.getElementById(
        "saveEditHostButton"
    );
    const error = document.getElementById(
        "editHostError"
    );

    function clearError() {
        error.textContent = "";
        error.classList.add("d-none");
    }

    function showError(message) {
        error.textContent = message;
        error.classList.remove("d-none");
    }

    modal.addEventListener(
        "show.bs.modal",
        (event) => {
            clearError();

            const button = event.relatedTarget;

            if (!button) {
                return;
            }

            hostname.value = button.dataset.hostname || "";
            group.value = button.dataset.group || "";
            ip.value = button.dataset.ip || "";
            user.value = button.dataset.user || "";
            become.checked =
                button.dataset.become === "true";

            document.getElementById(
                "editHostModalLabel"
            ).textContent =
                `Edit Host — ${hostname.value}`;
        }
    );

    saveButton.addEventListener(
        "click",
        async () => {
            clearError();

            if (
                !group.value.trim() ||
                !ip.value.trim() ||
                !user.value.trim()
            ) {
                showError(
                    "Group, IP address, and Ansible user are required."
                );
                return;
            }

            const payload = {
                group: group.value.trim(),
                ip: ip.value.trim(),
                user: user.value.trim(),
                become: become.checked,
            };

            const originalText =
                saveButton.textContent;

            saveButton.disabled = true;
            saveButton.textContent = "Saving...";

            try {
                const response = await fetch(
                    `/api/inventory/hosts/${encodeURIComponent(
                        hostname.value
                    )}`,
                    {
                        method: "PUT",
                        headers: {
                            "Content-Type":
                                "application/json",
                        },
                        body: JSON.stringify(payload),
                    }
                );

                const result = await response.json();

                if (!response.ok) {
                    throw new Error(
                        result.detail?.error ||
                        result.detail ||
                        `HTTP ${response.status}`
                    );
                }

                saveButton.classList.remove(
                    "btn-primary"
                );
                saveButton.classList.add(
                    "btn-success"
                );
                saveButton.textContent =
                    "Saved";

                setTimeout(() => {
                    window.location.reload();
                }, 800);

            } catch (err) {
                console.error(err);

                showError(err.message);

                saveButton.disabled = false;
                saveButton.textContent =
                    originalText;
            }
        }
    );
});


/*
 * HIMP Scheduler UI
 */

document.addEventListener("DOMContentLoaded", () => {
    const modal = document.getElementById("scheduleModal");

    if (!modal) {
        return;
    }

    const taskId = document.getElementById("scheduleTaskId");
    const enabled = document.getElementById("scheduleEnabled");
    const frequency = document.getElementById("scheduleFrequency");
    const scheduleTime = document.getElementById("scheduleTime");
    const scheduleDay = document.getElementById("scheduleDay");
    const timeGroup = document.getElementById("scheduleTimeGroup");
    const dayGroup = document.getElementById("scheduleDayGroup");
    const saveButton = document.getElementById("saveScheduleButton");
    const error = document.getElementById("scheduleError");

    function updateScheduleFields() {
        const value = frequency.value;

        timeGroup.classList.toggle(
            "d-none",
            value === "manual"
        );

        dayGroup.classList.toggle(
            "d-none",
            value !== "weekly"
        );
    }

    function showError(message) {
        error.textContent = message;
        error.classList.remove("d-none");
    }

    function clearError() {
        error.textContent = "";
        error.classList.add("d-none");
    }

    modal.addEventListener("show.bs.modal", async (event) => {
        clearError();

        const button = event.relatedTarget;

        if (!button) {
            return;
        }

        const id = button.dataset.taskId;
        const name = button.dataset.taskName;

        taskId.value = id;
        document.getElementById("scheduleModalLabel").textContent =
            `Edit Schedule — ${name}`;

        saveButton.disabled = true;

        try {
            const response = await fetch(
                `/api/scheduler/${encodeURIComponent(id)}`
            );

            const data = await response.json();

            if (!response.ok) {
                throw new Error(
                    data.detail || "Unable to load schedule."
                );
            }

            enabled.value = data.enabled ? "true" : "false";
            frequency.value = data.frequency;
            scheduleTime.value = data.schedule_time || "";
            scheduleDay.value =
                data.day_of_week !== null
                    ? String(data.day_of_week)
                    : "0";

            updateScheduleFields();
        } catch (err) {
            showError(err.message);
        } finally {
            saveButton.disabled = false;
        }
    });

    frequency.addEventListener(
        "change",
        updateScheduleFields
    );

    saveButton.addEventListener("click", async () => {
        clearError();

        const selectedFrequency = frequency.value;

        const payload = {
            enabled: enabled.value === "true",
            frequency: selectedFrequency,
            schedule_time:
                selectedFrequency === "manual"
                    ? null
                    : scheduleTime.value,
            day_of_week:
                selectedFrequency === "weekly"
                    ? Number(scheduleDay.value)
                    : null,
        };

        saveButton.disabled = true;

        try {
            const response = await fetch(
                `/api/scheduler/${encodeURIComponent(taskId.value)}`,
                {
                    method: "PUT",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify(payload),
                }
            );

            const data = await response.json();

            if (!response.ok) {
                throw new Error(
                    data.detail?.error ||
                    data.detail ||
                    "Unable to update schedule."
                );
            }

            window.location.reload();
        } catch (err) {
            showError(err.message);
            saveButton.disabled = false;
        }
    });

    updateScheduleFields();
});

/*
 * HIMP Automation Run UI
 */

document.addEventListener("DOMContentLoaded", () => {
    const buttons = document.querySelectorAll(
        ".automation-run-button"
    );

    buttons.forEach(button => {
        button.addEventListener("click", async () => {
            const taskId = button.dataset.taskId;
            const originalText = button.textContent;

            const confirmed = confirm(
                `Run automation "${taskId}" now?`
            );

            if (!confirmed) {
                return;
            }

            button.disabled = true;
            button.classList.remove(
                "btn-outline-success",
                "btn-success",
                "btn-danger"
            );
            button.classList.add("btn-warning", "text-dark");
            button.textContent = "Running...";

            try {
                const response = await fetch(
                    `/api/automation/${encodeURIComponent(taskId)}/run`,
                    {
                        method: "POST"
                    }
                );

                const result = await response.json();

                if (!response.ok) {
                    throw new Error(
                        result.detail ||
                        `HTTP ${response.status}`
                    );
                }

                button.classList.remove(
                    "btn-warning",
                    "text-dark"
                );
                button.classList.add("btn-success");
                button.textContent = "Completed";

                setTimeout(() => {
                    button.disabled = false;
                    button.classList.remove("btn-success");
                    button.classList.add("btn-outline-success");
                    button.textContent = originalText;
                }, 3000);

            } catch (error) {
                console.error(error);

                button.disabled = false;
                button.classList.remove(
                    "btn-warning",
                    "text-dark"
                );
                button.classList.add("btn-danger");
                button.textContent = "Failed";

                setTimeout(() => {
                    button.classList.remove("btn-danger");
                    button.classList.add("btn-outline-success");
                    button.textContent = originalText;
                }, 3000);
            }
        });
    });
});
