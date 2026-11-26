/* ==========================================================================
   TEAKWONDO — Progressive front-end enhancements (vanilla JavaScript)
   Everything here is optional: navigation, forms and server-side validation
   continue to work when JavaScript is unavailable.
   ========================================================================== */
(function () {
  "use strict";

  var doc = document;
  var root = doc.documentElement;

  /* ---------------------------------------------------------------------
     Theme (light / dark) — remembered per browser
     --------------------------------------------------------------------- */
  var STORAGE_KEY = "teakwondo-theme";

  function applyTheme(theme) {
    if (theme === "dark") {
      root.setAttribute("data-theme", "dark");
    } else {
      root.removeAttribute("data-theme");
    }
    doc.querySelectorAll("[data-theme-toggle]").forEach(function (button) {
      var isDark = theme === "dark";
      button.setAttribute("aria-pressed", isDark ? "true" : "false");
      var icon = button.querySelector("[data-theme-icon]");
      if (icon) {
        icon.className = isDark ? "bi bi-sun" : "bi bi-moon-stars";
      }
    });
  }

  function storedTheme() {
    try {
      return window.localStorage.getItem(STORAGE_KEY);
    } catch (error) {
      return null;
    }
  }

  applyTheme(storedTheme());

  doc.addEventListener("click", function (event) {
    var toggle = event.target.closest("[data-theme-toggle]");
    if (!toggle) return;
    var next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
    applyTheme(next);
    try {
      window.localStorage.setItem(STORAGE_KEY, next);
    } catch (error) {
      /* Storage may be blocked — theme simply won't persist. */
    }
  });

  /* ---------------------------------------------------------------------
     Password visibility toggle
     --------------------------------------------------------------------- */
  doc.addEventListener("click", function (event) {
    var button = event.target.closest("[data-password-toggle]");
    if (!button) return;
    var field = doc.getElementById(button.getAttribute("aria-controls"));
    if (!field) return;
    var show = field.type === "password";
    field.type = show ? "text" : "password";
    button.setAttribute("aria-pressed", show ? "true" : "false");
    button.setAttribute(
      "aria-label",
      show ? button.dataset.hideLabel || "Hide password" : button.dataset.showLabel || "Show password"
    );
    var icon = button.querySelector("i");
    if (icon) {
      icon.className = show ? "bi bi-eye-slash" : "bi bi-eye";
    }
  });

  /* ---------------------------------------------------------------------
     Image upload preview
     --------------------------------------------------------------------- */
  doc.querySelectorAll("[data-image-preview]").forEach(function (wrapper) {
    var input = wrapper.querySelector('input[type="file"]');
    var image = wrapper.querySelector("[data-image-preview-target]");
    if (!input || !image) return;
    input.addEventListener("change", function () {
      var file = input.files && input.files[0];
      if (!file || !/^image\//.test(file.type)) return;
      var url = URL.createObjectURL(file);
      image.src = url;
      image.onload = function () {
        URL.revokeObjectURL(url);
      };
    });
  });

  /* ---------------------------------------------------------------------
     Accessible confirmation dialog for destructive actions
     --------------------------------------------------------------------- */
  var confirmElement = doc.getElementById("confirmDialog");
  var pendingAction = null;

  function confirmDialog() {
    if (!confirmElement || !window.bootstrap) return null;
    return window.bootstrap.Modal.getOrCreateInstance(confirmElement);
  }

  function askConfirm(message, action) {
    var modal = confirmDialog();
    if (!modal) {
      if (window.confirm(message)) action();
      return;
    }
    var body = confirmElement.querySelector("[data-confirm-message]");
    if (body) body.textContent = message;
    pendingAction = action;
    modal.show();
  }

  if (confirmElement) {
    var accept = confirmElement.querySelector("[data-confirm-accept]");
    if (accept) {
      accept.addEventListener("click", function () {
        var action = pendingAction;
        pendingAction = null;
        confirmDialog().hide();
        if (typeof action === "function") action();
      });
    }
    confirmElement.addEventListener("hidden.bs.modal", function () {
      pendingAction = null;
    });
  }

  doc.addEventListener("click", function (event) {
    var trigger = event.target.closest("[data-confirm]");
    if (!trigger) return;
    event.preventDefault();
    var message = trigger.getAttribute("data-confirm") || "Are you sure?";
    var href = trigger.getAttribute("href");
    var form = trigger.closest("form");
    askConfirm(message, function () {
      if (href) {
        window.location.href = href;
      } else if (form) {
        form.submit();
      } else if (trigger.tagName === "BUTTON") {
        trigger.disabled = false;
        trigger.removeAttribute("data-confirm");
        trigger.click();
      }
    });
  });

  /* ---------------------------------------------------------------------
     Form accessibility enhancements (server-side errors stay authoritative)
     --------------------------------------------------------------------- */
  doc.querySelectorAll(".form-error").forEach(function (error) {
    var group = error.closest(".form-group, .form-check");
    if (!group) return;
    var input = group.querySelector("input, select, textarea");
    if (!input) return;
    input.setAttribute("aria-invalid", "true");
    if (error.id) {
      var describedBy = input.getAttribute("aria-describedby");
      input.setAttribute(
        "aria-describedby",
        describedBy ? describedBy + " " + error.id : error.id
      );
    }
  });

  var firstError = doc.querySelector(".field-has-error input, .field-has-error select, .field-has-error textarea");
  if (firstError && doc.querySelector(".error-summary")) {
    firstError.focus({ preventScroll: false });
  }

  /* Disable double submission while keeping Enter-key behaviour intact. */
  doc.querySelectorAll("form").forEach(function (form) {
    form.addEventListener("submit", function () {
      var submit = form.querySelector('button[type="submit"], input[type="submit"]');
      if (!submit) return;
      window.setTimeout(function () {
        submit.disabled = true;
        submit.classList.add("disabled");
      }, 0);
    });
  });

  /* ---------------------------------------------------------------------
     Filter bars: submit automatically on select change (optional)
     --------------------------------------------------------------------- */
  doc.querySelectorAll("[data-auto-submit] select").forEach(function (select) {
    select.addEventListener("change", function () {
      if (select.form) select.form.submit();
    });
  });

  /* ---------------------------------------------------------------------
     Back-to-top button
     --------------------------------------------------------------------- */
  var backToTop = doc.querySelector("[data-back-to-top]");
  if (backToTop) {
    var updateBackToTop = function () {
      backToTop.classList.toggle("is-visible", window.scrollY > 500);
    };
    window.addEventListener("scroll", updateBackToTop, { passive: true });
    updateBackToTop();
    backToTop.addEventListener("click", function () {
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  }

  /* ---------------------------------------------------------------------
     Homepage scroll depth and section reveals
     --------------------------------------------------------------------- */
  var prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var depthItems = doc.querySelectorAll("[data-scroll-depth]");

  if (depthItems.length && !prefersReducedMotion) {
    var depthFrame = 0;
    var updateDepth = function () {
      depthFrame = 0;
      depthItems.forEach(function (item) {
        var rect = item.getBoundingClientRect();
        var progress = Math.max(0, Math.min(1, -rect.top / Math.max(rect.height, 1)));
        item.style.setProperty("--hero-scroll-y", (-progress * 30).toFixed(1) + "px");
      });
    };
    var requestDepthUpdate = function () {
      if (!depthFrame) depthFrame = window.requestAnimationFrame(updateDepth);
    };

    window.addEventListener("scroll", requestDepthUpdate, { passive: true });
    window.addEventListener("resize", requestDepthUpdate, { passive: true });
    updateDepth();
  }

  var revealItems = doc.querySelectorAll(".home-page [data-scroll-reveal]");
  if (revealItems.length && "IntersectionObserver" in window && !prefersReducedMotion) {
    var revealObserver = new IntersectionObserver(function (entries, observer) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-visible");
        observer.unobserve(entry.target);
      });
    }, { threshold: 0.12, rootMargin: "0px 0px -24px 0px" });

    root.classList.add("has-scroll-reveal");
    revealItems.forEach(function (item) {
      revealObserver.observe(item);
    });
  }

  /* ---------------------------------------------------------------------
     Auto-dismiss confirmation alerts (success / info only)
     --------------------------------------------------------------------- */
  doc.querySelectorAll(".messages-stack .alert-success, .messages-stack .alert-info").forEach(function (alert) {
    window.setTimeout(function () {
      if (!window.bootstrap) return;
      var instance = window.bootstrap.Alert.getOrCreateInstance(alert);
      instance.close();
    }, 7000);
  });

  /* ---------------------------------------------------------------------
     Gallery lightbox (progressive enhancement — links work without JS)
     --------------------------------------------------------------------- */
  var lightboxElement = doc.getElementById("galleryLightbox");
  if (lightboxElement && window.bootstrap) {
    var lightboxModal = window.bootstrap.Modal.getOrCreateInstance(lightboxElement);
    var lightboxImage = lightboxElement.querySelector("[data-lightbox-image]");
    var lightboxCaption = lightboxElement.querySelector("[data-lightbox-caption]");
    var lightboxTrigger = null;

    doc.addEventListener("click", function (event) {
      var trigger = event.target.closest("[data-lightbox]");
      if (!trigger || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      var src = trigger.getAttribute("data-lightbox-src") || trigger.getAttribute("href");
      if (!src || !lightboxImage) return;
      event.preventDefault();
      lightboxTrigger = trigger;
      lightboxImage.src = src;
      lightboxImage.alt = trigger.getAttribute("data-lightbox-alt") || "";
      if (lightboxCaption) {
        lightboxCaption.textContent = trigger.getAttribute("data-lightbox-caption") || "";
      }
      lightboxModal.show();
    });

    lightboxElement.addEventListener("hidden.bs.modal", function () {
      if (lightboxImage) {
        lightboxImage.src = "data:image/gif;base64,R0lGODlhAQABAAAAACw=";
        lightboxImage.alt = "";
      }
      if (lightboxCaption) lightboxCaption.textContent = "";
      if (lightboxTrigger) lightboxTrigger.focus();
      lightboxTrigger = null;
    });
  }

  /* ---------------------------------------------------------------------
     Remember the last dashboard section in the mobile menu? Not needed:
     Bootstrap offcanvas closes on navigation because the page reloads.
     --------------------------------------------------------------------- */
})();
