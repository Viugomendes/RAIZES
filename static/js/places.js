// Where each person is linked to each place, and the Leaflet helpers shared
// by the family map and the personal map of a person's page.
(function (root, factory) {
  "use strict";
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.RaizesPlaces = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var ROLES = [
    ["birthPlace", "birth"],
    ["livedIn", "lived"],
    ["livesIn", "lives"],
    ["deathPlace", "death"],
    ["restingPlace", "resting"],
  ];

  // {slug: [{person, roles: [...]}, ...]} for the people given.
  function peopleByPlace(people) {
    var result = {};
    people.forEach(function (person) {
      var found = {};
      ROLES.forEach(function (pair) {
        var value = person[pair[0]];
        var slugs = Array.isArray(value) ? value : value ? [value] : [];
        slugs.forEach(function (slug) {
          (found[slug] = found[slug] || []).push(pair[1]);
        });
      });
      Object.keys(found).forEach(function (slug) {
        (result[slug] = result[slug] || []).push({ person: person.id, roles: found[slug] });
      });
    });
    return result;
  }

  // A map that never traps the page: like the tree, the plain mouse wheel
  // and one finger scroll the page; Ctrl + wheel, two fingers, the + and -
  // buttons or the full screen move and zoom the map. The texts of the hints
  // come from data-* attributes of the element, already translated.
  function baseMap(L, element, options) {
    var texts = element.dataset;
    var map = L.map(element, Object.assign({ scrollWheelZoom: false, worldCopyJump: true }, options || {}));
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18,
      // OpenStreetMap asks to know which site shows its map (only the site, not the page).
      referrerPolicy: "strict-origin-when-cross-origin",
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(map);

    // Phones and tablets; a laptop with a touch screen keeps mouse dragging.
    var touch = L.Browser.mobile;
    var full = false;

    var hint = document.createElement("p");
    hint.className = "map-hint";
    hint.setAttribute("aria-live", "polite");
    element.appendChild(hint);
    var timer = null;
    function showHint(text) {
      if (!text) {
        return;
      }
      hint.textContent = text;
      hint.classList.add("visible");
      clearTimeout(timer);
      timer = setTimeout(function () {
        hint.classList.remove("visible");
      }, 2200);
    }

    // One finger scrolls the page on phones (two fingers still zoom and move).
    if (touch) {
      map.dragging.disable();
    }

    element.addEventListener(
      "wheel",
      function (event) {
        if (full) {
          return; // Leaflet's own wheel zoom is on in full screen
        }
        if (!event.ctrlKey && !event.metaKey) {
          showHint(texts.hintWheel);
          return;
        }
        event.preventDefault();
        var zoom = map.getZoom() + (event.deltaY < 0 ? 1 : -1);
        map.setZoomAround(map.mouseEventToContainerPoint(event), zoom);
      },
      { passive: false }
    );
    element.addEventListener("touchstart", function (event) {
      if (!full && event.touches.length === 1) {
        showHint(texts.hintTouch);
      }
    }, { passive: true });

    function setFull(on) {
      full = on;
      element.classList.toggle("is-full", on);
      document.body.classList.toggle("map-is-full", on);
      button.textContent = on ? texts.exitFull : texts.full;
      button.setAttribute("aria-pressed", on ? "true" : "false");
      if (on) {
        map.scrollWheelZoom.enable();
        map.dragging.enable();
      } else {
        map.scrollWheelZoom.disable();
        if (touch) {
          map.dragging.disable();
        }
      }
      map.invalidateSize();
    }

    var FullControl = L.Control.extend({
      options: { position: "topright" },
      onAdd: function () {
        var box = L.DomUtil.create("div", "leaflet-bar map-full-control");
        L.DomEvent.disableClickPropagation(box);
        box.appendChild(button);
        return box;
      },
    });
    var button = document.createElement("button");
    button.type = "button";
    button.className = "map-full-button";
    button.textContent = texts.full || "⛶";
    button.setAttribute("aria-pressed", "false");
    button.addEventListener("click", function () {
      setFull(!full);
    });
    new FullControl().addTo(map);
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && full) {
        setFull(false);
      }
    });

    return map;
  }

  return { peopleByPlace: peopleByPlace, baseMap: baseMap, ROLES: ROLES };
});
