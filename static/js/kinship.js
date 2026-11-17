// The kinship rules in the browser: the same rules as family/kinship.py,
// used by the search and the map (distance and generation). A test runs both versions
// on every person of the invented family and compares the results.
(function (root, factory) {
  "use strict";
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.RaizesKinship = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var STRENGTH = { biological: 0, adoptive: 1, foster: 2 };
  var CENTER = "center";

  // data.people: [{id}] ordered by birth; data.unions: [{id, partners, children: [[id, kind]]}]
  function FamilyGraph(data) {
    var self = this;
    this.people = data.people.map(function (person) {
      return person.id;
    });
    this.order = {};
    this.asPartner = {};
    this.asChild = {};
    this.people.forEach(function (id, index) {
      self.order[id] = index;
      self.asPartner[id] = [];
      self.asChild[id] = [];
    });
    data.unions.forEach(function (union) {
      union.partners.forEach(function (partner) {
        self.asPartner[partner].push(union);
      });
      union.children.forEach(function (link) {
        self.asChild[link[0]].push([union, link[1]]);
      });
    });
  }

  FamilyGraph.prototype._strongest = function (links) {
    var best = {};
    var order = [];
    links.forEach(function (link) {
      var person = link[0];
      var kind = link[1];
      if (!(person in best)) {
        order.push(person);
        best[person] = kind;
      } else if (STRENGTH[kind] < STRENGTH[best[person]]) {
        best[person] = kind;
      }
    });
    return order.map(function (person) {
      return { person: person, kind: best[person] };
    });
  };

  FamilyGraph.prototype.parents = function (id) {
    var self = this;
    var links = [];
    this.asChild[id].forEach(function (entry) {
      entry[0].partners.forEach(function (partner) {
        links.push([partner, entry[1]]);
      });
    });
    return this._strongest(links).sort(function (a, b) {
      return STRENGTH[a.kind] - STRENGTH[b.kind] || self.order[a.person] - self.order[b.person];
    });
  };

  FamilyGraph.prototype.children = function (id) {
    var self = this;
    var links = [];
    this.asPartner[id].forEach(function (union) {
      union.children.forEach(function (link) {
        links.push(link);
      });
    });
    return this._strongest(links).sort(function (a, b) {
      return self.order[a.person] - self.order[b.person];
    });
  };

  FamilyGraph.prototype.partners = function (id) {
    var found = [];
    this.asPartner[id].forEach(function (union) {
      union.partners.forEach(function (partner) {
        if (partner !== id && found.indexOf(partner) === -1) {
          found.push(partner);
        }
      });
    });
    return found;
  };

  FamilyGraph.prototype.parentalFigures = function (id) {
    return this.parents(id).map(function (parent) {
      return parent.person;
    });
  };

  FamilyGraph.prototype._steps = function (id) {
    var steps = [];
    this.parents(id).forEach(function (parent) {
      steps.push([parent.person, -1]);
    });
    this.children(id).forEach(function (child) {
      steps.push([child.person, 1]);
    });
    this.partners(id).forEach(function (partner) {
      steps.push([partner, 0]);
    });
    return steps;
  };

  // Distance, generation and side of everyone linked to the central person.
  FamilyGraph.prototype.walk = function (central) {
    var distance = {};
    var generation = {};
    var firstSteps = {};
    distance[central] = 0;
    generation[central] = 0;
    firstSteps[central] = [];
    var queue = [central];
    for (var head = 0; head < queue.length; head++) {
      var person = queue[head];
      var steps = this._steps(person);
      for (var i = 0; i < steps.length; i++) {
        var neighbour = steps[i][0];
        var via = person === central ? [neighbour] : firstSteps[person];
        if (!(neighbour in distance)) {
          distance[neighbour] = distance[person] + 1;
          generation[neighbour] = generation[person] + steps[i][1];
          firstSteps[neighbour] = via.slice();
          queue.push(neighbour);
        } else if (distance[neighbour] === distance[person] + 1) {
          via.forEach(function (step) {
            if (firstSteps[neighbour].indexOf(step) === -1) {
              firstSteps[neighbour].push(step);
            }
          });
        }
      }
    }
    var figures = this.parentalFigures(central);
    var side = {};
    Object.keys(firstSteps).forEach(function (id) {
      var steps = firstSteps[id];
      side[id] = steps.length === 1 && figures.indexOf(steps[0]) !== -1 ? steps[0] : CENTER;
    });
    return { distance: distance, generation: generation, side: side, figures: figures };
  };

  return { FamilyGraph: FamilyGraph, CENTER: CENTER };
});
