// Light or dark theme, like the panel: auto -> light/dark -> auto, saved in
// localStorage "theme" (the same key as the panel, so both follow one choice).
// Loaded in <head> without "defer": the theme is set before the page is drawn.
(function (root, factory) {
  "use strict";
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.RaizesTheme = factory();
    root.RaizesTheme.start(root);
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var THEMES = ["auto", "light", "dark"];

  // The same order as the panel: the first click always changes what is seen.
  function nextTheme(current, prefersDark) {
    if (prefersDark) {
      return { auto: "light", light: "dark" }[current] || "auto";
    }
    return { auto: "dark", dark: "light" }[current] || "auto";
  }

  function valid(theme) {
    return THEMES.indexOf(theme) === -1 ? "auto" : theme;
  }

  function start(win) {
    var html = win.document.documentElement;
    var saved = null;
    try {
      saved = win.localStorage.getItem("theme");
    } catch (error) {
      // Storage blocked (private window): the theme follows the device.
    }
    html.setAttribute("data-theme", valid(saved));

    // One listener for the whole page: it works before the button exists.
    win.document.addEventListener("click", function (event) {
      var button = event.target.closest ? event.target.closest(".theme-toggle") : null;
      if (!button) {
        return;
      }
      var prefersDark = win.matchMedia && win.matchMedia("(prefers-color-scheme: dark)").matches;
      var theme = nextTheme(valid(html.getAttribute("data-theme")), prefersDark);
      html.setAttribute("data-theme", theme);
      try {
        win.localStorage.setItem("theme", theme);
      } catch (error) {
        // Not saved: it lasts until the next page.
      }
    });
  }

  return { nextTheme: nextTheme, start: start };
});
