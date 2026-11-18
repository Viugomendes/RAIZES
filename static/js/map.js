// The family map: every place, with the people linked to it, filtered by
// generation (counted from the central person).
(function () {
  "use strict";

  var data = window.RAIZES_DATA;
  var element = document.getElementById("family-map");
  if (!data || !window.L || !element) {
    return;
  }
  var R = window.Raizes;
  var strings = JSON.parse(document.getElementById("map-strings").textContent);
  var lang = document.documentElement.getAttribute("data-lang");
  var root = R.siteRoot(document);
  var people = R.byId(data.people);
  var kin = data.central ? new window.RaizesKinship.FamilyGraph(data).walk(data.central) : null;
  var COLOUR = "#3f5a36";

  // ----- Filter by generation -----
  var generationSelect = document.getElementById("map-generation");
  var options = [["", R.escapeHtml(strings.allGenerations)]];
  if (kin) {
    var centralName = people[data.central].name;
    var generations = {};
    Object.keys(kin.generation).forEach(function (id) {
      generations[kin.generation[id]] = true;
    });
    Object.keys(generations).map(Number).sort(function (a, b) {
      return a - b;
    }).forEach(function (value) {
      var label = strings.generations[String(value)] || strings.generationOther;
      options.push([String(value), R.format(label, { name: centralName, number: value })]);
    });
  }
  generationSelect.innerHTML = options.map(function (option) {
    // The labels come from R.format, which already escaped the names.
    return '<option value="' + R.escapeHtml(option[0]) + '">' + option[1] + "</option>";
  }).join("");
  document.getElementById("map-filters").hidden = !kin;

  // ----- Map -----
  var map = window.RaizesPlaces.baseMap(window.L, element);
  var layer = window.L.layerGroup().addTo(map);
  var markersBySlug = {};

  function draw() {
    var generation = generationSelect.value;
    var chosen = data.people.filter(function (person) {
      return generation === "" || (kin && String(kin.generation[person.id]) === generation);
    });
    var byPlace = window.RaizesPlaces.peopleByPlace(chosen);
    layer.clearLayers();
    markersBySlug = {};
    var bounds = [];
    Object.keys(byPlace).forEach(function (slug) {
      var place = data.places[slug];
      if (!place || place.lat === null || place.lon === null) {
        return;
      }
      var entries = byPlace[slug];
      var marker = window.L.circleMarker([place.lat, place.lon], {
        radius: Math.min(24, 7 + Math.sqrt(entries.length) * 4),
        color: "#ffffff",
        weight: 2,
        fillColor: COLOUR,
        fillOpacity: 0.85,
      });
      var list = entries.map(function (entry) {
        var person = people[entry.person];
        var roles = entry.roles.map(function (role) {
          return strings.roles[role];
        }).join(", ");
        return '<li><a href="' + R.escapeHtml(R.pageUrl(root, lang + "/people/" + person.id + "/")) + '">' + R.escapeHtml(person.name) + '</a> <span class="muted">' + R.escapeHtml(roles) + "</span></li>";
      }).join("");
      marker.bindPopup(
        "<strong>" + R.escapeHtml(place.name) + "</strong><br>" + R.format(R.plural(strings.people, entries.length), { count: entries.length }) + '<ul class="map-people">' + list + "</ul>",
        { maxHeight: 260 }
      );
      marker.addTo(layer);
      markersBySlug[slug] = marker;
      bounds.push([place.lat, place.lon]);
    });
    document.getElementById("map-count").textContent = bounds.length ? "" : strings.noPlaces;
    if (bounds.length) {
      map.fitBounds(bounds, { padding: [40, 40], maxZoom: 8 });
    } else {
      map.setView([0, 0], 2);
    }
  }

  generationSelect.addEventListener("change", draw);
  draw();

  // A link like ".../tree/map/#place-valencia" opens that place.
  var match = /^#place-(.+)$/.exec(window.location.hash);
  if (match && markersBySlug[match[1]]) {
    var marker = markersBySlug[match[1]];
    map.setView(marker.getLatLng(), 9);
    marker.openPopup();
  }
})();
