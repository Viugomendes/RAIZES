// Small helpers shared by the scripts of the site.
(function (root, factory) {
  "use strict";
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.Raizes = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  // Fill "%(name)s" placeholders. Values are escaped unless marked as HTML.
  function format(template, values, html) {
    return template.replace(/%\((\w+)\)s/g, function (all, key) {
      if (!(key in values)) {
        return all;
      }
      var value = values[key];
      return html && html[key] ? String(value) : escapeHtml(String(value));
    });
  }

  function plural(forms, count) {
    return count === 1 ? forms.one : forms.other;
  }

  function escapeHtml(text) {
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  // Lowercase, without accents: "Álvaro" -> "alvaro".
  function normalize(text) {
    return String(text || "")
      .normalize("NFD")
      .replace(/[̀-ͯ]/g, "")
      .toLowerCase()
      .trim();
  }

  // Where the root of the site is. While working locally it is "/"; in the
  // exported site it is a relative path ending in "index.html".
  function siteRoot(doc) {
    var value = doc.documentElement.getAttribute("data-root") || "/";
    return {
      prefix: value.replace(/index\.html$/, ""),
      isStatic: /index\.html$/.test(value),
    };
  }

  // Address of a page, from a path like "pt-br/people/lia-1996/".
  function pageUrl(root, path) {
    return root.prefix + path + (root.isStatic && /\/$/.test(path) ? "index.html" : "");
  }

  function fileUrl(root, path) {
    return root.prefix + path;
  }

  function byId(list, key) {
    var map = {};
    list.forEach(function (item) {
      map[item[key || "id"]] = item;
    });
    return map;
  }

  return {
    format: format,
    plural: plural,
    escapeHtml: escapeHtml,
    normalize: normalize,
    siteRoot: siteRoot,
    pageUrl: pageUrl,
    fileUrl: fileUrl,
    byId: byId,
  };
});
