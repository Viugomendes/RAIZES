// The family tree page.
//
// The drawing is made on the server (Python). This script:
// - moves and zooms it (drag, Ctrl + mouse wheel, two fingers, buttons, keys);
// - opens it in full screen, where one finger and the plain wheel also work;
// - recolours it from another central person ("see from..."), using the same
//   kinship rules as the server (kinship.js). Nobody moves: only the sides,
//   the distances and the central ring change.
(function () {
  "use strict";

  var svg = document.getElementById("family-tree");
  if (!svg) {
    return;
  }
  var frame = document.getElementById("tree-frame");
  var hint = document.getElementById("tree-hint");
  var strings = JSON.parse(document.getElementById("tree-strings").textContent);
  var data = window.RAIZES_DATA;

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

  // ----- See from... -----
  if (!data || !window.RaizesKinship || !data.people.length) {
    return;
  }
  var SVG_NS = "http://www.w3.org/2000/svg";
  var graph = new window.RaizesKinship.FamilyGraph(data);
  var people = window.Raizes.byId(data.people);
  var skin = data.skin;
  var colors = data.colors;
  var last = skin.radii.length - 1;
  var group = document.getElementById("tree-people");
  var nodes = Array.prototype.slice.call(group.querySelectorAll("a.person"));

  function mixWithWhite(colour, share) {
    var out = "#";
    for (var i = 1; i < 7; i += 2) {
      var channel = parseInt(colour.substr(i, 2), 16);
      var mixed = Math.round(channel + (255 - channel) * share);
      out += (mixed < 16 ? "0" : "") + mixed.toString(16);
    }
    return out;
  }

  function sideColor(side, figures) {
    if (side === undefined) {
      return colors.unlinked;
    }
    if (side === window.RaizesKinship.CENTER) {
      return colors.center;
    }
    var index = figures.indexOf(side);
    return index < colors.sides.length ? colors.sides[index] : colors.otherSides;
  }

  function restyle(central) {
    var result = graph.walk(central);
    nodes.forEach(function (node) {
      var id = node.getAttribute("data-id");
      var person = people[id];
      var d = result.distance[id];
      var step = d === undefined ? last : Math.min(d, last);
      var radius = skin.radii[step];
      var font = skin.fontSizes[step];
      var shade = mixWithWhite(sideColor(result.side[id], result.figures), skin.fades[step]);
      var dot = node.querySelector("circle.dot");
      var cx = dot.getAttribute("cx");
      var cy = parseFloat(dot.getAttribute("cy"));
      dot.setAttribute("r", radius);
      dot.setAttribute("fill", person.deceased ? "#ffffff" : shade);
      dot.setAttribute("stroke", shade);
      dot.setAttribute("stroke-width", person.deceased ? 2.5 : 0);

      var ring = node.querySelector("circle.ring");
      var isCentral = id === central;
      if (isCentral && !ring) {
        ring = document.createElementNS(SVG_NS, "circle");
        ring.setAttribute("class", "ring");
        ring.setAttribute("cx", cx);
        ring.setAttribute("cy", cy);
        ring.setAttribute("fill", "#ffffff");
        ring.setAttribute("stroke-width", 2);
        node.insertBefore(ring, dot);
      } else if (!isCentral && ring) {
        node.removeChild(ring);
        ring = null;
      }
      var ringRadius = 0;
      if (ring) {
        ringRadius = radius + 5;
        ring.setAttribute("r", ringRadius);
        ring.setAttribute("stroke", shade);
      }
      node.classList.toggle("central", isCentral);

      var text = node.querySelector("text");
      text.setAttribute("font-size", font);
      var first = cy + Math.max(radius, ringRadius) + font + 4;
      Array.prototype.forEach.call(text.querySelectorAll("tspan"), function (span, index) {
        span.setAttribute("y", Math.round((first + index * font * 1.12) * 10) / 10);
      });
      node._radius = radius;
    });
    // Nearest people are drawn last, on top of the others.
    nodes.slice().sort(function (a, b) {
      return b._radius - a._radius;
    }).forEach(function (node) {
      group.appendChild(node);
    });
    updateLegend(central, result);
  }

  function updateLegend(central, result) {
    var list = document.getElementById("legend-sides");
    var f = window.Raizes.format;
    var entries = result.figures.map(function (figure) {
      return [sideColor(figure, result.figures), f(strings.side, { name: people[figure].name })];
    });
    entries.push([colors.center, f(strings.center, { name: people[central].name })]);
    if (Object.keys(result.distance).length < data.people.length) {
      entries.push([colors.unlinked, f(strings.unlinked, { name: people[central].name })]);
    }
    list.innerHTML = entries.map(function (entry) {
      return '<li><svg viewBox="0 0 44 28" aria-hidden="true"><circle cx="22" cy="14" r="10" fill="' + entry[0] + '"/></svg> <span>' + entry[1] + "</span></li>";
    }).join("");
  }

  var select = document.getElementById("tree-from");
  var sorted = data.people.slice().sort(function (a, b) {
    return window.Raizes.normalize(a.name) < window.Raizes.normalize(b.name) ? -1 : 1;
  });
  select.innerHTML = sorted.map(function (person) {
    return '<option value="' + window.Raizes.escapeHtml(person.id) + '">' + window.Raizes.escapeHtml(person.name) + (person.years ? " (" + window.Raizes.escapeHtml(person.years) + ")" : "") + "</option>";
  }).join("");
  document.querySelector(".tree-controls").hidden = false;

  var wanted = new URLSearchParams(window.location.search).get("from");
  var start = wanted && people[wanted] ? wanted : data.central;
  if (start) {
    select.value = start;
    if (start !== data.central) {
      restyle(start);
    }
  } else {
    select.selectedIndex = -1;
  }
  select.addEventListener("change", function () {
    restyle(select.value);
  });
})();
