// Opens a photo in large size over the page, with its caption. Without this
// script the link still works: it opens the photo on its own.
(function () {
  "use strict";

  var dialog = null;

  function build() {
    dialog = document.createElement("dialog");
    dialog.className = "lightbox";
    dialog.innerHTML =
      '<form method="dialog"><button class="lightbox-close" aria-label="×">×</button></form>' +
      '<img alt=""><p class="lightbox-caption"></p>';
    dialog.addEventListener("click", function (event) {
      if (event.target === dialog) {
        dialog.close();
      }
    });
    document.body.appendChild(dialog);
  }

  document.addEventListener("click", function (event) {
    var link = event.target.closest && event.target.closest("a.photo-link");
    if (!link || typeof HTMLDialogElement === "undefined") {
      return;
    }
    event.preventDefault();
    if (!dialog) {
      build();
    }
    var caption = link.getAttribute("data-caption") || "";
    var image = dialog.querySelector("img");
    image.src = link.getAttribute("href");
    image.alt = caption;
    dialog.querySelector(".lightbox-caption").textContent = caption;
    dialog.showModal();
  });
})();
