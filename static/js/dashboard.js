/* ==========================================================================
   TEAKWONDO — Dashboard enhancements
   The dashboard is fully usable without this file; it only adds conveniences.
   ========================================================================== */
(function () {
  "use strict";

  var doc = document;

  /* Keep the mobile sidebar scroll position usable and close it after a link
     is followed (backup for browsers without Bootstrap's data API). */
  doc.querySelectorAll(".dashboard-offcanvas .sidebar-nav a").forEach(function (link) {
    link.addEventListener("click", function () {
      var offcanvasElement = link.closest(".offcanvas");
      if (offcanvasElement && window.bootstrap) {
        var instance = window.bootstrap.Offcanvas.getInstance(offcanvasElement);
        if (instance) instance.hide();
      }
    });
  });

  /* Add horizontal-scroll affordance to wide tables. */
  doc.querySelectorAll(".table-wrap").forEach(function (wrapper) {
    var table = wrapper.querySelector("table");
    if (!table) return;
    var update = function () {
      var scrollable = wrapper.scrollWidth > wrapper.clientWidth + 4;
      wrapper.classList.toggle("is-scrollable", scrollable);
      wrapper.setAttribute("tabindex", scrollable ? "0" : "-1");
      if (scrollable) {
        wrapper.setAttribute("role", "region");
        wrapper.setAttribute("aria-label", doc.body.getAttribute("data-scroll-label") || "Scrollable table");
      }
    };
    update();
    window.addEventListener("resize", update);
  });

  /* Status filter shortcuts: keep the URL shareable. */
  doc.querySelectorAll("[data-status-filter]").forEach(function (select) {
    select.addEventListener("change", function () {
      if (select.form) select.form.submit();
    });
  });

  /* Focus the first invalid field after a failed POST. */
  var invalid = doc.querySelector(".field-has-error input, .field-has-error select, .field-has-error textarea");
  if (invalid && !doc.querySelector(".error-summary")) {
    invalid.focus({ preventScroll: false });
  }
})();
