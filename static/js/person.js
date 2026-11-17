// Page of a person.
(function () {
  "use strict";

  // A click on an interview minute, like [04:12], starts the video on this
  // page at that moment instead of opening YouTube.
  var player = document.getElementById("interview-player");
  if (player) {
    document.addEventListener("click", function (event) {
      var link = event.target.closest("a.timestamp");
      if (!link) {
        return;
      }
      var seconds = parseInt(link.getAttribute("data-seconds"), 10);
      if (isNaN(seconds)) {
        return;
      }
      event.preventDefault();
      player.src = player.getAttribute("data-embed-url") + "?start=" + seconds + "&autoplay=1";
      player.scrollIntoView({ behavior: "smooth", block: "center" });
    });
  }

  // The personal map: every place of this life, with what happened there.
  var element = document.getElementById("personal-map");
  var source = document.getElementById("personal-places");
  if (element && source && window.L && window.RaizesPlaces) {
    var places = JSON.parse(source.textContent);
    var map = window.RaizesPlaces.baseMap(window.L, element);
    var bounds = [];
    places.forEach(function (place) {
      var marker = window.L.circleMarker([place.lat, place.lon], {
        radius: 9,
        color: "#ffffff",
        weight: 2,
        fillColor: "#3f5a36",
        fillOpacity: 0.9,
      }).addTo(map);
      var popup = document.createElement("div");
      var name = document.createElement("strong");
      name.textContent = place.name;
      popup.appendChild(name);
      popup.appendChild(document.createElement("br"));
      popup.appendChild(document.createTextNode(place.roles.join(", ")));
      marker.bindPopup(popup);
      bounds.push([place.lat, place.lon]);
    });
    if (bounds.length === 1) {
      map.setView(bounds[0], 7);
    } else {
      map.fitBounds(bounds, { padding: [30, 30], maxZoom: 8 });
    }
  }
})();
