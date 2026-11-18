/* TECHWANDO progressive UI enhancements (navigation, alerts, file checks) */
(function () {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    const toggle = document.querySelector("[data-nav-toggle]");
    const menu = document.querySelector("[data-nav-menu]");
    if (toggle && menu) {
      toggle.addEventListener("click", function () {
        const isOpen = menu.classList.toggle("is-open");
        toggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
      });
    }

    // Client-side file size hint (complementing mandatory server-side validation)
    const maxBytes = 5 * 1024 * 1024;
    document.querySelectorAll('input[type="file"]').forEach(function (input) {
      input.addEventListener("change", function () {
        const file = input.files && input.files[0];
        if (file && file.size > maxBytes) {
          input.setCustomValidity("5MB max");
          input.reportValidity();
        } else {
          input.setCustomValidity("");
        }
      });
    });
  });
})();
