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
    const scheduleDayOfMonth = document.getElementById(
        "scheduleDayOfMonth"
    );
    const timeGroup = document.getElementById("scheduleTimeGroup");
    const dayGroup = document.getElementById("scheduleDayGroup");
    const dayOfMonthGroup = document.getElementById(
        "scheduleDayOfMonthGroup"
    );
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

        dayOfMonthGroup.classList.toggle(
            "d-none",
            value !== "monthly"
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

            scheduleDayOfMonth.value =
                data.day_of_month !== null
                    ? String(data.day_of_month)
                    : "";

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

            day_of_month:
                selectedFrequency === "monthly"
                    ? Number(scheduleDayOfMonth.value)
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
                          method: "POST",
                          headers: {
                              "Content-Type": "application/json"
                          },
                          body: JSON.stringify({
                              confirmed: true
                          })
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

/*
 * HIMP Execution History Detail UI
 */

document.addEventListener("DOMContentLoaded", () => {
    const modal = document.getElementById(
        "executionDetailsModal"
    );

    if (!modal) {
        return;
    }

    const loading = document.getElementById(
        "executionDetailsLoading"
    );

    const content = document.getElementById(
        "executionDetailsContent"
    );

    const error = document.getElementById(
        "executionDetailsError"
    );

    const executionId = document.getElementById(
        "executionDetailsId"
    );

    const plugin = document.getElementById(
        "executionDetailsPlugin"
    );

    const status = document.getElementById(
        "executionDetailsStatus"
    );

    const returnCode = document.getElementById(
        "executionDetailsReturnCode"
    );

    const elapsed = document.getElementById(
        "executionDetailsElapsed"
    );

    const executedAt = document.getElementById(
        "executionDetailsExecutedAt"
    );

    const stdout = document.getElementById(
        "executionDetailsStdout"
    );

    const stderr = document.getElementById(
        "executionDetailsStderr"
    );

    const warnings = document.getElementById(
        "executionDetailsWarnings"
    );

    const artifacts = document.getElementById(
        "executionDetailsArtifacts"
    );

    const reset = () => {
        loading.classList.remove("d-none");
        content.classList.add("d-none");
        error.classList.add("d-none");
        error.textContent = "";

        executionId.textContent = "";
        plugin.textContent = "";
        status.textContent = "";
        returnCode.textContent = "";
        elapsed.textContent = "";
        executedAt.textContent = "";

        stdout.textContent = "";
        stderr.textContent = "";
        warnings.textContent = "";
        artifacts.textContent = "";
    };

    const formatJson = (value) => {
        try {
            return JSON.stringify(
                value,
                null,
                2
            );
        } catch {
            return String(value);
        }
    };

    const loadExecution = async (id) => {
        reset();

        try {
            const response = await fetch(
                `/api/executions/id/${encodeURIComponent(id)}`
            );

            const result = await response.json();

            if (!response.ok) {
                throw new Error(
                    result.detail ||
                    "Unable to load execution details."
                );
            }

            executionId.textContent = result.id;
            plugin.textContent = result.plugin;

            status.innerHTML = result.success
                ? '<span class="badge bg-success">Success</span>'
                : '<span class="badge bg-danger">Failed</span>';

            returnCode.textContent =
                result.return_code;

            elapsed.textContent =
                `${Number(result.elapsed).toFixed(3)} sec`;

            executedAt.textContent =
                result.executed_at;

            stdout.textContent =
                result.stdout || "(none)";

            stderr.textContent =
                result.stderr || "(none)";

            warnings.textContent =
                result.warnings &&
                result.warnings.length
                    ? formatJson(result.warnings)
                    : "(none)";

            artifacts.textContent =
                result.artifacts &&
                result.artifacts.length
                    ? formatJson(result.artifacts)
                    : "(none)";

            loading.classList.add("d-none");
            content.classList.remove("d-none");

        } catch (loadError) {
            loading.classList.add("d-none");
            error.textContent =
                loadError.message ||
                "Unable to load execution details.";
            error.classList.remove("d-none");
        }
    };

    document.querySelectorAll(
        ".execution-details-button"
    ).forEach((button) => {
        button.addEventListener(
            "click",
            () => {
                loadExecution(
                    button.dataset.executionId
                );
            }
        );
    });
});

/*
 * HIMP Inventory SSH Connectivity Test UI
 */

document.addEventListener("DOMContentLoaded", () => {
    const modal = document.getElementById(
        "sshTestModal"
    );

    if (!modal) {
        return;
    }

    const loading = document.getElementById(
        "sshTestLoading"
    );

    const error = document.getElementById(
        "sshTestError"
    );

    const result = document.getElementById(
        "sshTestResult"
    );

    const host = document.getElementById(
        "sshTestHost"
    );

    const address = document.getElementById(
        "sshTestAddress"
    );

    const user = document.getElementById(
        "sshTestUser"
    );

    const status = document.getElementById(
        "sshTestStatus"
    );

    const elapsed = document.getElementById(
        "sshTestElapsed"
    );

    const message = document.getElementById(
        "sshTestMessage"
    );

    const stderrContainer = document.getElementById(
        "sshTestStderrContainer"
    );

    const stderr = document.getElementById(
        "sshTestStderr"
    );

    const reset = () => {
        loading.classList.remove("d-none");
        error.classList.add("d-none");
        result.classList.add("d-none");

        error.textContent = "";

        host.textContent = "";
        address.textContent = "";
        user.textContent = "";
        status.textContent = "";
        elapsed.textContent = "";
        message.textContent = "";

        stderr.textContent = "";
        stderrContainer.classList.add("d-none");
    };

    const statusBadge = (value, success) => {
        const badge = document.createElement("span");

        badge.className = success
            ? "badge bg-success"
            : "badge bg-danger";

        badge.textContent = value;

        return badge;
    };

    const testHost = async (
        hostname,
        button
    ) => {
        reset();

        button.disabled = true;

        const originalText = button.textContent;

        button.textContent = "Testing...";

        const bootstrapModal =
            bootstrap.Modal.getOrCreateInstance(
                modal
            );

        bootstrapModal.show();

        try {
            const response = await fetch(
                `/api/inventory/hosts/${encodeURIComponent(hostname)}/ssh-test`,
                {
                    method: "POST",
                }
            );

            const data = await response.json();

            if (!response.ok) {
                throw new Error(
                    data.detail?.error ||
                    data.detail ||
                    "Unable to test SSH connectivity."
                );
            }

            host.textContent =
                data.hostname;

            address.textContent =
                data.ip;

            user.textContent =
                data.user;

            status.replaceChildren(
                statusBadge(
                    data.status,
                    data.success
                )
            );

            elapsed.textContent =
                `${Number(data.elapsed).toFixed(3)} sec`;

            message.textContent =
                data.message ||
                "No additional information.";

            if (data.stderr) {
                stderr.textContent =
                    data.stderr;

                stderrContainer.classList.remove(
                    "d-none"
                );
            }

            loading.classList.add("d-none");
            result.classList.remove("d-none");

        } catch (testError) {
            loading.classList.add("d-none");

            error.textContent =
                testError.message ||
                "Unable to test SSH connectivity.";

            error.classList.remove("d-none");

        } finally {
            button.disabled = false;
            button.textContent = originalText;
        }
    };

    document.querySelectorAll(
        ".test-ssh-button"
    ).forEach((button) => {
        button.addEventListener(
            "click",
            () => {
                testHost(
                    button.dataset.hostname,
                    button
                );
            }
        );
    });
});

/*
 * HIMP Inventory Host Health UI
 */

document.addEventListener("DOMContentLoaded", () => {
    const modal = document.getElementById(
        "hostHealthModal"
    );

    if (!modal) {
        return;
    }

    const loading = document.getElementById(
        "hostHealthLoading"
    );

    const error = document.getElementById(
        "hostHealthError"
    );

    const result = document.getElementById(
        "hostHealthResult"
    );

    const host = document.getElementById(
        "hostHealthHost"
    );

    const check = document.getElementById(
        "hostHealthCheck"
    );

    const status = document.getElementById(
        "hostHealthStatus"
    );

    const elapsed = document.getElementById(
        "hostHealthElapsed"
    );

    const sshStatus = document.getElementById(
        "hostHealthSSHStatus"
    );

    const returnCode = document.getElementById(
        "hostHealthReturnCode"
    );

    const message = document.getElementById(
        "hostHealthMessage"
    );

    const stdout = document.getElementById(
        "hostHealthStdout"
    );

    const stderr = document.getElementById(
        "hostHealthStderr"
    );

    const stdoutContainer = document.getElementById(
        "hostHealthStdoutContainer"
    );

    const stderrContainer = document.getElementById(
        "hostHealthStderrContainer"
    );

    const reset = () => {
        loading.classList.remove("d-none");
        error.classList.add("d-none");
        result.classList.add("d-none");

        error.textContent = "";

        host.textContent = "";
        check.textContent = "";
        status.textContent = "";
        elapsed.textContent = "";
        sshStatus.textContent = "";
        returnCode.textContent = "";
        message.textContent = "";

        stdout.textContent = "";
        stderr.textContent = "";

        stdoutContainer.classList.add("d-none");
        stderrContainer.classList.add("d-none");
    };

    const showResult = (data) => {
        const healthResult = (
            data.results &&
            data.results.length
        )
            ? data.results[0]
            : null;

        if (!healthResult) {
            throw new Error(
                "Host health response contained no results."
            );
        }

        const details = healthResult.details || {};

        host.textContent = data.hostname || "(unknown)";
        check.textContent = healthResult.check || "(unknown)";

        status.textContent =
            healthResult.status || "UNKNOWN";

        status.classList.remove(
            "text-success",
            "text-warning",
            "text-danger",
            "text-secondary"
        );

        if (healthResult.status === "PASS") {
            status.classList.add("text-success");
        } else if (
            healthResult.status === "WARNING"
        ) {
            status.classList.add("text-warning");
        } else if (
            healthResult.status === "FAIL"
        ) {
            status.classList.add("text-danger");
        } else {
            status.classList.add("text-secondary");
        }

        elapsed.textContent =
            `${Number(
                healthResult.duration_ms || 0
            ).toFixed(3)} ms`;

        sshStatus.textContent =
            details.ssh_status || "(none)";

        returnCode.textContent =
            details.return_code ?? "(none)";

        message.textContent =
            healthResult.message || "(none)";

        if (details.stdout) {
            stdout.textContent = details.stdout;
            stdoutContainer.classList.remove(
                "d-none"
            );
        }

        if (details.stderr) {
            stderr.textContent = details.stderr;
            stderrContainer.classList.remove(
                "d-none"
            );
        }

        loading.classList.add("d-none");
        result.classList.remove("d-none");
    };

    const testHealth = async (
        button,
        hostname
    ) => {
        reset();

        button.disabled = true;
        const originalText = button.textContent;
        button.textContent = "Checking...";

        const bootstrapModal =
            bootstrap.Modal.getOrCreateInstance(
                modal
            );

        bootstrapModal.show();

        try {
            const response = await fetch(
                `/api/inventory/hosts/${encodeURIComponent(hostname)}/health`,
                {
                    method: "POST",
                    headers: {
                        "Accept": "application/json",
                    },
                }
            );

            const data = await response.json();

            if (!response.ok) {
                throw new Error(
                    data.detail?.error ||
                    data.detail ||
                    "Unable to check host health."
                );
            }

            showResult(data);

        } catch (healthError) {
            loading.classList.add("d-none");

            error.textContent =
                healthError.message ||
                "Unable to check host health.";

            error.classList.remove("d-none");

        } finally {
            button.disabled = false;
            button.textContent = originalText;
        }
    };

    document.querySelectorAll(
        ".host-health-button"
    ).forEach((button) => {
        button.addEventListener(
            "click",
            () => {
                testHealth(
                    button,
                    button.dataset.hostname
                );
            }
        );
    });
});

/*
 * HIMP Inventory Host Health History UI
 */

document.addEventListener("DOMContentLoaded", () => {
    const modal = document.getElementById(
        "hostHealthHistoryModal"
    );

    if (!modal) {
        return;
    }

    const loading = document.getElementById(
        "hostHealthHistoryLoading"
    );

    const error = document.getElementById(
        "hostHealthHistoryError"
    );

    const result = document.getElementById(
        "hostHealthHistoryResult"
    );

    const host = document.getElementById(
        "hostHealthHistoryHost"
    );

    const count = document.getElementById(
        "hostHealthHistoryCount"
    );

    const rows = document.getElementById(
        "hostHealthHistoryRows"
    );

    const empty = document.getElementById(
        "hostHealthHistoryEmpty"
    );

    const reset = () => {
        loading.classList.remove("d-none");
        error.classList.add("d-none");
        result.classList.add("d-none");
        empty.classList.add("d-none");

        error.textContent = "";
        host.textContent = "";
        count.textContent = "";
        rows.innerHTML = "";
    };

    const statusClass = (status) => {
        if (status === "PASS") {
            return "text-success";
        }

        if (status === "WARNING") {
            return "text-warning";
        }

        if (status === "FAIL") {
            return "text-danger";
        }

        return "text-secondary";
    };

    const formatDetails = (details) => {
        try {
            return JSON.stringify(
                details || {},
                null,
                2
            );
        } catch {
            return String(details);
        }
    };

    const renderHistory = (data) => {
        const history = Array.isArray(data.history)
            ? data.history
            : [];

        host.textContent =
            data.hostname || "(unknown)";

        count.textContent =
            data.count ?? history.length;

        rows.innerHTML = "";

        if (history.length === 0) {
            empty.classList.remove("d-none");
            loading.classList.add("d-none");
            result.classList.remove("d-none");
            return;
        }

        history.forEach((entry) => {
            const row = document.createElement("tr");

            const id = document.createElement("td");
            id.textContent = entry.id ?? "";
            row.appendChild(id);

            const check = document.createElement("td");
            check.textContent =
                entry.check_name || "(unknown)";
            row.appendChild(check);

            const status = document.createElement("td");
            status.textContent =
                entry.status || "UNKNOWN";
            status.classList.add(
                statusClass(entry.status)
            );
            row.appendChild(status);

            const runtime = document.createElement("td");
            runtime.textContent =
                `${Number(
                    entry.duration_ms || 0
                ).toFixed(3)} ms`;
            row.appendChild(runtime);

            const message = document.createElement("td");
            message.textContent =
                entry.message || "(none)";
            row.appendChild(message);

            const executed = document.createElement("td");
            executed.textContent =
                entry.created_at || "(unknown)";
            row.appendChild(executed);

            const details = document.createElement("td");

            const detailsPre =
                document.createElement("pre");

            detailsPre.className =
                "mb-0 bg-black border border-secondary rounded p-2 text-light";

            detailsPre.style.maxWidth = "420px";
            detailsPre.style.maxHeight = "180px";
            detailsPre.style.overflow = "auto";

            detailsPre.textContent =
                formatDetails(entry.details);

            details.appendChild(detailsPre);
            row.appendChild(details);

            rows.appendChild(row);
        });

        loading.classList.add("d-none");
        result.classList.remove("d-none");
    };

    const loadHistory = async (
        button,
        hostname
    ) => {
        reset();

        button.disabled = true;

        const originalText = button.textContent;
        button.textContent = "Loading...";

        const bootstrapModal =
            bootstrap.Modal.getOrCreateInstance(
                modal
            );

        bootstrapModal.show();

        try {
            const response = await fetch(
                `/api/inventory/hosts/${encodeURIComponent(hostname)}/health/history`,
                {
                    headers: {
                        "Accept": "application/json",
                    },
                }
            );

            const data = await response.json();

            if (!response.ok) {
                throw new Error(
                    data.detail?.error ||
                    data.detail ||
                    "Unable to load host health history."
                );
            }

            renderHistory(data);

        } catch (historyError) {
            loading.classList.add("d-none");

            error.textContent =
                historyError.message ||
                "Unable to load host health history.";

            error.classList.remove("d-none");

        } finally {
            button.disabled = false;
            button.textContent = originalText;
        }
    };

    document.querySelectorAll(
        ".host-health-history-button"
    ).forEach((button) => {
        button.addEventListener(
            "click",
            () => {
                loadHistory(
                    button,
                    button.dataset.hostname
                );
            }
        );
    });
});
