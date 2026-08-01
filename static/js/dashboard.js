document.addEventListener("DOMContentLoaded", () => {

    console.log("HIMP dashboard loaded.");

    const buttons = document.querySelectorAll(".run-plugin");

    console.log(`Found ${buttons.length} Run buttons.`);

    buttons.forEach(button => {

        button.addEventListener("click", async () => {

            const plugin = button.dataset.plugin;

            const status = document.getElementById(`status-${plugin}`);

            const elapsed = document.getElementById(`elapsed-${plugin}`);

            button.disabled = true;

            button.textContent = "Running...";

            status.textContent = "Running...";

            elapsed.textContent = "--";

            try {

                const response = await fetch(
                    `/api/plugins/${plugin}/run`,
                    {
                        method: "POST"
                    }
                );

                const result = await response.json();

                if (result.success) {

                    button.textContent = "Completed";

                    button.classList.remove("btn-primary");

                    button.classList.add("btn-success");

                    status.textContent = "Success";

                } else {

                    button.textContent = "Failed";

                    button.classList.remove("btn-primary");

                    button.classList.add("btn-danger");

                    status.textContent = "Failed";

                }

                elapsed.textContent = `${result.elapsed.toFixed(3)} sec`;

            } catch (error) {

                console.error(error);

                button.textContent = "Error";

                button.classList.remove("btn-primary");

                button.classList.add("btn-danger");

                status.textContent = "Error";

                elapsed.textContent = "--";

            }

        });

    });

});
