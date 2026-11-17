// The family tree page.
//
// The drawing is made on the server (Python). This script:
// - moves and zooms it (drag, Ctrl + mouse wheel, two fingers, buttons, keys);
// - opens it in full screen, where one finger and the plain wheel also work;
// - zooms on a person when the address says so (tree/?person=<identifier>).
(function () {
  "use strict";

  var svg = document.getElementById("family-tree");
  if (!svg) {
    return;
  }
  var frame = document.getElementById("tree-frame");
  var hint = document.getElementById("tree-hint");
  var strings = JSON.parse(document.getElementById("tree-strings").textContent);

  var MAX_ZOOM = 12; // how many times closer than the whole-family view
  var MIN_ZOOM = 0.6;
  var DRAG_THRESHOLD = 5; // pixels before a press becomes a drag

  var full = svg.viewBox.baseVal;
  var whole = { x: full.x, y: full.y, width: full.width, height: full.height };
  var view = { x: whole.x, y: whole.y, width: whole.width, height: whole.height };

  function apply() {
    svg.setAttribute("viewBox", view.x + " " + view.y + " " + view.width + " " + view.height);
  }

  function isFull() {
    return frame.classList.contains("is-full");
  }

  var hintTimer = null;
  function showHint(text) {
    hint.textContent = text;
    hint.classList.add("visible");
    clearTimeout(hintTimer);
    hintTimer = setTimeout(function () {
      hint.classList.remove("visible");
    }, 2200);
  }

  // Convert a point of the screen to a point of the drawing.
  function toDrawing(clientX, clientY) {
    var matrix = svg.getScreenCTM();
    if (!matrix) {
      return { x: view.x + view.width / 2, y: view.y + view.height / 2 };
    }
    var point = svg.createSVGPoint();
    point.x = clientX;
    point.y = clientY;
    return point.matrixTransform(matrix.inverse());
  }

  // Zoom keeping the given point of the drawing under the same screen point.
  function zoomAt(point, factor) {
    var newWidth = view.width / factor;
    newWidth = Math.max(whole.width / MAX_ZOOM, Math.min(whole.width / MIN_ZOOM, newWidth));
    var scale = newWidth / view.width;
    view.x = point.x - (point.x - view.x) * scale;
    view.y = point.y - (point.y - view.y) * scale;
    view.width = newWidth;
    view.height = view.height * scale;
    apply();
  }

  function zoomAtCentre(factor) {
    zoomAt({ x: view.x + view.width / 2, y: view.y + view.height / 2 }, factor);
  }

  function fit() {
    view = { x: whole.x, y: whole.y, width: whole.width, height: whole.height };
    apply();
  }

  // ----- Mouse wheel -----
  // The plain wheel scrolls the page (to reach the legend); Ctrl + wheel, a
  // trackpad pinch (which browsers send as Ctrl + wheel) or the full screen
  // zoom the tree.
  svg.addEventListener(
    "wheel",
    function (event) {
      if (!event.ctrlKey && !event.metaKey && !isFull()) {
        showHint(strings.wheelHint);
        return;
      }
      event.preventDefault();
      var factor = Math.pow(1.0015, -event.deltaY);
      zoomAt(toDrawing(event.clientX, event.clientY), factor);
    },
    { passive: false }
  );

  // ----- Dragging and pinching -----
  // Mouse and pen: drag to move. Touch: outside the full screen one finger
  // scrolls the page (the browser does it) and two fingers move and zoom;
  // in full screen one finger also moves the tree.
  var pointers = {}; // pointerId -> {x, y, type} on the screen
  var dragStart = null;
  var dragged = false;
  var pinch = null;

  function pointerList() {
    return Object.keys(pointers).map(function (id) {
      return pointers[id];
    });
  }

  function distance(a, b) {
    return Math.hypot(a.x - b.x, a.y - b.y);
  }

  function middle(list) {
    return { x: (list[0].x + list[1].x) / 2, y: (list[0].y + list[1].y) / 2 };
  }

  function panBy(fromX, fromY, toX, toY) {
    var before = toDrawing(fromX, fromY);
    var after = toDrawing(toX, toY);
    view.x -= after.x - before.x;
    view.y -= after.y - before.y;
    apply();
  }

  svg.addEventListener("pointerdown", function (event) {
    if (event.pointerType === "mouse" && event.button !== 0) {
      return;
    }
    pointers[event.pointerId] = { x: event.clientX, y: event.clientY, type: event.pointerType };
    var list = pointerList();
    if (list.length === 1) {
      dragStart = { x: event.clientX, y: event.clientY };
      dragged = false;
    } else if (list.length === 2) {
      pinch = { distance: distance(list[0], list[1]), middle: middle(list) };
      dragged = true;
    }
  });

  svg.addEventListener("pointermove", function (event) {
    var previous = pointers[event.pointerId];
    if (!previous) {
      return;
    }
    var list = pointerList();
    var oneFingerMoves = event.pointerType !== "touch" || isFull();

    if (list.length === 1 && oneFingerMoves) {
      if (!dragged && distance(dragStart, { x: event.clientX, y: event.clientY }) < DRAG_THRESHOLD) {
        return;
      }
      if (!dragged) {
        dragged = true;
        svg.classList.add("dragging");
        try {
          svg.setPointerCapture(event.pointerId);
        } catch (error) {
          // Some browsers refuse; dragging still works.
        }
      }
      panBy(previous.x, previous.y, event.clientX, event.clientY);
    }

    pointers[event.pointerId] = { x: event.clientX, y: event.clientY, type: event.pointerType };

    if (list.length === 2 && pinch) {
      list = pointerList();
      var now = { distance: distance(list[0], list[1]), middle: middle(list) };
      panBy(pinch.middle.x, pinch.middle.y, now.middle.x, now.middle.y);
      if (pinch.distance > 0 && now.distance > 0) {
        zoomAt(toDrawing(now.middle.x, now.middle.y), now.distance / pinch.distance);
      }
      pinch = now;
    }
  });

  function release(event) {
    var wasTouch = pointers[event.pointerId] && pointers[event.pointerId].type === "touch";
    delete pointers[event.pointerId];
    if (pointerList().length < 2) {
      pinch = null;
    }
    if (pointerList().length === 0) {
      svg.classList.remove("dragging");
    }
    // The browser took a one-finger touch to scroll the page: explain how to move the tree.
    if (event.type === "pointercancel" && wasTouch && !isFull()) {
      showHint(strings.touchHint);
    }
  }

  svg.addEventListener("pointerup", release);
  svg.addEventListener("pointercancel", release);

  // A drag that ends on top of a person must not open that person's page.
  svg.addEventListener(
    "click",
    function (event) {
      if (dragged) {
        event.preventDefault();
        event.stopPropagation();
        dragged = false;
      }
    },
    true
  );

  // ----- Buttons and keyboard -----
  document.getElementById("tree-zoom-in").addEventListener("click", function () {
    zoomAtCentre(1.4);
  });
  document.getElementById("tree-zoom-out").addEventListener("click", function () {
    zoomAtCentre(1 / 1.4);
  });
  document.getElementById("tree-fit").addEventListener("click", fit);

  var fullButton = document.getElementById("tree-full");
  function setFull(on) {
    frame.classList.toggle("is-full", on);
    document.body.classList.toggle("tree-is-full", on);
    fullButton.setAttribute("aria-pressed", on ? "true" : "false");
    fullButton.textContent = on ? strings.exitFullScreen : strings.fullScreen;
    fit();
  }
  fullButton.addEventListener("click", function () {
    setFull(!isFull());
  });
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && isFull()) {
      setFull(false);
    }
  });

  svg.addEventListener("keydown", function (event) {
    var step = view.width / 10;
    if (event.key === "+" || event.key === "=") {
      zoomAtCentre(1.4);
    } else if (event.key === "-") {
      zoomAtCentre(1 / 1.4);
    } else if (event.key === "0") {
      fit();
    } else if (event.key === "ArrowLeft") {
      view.x -= step;
      apply();
    } else if (event.key === "ArrowRight") {
      view.x += step;
      apply();
    } else if (event.key === "ArrowUp") {
      view.y -= step;
      apply();
    } else if (event.key === "ArrowDown") {
      view.y += step;
      apply();
    } else {
      return;
    }
    event.preventDefault();
  });

  // ----- "See in the tree" from a person's page: tree/?person=<identifier> -----
  var wanted = new URLSearchParams(window.location.search).get("person");
  if (wanted) {
    var node = svg.querySelector('a.person[data-id="' + wanted.replace(/[^a-z0-9-]/g, "") + '"]');
    if (node) {
      var dot = node.querySelector("circle.dot");
      var cx = parseFloat(dot.getAttribute("cx"));
      var cy = parseFloat(dot.getAttribute("cy"));
      var width = Math.max(whole.width / 4, 500);
      var height = width * (whole.height / whole.width);
      view = { x: cx - width / 2, y: cy - height / 2, width: width, height: height };
      apply();
      node.classList.add("focused");
      node.focus();
    }
  }
})();