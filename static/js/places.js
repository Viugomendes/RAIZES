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

  // Tiles of OpenStreetMap; everything else of the map is inside the site.
  function baseMap(L, element, options) {
    var map = L.map(element, Object.assign({ scrollWheelZoom: false, worldCopyJump: true }, options || {}));
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(map);
    // The wheel scrolls the page until the map is clicked.
    map.on("click focus", function () {
      map.scrollWheelZoom.enable();
    });
    map.on("blur mouseout", function () {
      map.scrollWheelZoom.disable();
    });
    return map;
  }

  return { peopleByPlace: peopleByPlace, baseMap: baseMap, ROLES: ROLES };
});
