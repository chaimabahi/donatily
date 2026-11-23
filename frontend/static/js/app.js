// Donatily Frontend Interactive Utilities

document.addEventListener("DOMContentLoaded", function () {
    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll(".alert-dismissible");
    alerts.forEach((alert) => {
        setTimeout(() => {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) bsAlert.close();
        }, 5000);
    });

    // Confirmation dialogues for critical actions
    const confirmButtons = document.querySelectorAll("[data-confirm]");
    confirmButtons.forEach((btn) => {
        btn.addEventListener("click", function (e) {
            const message = this.getAttribute("data-confirm") || "Êtes-vous sûr de vouloir continuer ?";
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });
});
