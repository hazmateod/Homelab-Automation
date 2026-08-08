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
