// 1 · News: a strip with every photo of the family, in a new random order on
// each visit, sliding sideways without end. It stops under the mouse, while a
// card has the keyboard focus and while a finger touches it. With "reduce
// motion" it does not move: it is a strip to scroll by hand.
(function (root, factory) {
  "use strict";
  if (typeof module === "object" && module.exports) {
    module.exports = factory(require("./common.js"));
  } else {
    root.RaizesCarousel = factory(root.Raizes);
    if (root.document) {
      root.document.addEventListener("DOMContentLoaded", function () {
        root.RaizesCarousel.start(root.document, root, root.RAIZES_DATA);
      });
    }
  }
})(typeof self !== "undefined" ? self : this, function (Raizes) {
  "use strict";

  var SPEED = 28; // pixels per second, whatever the number of photos
  var TOUCH_RESUME = 1500; // ms after the finger leaves
  var DRAG = 6; // pixels: more than this is a drag, not a click

  // A new list in random order (Fisher-Yates). `random` is Math.random by default.
  function shuffle(items, random) {
    var list = items.slice();
    random = random || Math.random;
    for (var i = list.length - 1; i > 0; i--) {
      var j = Math.floor(random() * (i + 1));
      var kept = list[i];
      list[i] = list[j];
      list[j] = kept;
    }
    return list;
  }

  // How many times the photos go in a row so that one round is at least as
  // wide as the screen (otherwise a gap would show before the copy comes).
  function roundsToFill(rowWidth, screenWidth) {
    if (!(rowWidth > 0)) {
      return 1;
    }
    return Math.max(1, Math.ceil(screenWidth / rowWidth));
  }

  // Seconds for one round: the speed stays the same with 5 or 500 photos.
  function duration(roundWidth) {
    return Math.max(1, roundWidth / SPEED);
  }

  function card(doc, root, photo, untitled, hidden) {
    var item = doc.createElement("li");
    var link = doc.createElement("a");
    var image = doc.createElement("img");
    var caption = doc.createElement("span");
    var text = photo.caption || untitled;
    link.className = "photo-link carousel-card";
    link.draggable = false;
    link.href = Raizes.fileUrl(root, photo.large);
    link.setAttribute("data-caption", photo.caption || "");
    image.src = Raizes.fileUrl(root, photo.thumb);
    image.alt = "";
    image.width = 225;
    image.height = 150;
    image.loading = "lazy";
    image.decoding = "async";
    image.draggable = false;
    caption.className = "carousel-caption";
    caption.textContent = text;
    link.appendChild(image);
    link.appendChild(caption);
    if (hidden) {
      item.setAttribute("aria-hidden", "true");
      link.tabIndex = -1;
    }
    item.appendChild(link);
    return item;
  }

  function row(doc, root, photos, untitled, hidden) {
    var list = doc.createElement("ul");
    list.className = "carousel-row";
    if (hidden) {
      list.setAttribute("aria-hidden", "true");
    }
    photos.forEach(function (photo) {
      list.appendChild(card(doc, root, photo, untitled, hidden));
    });
    return list;
  }

  function start(doc, win, data) {
    var section = doc.getElementById("carousel");
    if (!section || !data || !data.photos || !data.photos.length) {
      return;
    }
    var root = Raizes.siteRoot(doc);
    var viewport = section.querySelector(".carousel-viewport");
    var track = section.querySelector(".carousel-track");
    var untitled = section.getAttribute("data-untitled") || "";
    var photos = shuffle(data.photos);
    var still = win.matchMedia && win.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var round = 0;
    var seconds = 0;

    function pageWidth() {
      section.style.setProperty("--page-width", doc.documentElement.clientWidth + "px");
    }

    function build() {
      pageWidth();
      track.classList.remove("is-moving");
      track.textContent = "";
      var first = row(doc, root, photos, untitled, false);
      track.appendChild(first);
      if (still) {
        return;
      }
      // Few photos: repeat them (hidden from screen readers) to fill the screen.
      var rounds = roundsToFill(first.offsetWidth, viewport.clientWidth);
      for (var i = 1; i < rounds; i++) {
        photos.forEach(function (photo) {
          first.appendChild(card(doc, root, photo, untitled, true));
        });
      }
      round = first.offsetWidth;
      seconds = duration(round);
      // The copy that comes right after: when the strip has moved by one
      // round, it starts again from the beginning without a jump.
      track.appendChild(first.cloneNode(true));
      track.lastChild.setAttribute("aria-hidden", "true");
      Array.prototype.forEach.call(track.lastChild.querySelectorAll("a"), function (link) {
        link.tabIndex = -1;
      });
      track.style.setProperty("--carousel-duration", seconds + "s");
      track.style.setProperty("--carousel-delay", "0s");
      track.classList.add("is-moving");
    }

    // Moves the strip so that `offset` pixels (0 to one round) are to the left.
    function seek(offset) {
      track.style.setProperty("--carousel-delay", -(seconds * offset) / round + "s");
      track.classList.remove("is-moving");
      void track.offsetWidth; // the animation starts again from the new place
      track.classList.add("is-moving");
    }

    section.hidden = false;
    build();

    // The page also changes width when its scroll bar appears (no "resize").
    var wide = viewport.clientWidth;
    function resized() {
      pageWidth();
      if (!still && viewport.clientWidth > wide) {
        wide = viewport.clientWidth;
        if (round < wide) {
          build();
        }
      }
    }
    if (win.ResizeObserver) {
      new win.ResizeObserver(resized).observe(doc.body);
    } else {
      win.addEventListener("resize", resized);
    }

    // A card reached with the keyboard is brought into view (the strip is
    // paused while it has the focus, by the CSS).
    section.addEventListener("focusin", function (event) {
      var link = event.target.closest && event.target.closest(".carousel-card");
      if (still || !link) {
        return;
      }
      win.requestAnimationFrame(function () {
        viewport.scrollLeft = 0;
        var box = viewport.getBoundingClientRect();
        var place = link.getBoundingClientRect();
        if (place.left < box.left || place.right > box.right) {
          // In the middle of the screen; the first cards simply at the start.
          seek(Math.max(0, link.parentNode.offsetLeft - (box.width - place.width) / 2));
        }
      });
    });

    // A finger on the strip stops it; it moves again a little after.
    var timer = null;
    section.addEventListener("touchstart", function () {
      win.clearTimeout(timer);
      section.classList.add("is-held");
    }, { passive: true });
    function release() {
      win.clearTimeout(timer);
      timer = win.setTimeout(function () {
        section.classList.remove("is-held");
      }, TOUCH_RESUME);
    }
    section.addEventListener("touchend", release);
    section.addEventListener("touchcancel", release);

    // A drag or a swipe does not open the photo.
    var from = null;
    section.addEventListener("pointerdown", function (event) {
      from = { x: event.clientX, y: event.clientY };
    });
    section.addEventListener("click", function (event) {
      if (from && Math.abs(event.clientX - from.x) + Math.abs(event.clientY - from.y) > DRAG && event.detail > 0) {
        event.preventDefault();
        event.stopPropagation();
      }
      from = null;
    });
  }

  return { shuffle: shuffle, roundsToFill: roundsToFill, duration: duration, start: start };
});
