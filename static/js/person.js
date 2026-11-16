// Page of a person: a click on an interview minute, like [04:12], starts the
// video on this page at that moment instead of opening YouTube.
(function () {
  "use strict";

  var player = document.getElementById("interview-player");
  if (!player) {
    return;
  }

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
})();
