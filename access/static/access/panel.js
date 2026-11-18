// Every panel page (access/templates/admin/base_site.html): names for two fields
// that Django leaves without a label of their own.
// - The search box that the autocomplete adds to a multiple choice ("Lived in").
// - A file field ("Main photo"), which Django puts in a fieldset with a legend.
(function () {
  "use strict";

  function fieldName(text) {
    return text.replace(/:\s*$/, "").trim();
  }

  function nameFields() {
    document.querySelectorAll("select.admin-autocomplete[multiple]").forEach(function (select) {
      var label = document.querySelector('label[for="' + select.id + '"]');
      var box = select.parentNode.querySelector(".select2-search__field");
      if (label && box) {
        box.setAttribute("aria-label", fieldName(label.textContent));
      }
    });
    document.querySelectorAll('fieldset input[type="file"]').forEach(function (input) {
      var legend = input.closest("fieldset").querySelector("legend");
      if (legend && !input.labels.length && !input.hasAttribute("aria-label")) {
        input.setAttribute("aria-label", fieldName(legend.textContent));
      }
    });
  }

  // Django starts the autocomplete in a jQuery "ready" handler: ours runs after it.
  if (window.django && window.django.jQuery) {
    window.django.jQuery(nameFields);
  } else {
    nameFields();
  }
  document.addEventListener("formset:added", function () {
    window.setTimeout(nameFields, 0);
  });
})();
