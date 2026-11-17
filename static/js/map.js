// The family map: every place, with the people linked to it, filtered by
// side and generation (counted from the central person).
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
  var graph = new window.RaizesKinship.FamilyGraph(data);
  var kin = data.central ? graph.walk(data.central) : null;
  var CENTER = window.RaizesKinship.CENTER;

  function sideColor(side) {
    if (!kin || side === undefined) {
      return data.colors.unlinked;
    }
    if (side === CENTER) {
      return data.colors.center;
    }
    var index = kin.figures.indexOf(side);
    return index < data.colors.sides.length ? data.colors.sides[index] : data.colors.otherSides;
  }

  // ----- Filters -----
  var sideSelect = document.getElementById("map-side");
  var generationSelect = document.getElementById("map-generation");
  var sideOptions = [["", strings.allSides]];
  var generationOptions = [["", strings.allGenerations]];
  if (kin) {
    var centralName = people[data.central].name;
    kin.figures.forEach(function (figure) {
      sideOptions.push([figure, R.format(strings.side, { name: people[figure].name })]);
    });
    sideOptions.push([CENTER, R.format(strings.center, { name: centralName })]);
    var generations = {};
    Object.keys(kin.generation).forEach(function (id) {
      generations[kin.generation[id]] = true;
    });
    Object.keys(generations).map(Number).sort(function (a, b) {
      return a - b;
    }).forEach(function (value) {
      var label = strings.generations[String(value)] || strings.generationOther;
      generationOptions.push([String(value), R.format(label, { name: centralName, number: value })]);
    });
  }
  function fill(select, options) {
    select.innerHTML = options.map(function (option) {
      return '<option value="' + R.escapeHtml(option[0]) + '">' + R.escapeHtml(option[1]) + "</option>";
    }).join("");
  }
  fill(sideSelect, sideOptions);
  fill(generationSelect, generationOptions);
  document.getElementById("map-filters").hidden = !kin;

  // ----- Map -----
  var map = window.RaizesPlaces.baseMap(window.L, element);
  var layer = window.L.layerGroup().addTo(map);
  var markersBySlug = {};

  function draw() {
    var side = sideSelect.value;
    var generation = generationSelect.value;
    var chosen = data.people.filter(function (person) {
      if (side && (!kin || kin.side[person.id] !== side)) {
        return false;
      }
      if (generation !== "" && (!kin || String(kin.generation[person.id]) !== generation)) {
        return false;
      }
      return true;
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
      var colours = {};
      entries.forEach(function (entry) {
        colours[sideColor(kin ? kin.side[entry.person] : undefined)] = true;
      });
      var colourList = Object.keys(colours);
      var marker = window.L.circleMarker([place.lat, place.lon], {
        radius: Math.min(24, 7 + Math.sqrt(entries.length) * 4),
        color: "#ffffff",
        weight: 2,
        fillColor: colourList.length === 1 ? colourList[0] : data.colors.center,
        fillOpacity: 0.85,
      });
      var list = entries.map(function (entry) {
        var person = people[entry.person];
        var roles = entry.roles.map(function (role) {
          return strings.roles[role];
        }).join(", ");
        return '<li><a href="' + R.pageUrl(root, lang + "/people/" + person.id + "/") + '">' + R.escapeHtml(person.name) + "</a> <span class=\"muted\">" + R.escapeHtml(roles) + "</span></li>";
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

  sideSelect.addEventListener("change", draw);
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
