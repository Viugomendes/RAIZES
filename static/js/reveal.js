// "Show password" on /entrar/ and on the panel login (access/templates/access/_reveal.html).
// The button stays hidden without JavaScript; its label never changes and
// aria-pressed says whether the password is shown.
(function () {
  "use strict";

  document.querySelectorAll("[data-reveal]").forEach(function (button) {
    var field = document.getElementById(button.getAttribute("aria-controls"));
    if (!field) {
      return;
    }
    button.hidden = false;
    button.addEventListener("click", function () {
      var show = field.type === "password";
      field.type = show ? "text" : "password";
      button.setAttribute("aria-pressed", String(show));
    });
    // Sent as a password field, so the browser never keeps it as plain text.
    if (field.form) {
      field.form.addEventListener("submit", function () {
        field.type = "password";
        button.setAttribute("aria-pressed", "false");
      });
    }
  });
})();
