// 1 · News: a strip with every photo of the family, in a new random order on
// each visit, sliding sideways without end. It stops under the mouse, while a
// card has the keyboard focus and while a finger touches it. With "reduce
// motion", or fewer than 4 photos, it does not move: it is a strip to
// scroll by hand.
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
  var FEWEST_MOVING = 4; // with fewer photos the strip stays still

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

  // The strip moves only with 4 photos or more, and when the person did not
  // ask the system for less motion.
  function moves(count, reduceMotion) {
    return count >= FEWEST_MOVING && !reduceMotion;
  }

  // Where the strip must be (pixels moved to the left) so that a card
  // `left` pixels from the start of the strip is in the middle of the screen.
  function centred(left, cardWidth, screenWidth) {
    return left - (screenWidth - cardWidth) / 2;
  }

  // The same place as a point of the animation (0 to one round), knowing that
  // the animation starts one round in (the first row is a copy).
  function phase(shift, round) {
    return (((shift - round) % round) + round) % round;
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
    var reduce = win.matchMedia && win.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var still = !moves(photos.length, reduce);
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
        section.classList.add("is-still");
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
      // A copy before and one after (hidden): when the strip has moved by
      // one round, it starts again without a jump, and any card can be put
      // in the middle of the screen.
      [true, false].forEach(function (before) {
        var copy = first.cloneNode(true);
        copy.setAttribute("aria-hidden", "true");
        Array.prototype.forEach.call(copy.querySelectorAll("a"), function (link) {
          link.tabIndex = -1;
        });
        track.insertBefore(copy, before ? first : null);
      });
      track.style.setProperty("--round", round + "px");
      track.style.setProperty("--carousel-duration", seconds + "s");
      track.style.setProperty("--carousel-delay", "0s");
      track.classList.add("is-moving");
    }

    // The animation goes on from `offset` pixels (0 to one round).
    function seek(offset) {
      track.style.setProperty("--carousel-delay", -(seconds * offset) / round + "s");
      track.classList.remove("is-moving", "is-steered");
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

    // A card reached with the keyboard goes to the middle of the screen,
    // clear of the soft edges. A click with the mouse does not move it.
    var shift = null;
    function keyboard(link) {
      try {
        return link.matches(":focus-visible");
      } catch (error) {
        return true; // old browser: better to show the card
      }
    }
    section.addEventListener("focusin", function (event) {
      var link = event.target.closest && event.target.closest(".carousel-card");
      if (still || !link || !keyboard(link)) {
        return;
      }
      viewport.scrollLeft = 0;
      shift = centred(link.parentNode.offsetLeft, link.offsetWidth, viewport.clientWidth);
      track.style.setProperty("--steer", -shift + "px");
      track.classList.add("is-steered");
      win.requestAnimationFrame(function () {
        viewport.scrollLeft = 0; // the browser may have scrolled it to the card
      });
    });
    // When the keyboard leaves the strip, it moves on from where it is.
    section.addEventListener("focusout", function (event) {
      if (shift === null || section.contains(event.relatedTarget)) {
        return;
      }
      seek(phase(shift, round));
      shift = null;
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
    var byMouse = false;
    section.addEventListener("pointerdown", function (event) {
      from = { x: event.clientX, y: event.clientY };
    });
    section.addEventListener("click", function (event) {
      byMouse = event.detail > 0;
      if (from && Math.abs(event.clientX - from.x) + Math.abs(event.clientY - from.y) > DRAG && byMouse) {
        event.preventDefault();
        event.stopPropagation();
      }
      from = null;
    });
    // The photo was opened with the mouse or a finger and closed with Esc: the
    // browser puts a keyboard focus back on the card, which would keep the
    // strip stopped. Without that focus it moves on.
    doc.addEventListener("close", function (event) {
      var active = doc.activeElement;
      if (byMouse && event.target.classList.contains("lightbox") && active && section.contains(active)) {
        active.blur();
      }
    }, true);
  }

  return {
    shuffle: shuffle,
    roundsToFill: roundsToFill,
    moves: moves,
    centred: centred,
    phase: phase,
    duration: duration,
    start: start,
  };
});
