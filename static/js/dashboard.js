document.addEventListener("DOMContentLoaded", () => {

    console.log("HIMP dashboard loaded.");

    const buttons = document.querySelectorAll(".run-plugin");

    console.log(`Found ${buttons.length} Run buttons.`);


    buttons.forEach(button => {

        button.addEventListener("click", async () => {

            const plugin = button.dataset.plugin;

            const status = document.getElementById(
                `status-${plugin}`
            );

            const elapsed = document.getElementById(
                `elapsed-${plugin}`
            );


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

                const response = await fetch(
                    `/api/plugins/${plugin}/run`,
                    {
                        method: "POST"
                    }
                );


                const result = await response.json();


                if (result.success) {

                    button.textContent = "Completed";

                    button.classList.remove(
                        "btn-primary",
                        "btn-danger"
                    );

                    button.classList.add(
                        "btn-success"
                    );


                    if (status) {

                        status.textContent = "Success";

                        status.className =
                            "badge bg-success";

                    }


                } else {

                    button.textContent = "Failed";

                    button.classList.remove(
                        "btn-primary",
                        "btn-success"
                    );

                    button.classList.add(
                        "btn-danger"
                    );


                    if (status) {

                        status.textContent = "Failed";

                        status.className =
                            "badge bg-danger";

                    }

                }


                if (elapsed) {

                    elapsed.textContent =
                        `${result.elapsed.toFixed(3)} sec`;

                }


            } catch (error) {

                console.error(error);


                button.textContent = "Error";


                button.classList.remove(
                    "btn-primary",
                    "btn-success"
                );


                button.classList.add(
                    "btn-danger"
                );


                if (status) {

                    status.textContent = "Error";

                    status.className =
                        "badge bg-danger";

                }


                if (elapsed) {

                    elapsed.textContent = "--";

                }

            }


        });

    });

});
