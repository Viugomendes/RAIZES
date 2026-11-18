// The header: it steps aside while the page goes down, and the magnifier
// opens a search right there (names appear while typing).
// Without JavaScript the magnifier is a plain link to the search page.
(function (root, factory) {
  "use strict";
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.RaizesHeader = factory();
    root.RaizesHeader.start(root);
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var LIMIT = 8;

  // ----- What can be tested without a browser -----

  // The first `limit` people whose names match, and how many match in all.
  // Same matching as the search page (search.js): no accents, no capitals.
  function suggest(Search, index, text, limit) {
    if (!String(text || "").trim()) {
      return { people: [], total: 0 };
    }
    var found = Search.filterPeople(index, { text: text });
    // Names where a word starts with what was typed come first ("lia": Lia
    // before Amélia); each group stays in alphabetical order.
    var typed = Search.words(text);
    var starts = function (entry) {
      return typed.every(function (word) { return (" " + entry.names).indexOf(" " + word) !== -1; });
    };
    found = found.filter(starts).concat(found.filter(function (entry) { return !starts(entry); }));
    return {
      people: found.slice(0, limit || LIMIT).map(function (entry) { return entry.person; }),
      total: found.length,
    };
  }

  // The full search page with the text already typed in.
  function seeAllUrl(searchHref, text) {
    var base = String(searchHref).split(/[?#]/)[0];
    var typed = String(text || "").trim();
    return typed ? base + "?text=" + encodeURIComponent(typed) : base;
  }

  // The small line under the name: the nickname, or else the years.
  function detail(person) {
    if (person.nickname) {
      return "“" + person.nickname + "”";
    }
    return person.years || "";
  }

  // ----- Page -----

  function start(win) {
    var doc = win.document;
    if (!doc.getElementById("site-header")) {
      return;
    }
    function ready() {
      var reduced = win.matchMedia ? win.matchMedia("(prefers-reduced-motion: reduce)") : { matches: false };
      var search = quickSearch(win);
      stepAside(win, reduced, search);
    }
    if (doc.readyState === "loading") {
      doc.addEventListener("DOMContentLoaded", ready);
    } else {
      ready();
    }
  }

  // The bar hides while scrolling down and comes back on the way up; never
  // while the search is open, while something in it has the focus, or for
  // people who asked for less motion.
  function stepAside(win, reduced, search) {
    var doc = win.document;
    var header = doc.getElementById("site-header");
    var lastY = win.scrollY;
    var waiting = false;

    function show() {
      header.classList.remove("is-away");
    }

    function update() {
      waiting = false;
      var y = Math.max(0, win.scrollY);
      if (reduced.matches || search.isOpen() || header.contains(doc.activeElement)) {
        show();
        lastY = y;
        return;
      }
      if (y > lastY + 8 && y > header.offsetHeight) {
        header.classList.add("is-away");
        lastY = y;
      } else if (y < lastY - 8) {
        show();
        lastY = y;
      }
    }

    win.addEventListener("scroll", function () {
      if (!waiting) {
        waiting = true;
        win.requestAnimationFrame(update);
      }
    }, { passive: true });
    header.addEventListener("focusin", show);
  }

  function quickSearch(win) {
    var doc = win.document;
    var panel = doc.getElementById("quick-search");
    var input = doc.getElementById("quick-search-input");
    var list = doc.getElementById("quick-search-list");
    var status = doc.getElementById("quick-search-status");
    var closeButton = panel.querySelector(".quick-search-close");
    var strings = JSON.parse(doc.getElementById("header-strings").textContent);
    var magnifiers = doc.querySelectorAll(".nav-search");
    var searchHref = magnifiers.length ? magnifiers[0].href : "";
    var opener = null;
    var index = null;
    var loading = false;
    var failed = false;
    var options = [];
    var active = -1;

    function isOpen() {
      return !panel.hidden;
    }

    // The family data and the matching rules, fetched the first time only.
    function load(done) {
      if (loading) {
        return;
      }
      loading = true;
      var have = { RAIZES_DATA: win.RAIZES_DATA, Raizes: win.Raizes, RaizesSearch: win.RaizesSearch };
      var template = doc.getElementById("quick-search-scripts");
      var sources = Array.prototype.filter.call(template.content.querySelectorAll("script"), function (script) {
        return !have[script.getAttribute("data-provides")];
      }).map(function (script) {
        return script.getAttribute("src");
      });
      var left = sources.length;

      function finish() {
        loading = false;
        try {
          index = win.RaizesSearch.buildIndex(win.RAIZES_DATA);
        } catch (error) {
          failed = true;
        }
        done();
      }

      if (!left) {
        finish();
        return;
      }
      sources.forEach(function (src) {
        var script = doc.createElement("script");
        script.src = src;
        script.async = false; // run in the order of the list
        script.onload = function () {
          left -= 1;
          if (!left) {
            finish();
          }
        };
        script.onerror = function () {
          loading = false;
          failed = true;
          done();
        };
        doc.body.appendChild(script);
      });
    }

    function setActive(position) {
      active = position;
      options.forEach(function (option, i) {
        option.setAttribute("aria-selected", i === active ? "true" : "false");
      });
      if (active >= 0) {
        input.setAttribute("aria-activedescendant", options[active].id);
        if (options[active].scrollIntoView) {
          options[active].scrollIntoView({ block: "nearest" });
        }
      } else {
        input.removeAttribute("aria-activedescendant");
      }
    }

    function option(id, href, className) {
      var item = doc.createElement("li");
      item.setAttribute("role", "none");
      var link = doc.createElement("a");
      link.id = id;
      link.href = href;
      link.className = className;
      link.setAttribute("role", "option");
      link.setAttribute("aria-selected", "false");
      link.tabIndex = -1;
      item.appendChild(link);
      list.appendChild(item);
      options.push(link);
      return link;
    }

    function span(className, text) {
      var element = doc.createElement("span");
      element.className = className;
      element.textContent = text;
      return element;
    }

    function render() {
      var text = input.value;
      list.textContent = "";
      options = [];
      setActive(-1);
      if (!text.trim()) {
        list.hidden = true;
        input.setAttribute("aria-expanded", "false");
        status.textContent = "";
        return;
      }
      if (!index) {
        status.textContent = failed ? strings.failed : strings.loading;
      }
      if (index) {
        var root = win.Raizes.siteRoot(doc);
        var lang = doc.documentElement.getAttribute("data-lang");
        var found = suggest(win.RaizesSearch, index, text, LIMIT);
        found.people.forEach(function (person, i) {
          var link = option("quick-search-option-" + i, win.Raizes.pageUrl(root, lang + "/people/" + person.id + "/"), "quick-result");
          if (person.avatar) {
            var picture = doc.createElement("img");
            picture.className = "quick-avatar";
            picture.src = win.Raizes.fileUrl(root, person.avatar);
            picture.alt = "";
            picture.loading = "lazy";
            link.appendChild(picture);
          } else {
            var initials = span("quick-avatar quick-initials", person.initials || "");
            initials.setAttribute("aria-hidden", "true");
            link.appendChild(initials);
          }
          var words = span("quick-text", "");
          words.appendChild(span("quick-name", person.name));
          var small = detail(person);
          if (small) {
            words.appendChild(span("quick-detail", small));
          }
          link.appendChild(words);
        });
        status.textContent = found.total
          ? win.Raizes.format(win.Raizes.plural(strings.results, found.total), { count: found.total })
          : strings.noResults;
        if (!found.total) {
          var empty = doc.createElement("li");
          empty.setAttribute("role", "none");
          empty.className = "quick-empty";
          empty.textContent = strings.noResults;
          list.appendChild(empty);
        }
      }
      var all = option("quick-search-option-all", seeAllUrl(searchHref, text), "quick-all");
      all.textContent = strings.seeAll;
      list.hidden = false;
      input.setAttribute("aria-expanded", "true");
    }

    function open(from) {
      opener = from;
      panel.hidden = false;
      doc.documentElement.classList.add("quick-search-open");
      input.focus();
      if (input.value) {
        input.select();
      }
      render();
      if (!index && !failed) {
        load(render);
      }
    }

    function close(returnFocus) {
      if (!isOpen()) {
        return;
      }
      panel.hidden = true;
      doc.documentElement.classList.remove("quick-search-open");
      list.hidden = true;
      input.setAttribute("aria-expanded", "false");
      setActive(-1);
      if (returnFocus && opener) {
        opener.focus();
      }
    }

    function go(href) {
      win.location.href = href;
    }

    Array.prototype.forEach.call(magnifiers, function (magnifier) {
      magnifier.addEventListener("click", function (event) {
        // Ctrl/Cmd/Shift+click, middle click: the search page, as a link does.
        if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
          return;
        }
        event.preventDefault();
        // On the search page itself, its own field is already there.
        var pageField = doc.querySelector("#search-form:not([hidden]) input[name='text']");
        if (pageField) {
          pageField.focus();
          return;
        }
        open(magnifier);
      });
    });

    input.addEventListener("input", render);
    input.addEventListener("keydown", function (event) {
      if (event.key === "ArrowDown" || event.key === "ArrowUp") {
        if (!options.length) {
          return;
        }
        event.preventDefault();
        var step = event.key === "ArrowDown" ? 1 : -1;
        var count = options.length;
        if (active === -1) {
          setActive(step === 1 ? 0 : count - 1);
        } else {
          setActive((active + step + count) % count);
        }
      } else if (event.key === "Enter") {
        event.preventDefault();
        if (active >= 0) {
          go(options[active].href);
        } else if (input.value.trim()) {
          go(seeAllUrl(searchHref, input.value));
        }
      } else if (event.key === "Escape") {
        event.preventDefault();
        close(true);
      }
    });
    panel.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        close(true);
      }
    });
    closeButton.addEventListener("click", function () {
      close(true);
    });
    // A click outside closes it, without taking the focus anywhere.
    doc.addEventListener("pointerdown", function (event) {
      if (isOpen() && !panel.contains(event.target) && !event.target.closest(".nav-search")) {
        close(false);
      }
    });

    return { isOpen: isOpen };
  }

  return { suggest: suggest, seeAllUrl: seeAllUrl, detail: detail, start: start };
});
