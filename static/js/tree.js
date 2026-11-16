// The family tree: move it by dragging and zoom with the wheel, a pinch or
// the buttons. The drawing itself is made on the server (Python); this file
// only changes which part of it is visible, by changing the SVG "viewBox".
(function () {
  "use strict";

  var svg = document.getElementById("family-tree");
  if (!svg) {
    return;
  }

  var MAX_ZOOM = 12; // how many times closer than the whole-family view
  var MIN_ZOOM = 0.6;
  var DRAG_THRESHOLD = 5; // pixels before a press becomes a drag

  var full = svg.viewBox.baseVal;
  var whole = { x: full.x, y: full.y, width: full.width, height: full.height };
  var view = { x: whole.x, y: whole.y, width: whole.width, height: whole.height };

  function apply() {
    svg.setAttribute(
      "viewBox",
      view.x + " " + view.y + " " + view.width + " " + view.height
    );
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
  svg.addEventListener(
    "wheel",
    function (event) {
      event.preventDefault();
      var factor = Math.pow(1.0015, -event.deltaY);
      zoomAt(toDrawing(event.clientX, event.clientY), factor);
    },
    { passive: false }
  );

  // ----- Dragging and pinching (mouse, pen and touch) -----
  var pointers = {}; // pointerId -> {x, y} on the screen
  var dragStart = null;
  var dragged = false;
  var pinchDistance = 0;

  function pointerList() {
    return Object.keys(pointers).map(function (id) {
      return pointers[id];
    });
  }

  function distance(a, b) {
    return Math.hypot(a.x - b.x, a.y - b.y);
  }

  svg.addEventListener("pointerdown", function (event) {
    if (event.pointerType === "mouse" && event.button !== 0) {
      return;
    }
    pointers[event.pointerId] = { x: event.clientX, y: event.clientY };
    var list = pointerList();
    if (list.length === 1) {
      dragStart = { x: event.clientX, y: event.clientY };
      dragged = false;
    } else if (list.length === 2) {
      pinchDistance = distance(list[0], list[1]);
      dragged = true;
    }
  });

  svg.addEventListener("pointermove", function (event) {
    var previous = pointers[event.pointerId];
    if (!previous) {
      return;
    }
    var list = pointerList();

    if (list.length === 1) {
      if (!dragged && distance(dragStart, { x: event.clientX, y: event.clientY }) < DRAG_THRESHOLD) {
        return;
      }
      if (!dragged) {
        dragged = true;
        svg.classList.add("dragging");
        // From now on the tree keeps receiving the movement even if the
        // pointer leaves it. Some browsers refuse; dragging still works.
        try {
          svg.setPointerCapture(event.pointerId);
        } catch (error) {
          // Nothing to do.
        }
      }
      var before = toDrawing(previous.x, previous.y);
      var after = toDrawing(event.clientX, event.clientY);
      view.x -= after.x - before.x;
      view.y -= after.y - before.y;
      apply();
    }

    pointers[event.pointerId] = { x: event.clientX, y: event.clientY };

    if (list.length === 2) {
      list = pointerList();
      var newDistance = distance(list[0], list[1]);
      if (pinchDistance > 0 && newDistance > 0) {
        var middle = toDrawing((list[0].x + list[1].x) / 2, (list[0].y + list[1].y) / 2);
        zoomAt(middle, newDistance / pinchDistance);
      }
      pinchDistance = newDistance;
    }
  });

  function release(event) {
    delete pointers[event.pointerId];
    if (pointerList().length === 0) {
      svg.classList.remove("dragging");
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
})();
