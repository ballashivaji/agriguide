// AgriGuide - small UX helpers

document.addEventListener("DOMContentLoaded", () => {
  // Auto-dismiss flash messages after a few seconds
  document.querySelectorAll(".flash").forEach((el) => {
    setTimeout(() => {
      el.style.transition = "opacity 0.4s ease";
      el.style.opacity = "0";
      setTimeout(() => el.remove(), 400);
    }, 4000);
  });

  // Toggle password visibility (inputs with a sibling .toggle-pass icon)
  document.querySelectorAll(".toggle-pass").forEach((btn) => {
    btn.addEventListener("click", () => {
      const input = btn.parentElement.querySelector("input");
      if (!input) return;
      input.type = input.type === "password" ? "text" : "password";
      btn.textContent = input.type === "password" ? "\u{1F441}" : "\u{1F576}";
    });
  });

  // Simple client-side confirm for delete links in admin tables
  document.querySelectorAll("a.confirm-delete").forEach((link) => {
    link.addEventListener("click", (e) => {
      if (!confirm("Are you sure you want to delete this item?")) {
        e.preventDefault();
      }
    });
  });
});
