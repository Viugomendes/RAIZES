// 3 · Search: runs in the browser, ignoring accents and capitals.
(function (root, factory) {
  "use strict";
  if (typeof module === "object" && module.exports) {
    module.exports = factory(require("./common.js"), require("./kinship.js"));
  } else {
    root.RaizesSearch = factory(root.Raizes, root.RaizesKinship);
    if (root.document) {
      root.document.addEventListener("DOMContentLoaded", function () {
        root.RaizesSearch.start(root.document, root.RAIZES_DATA);
      });
    }
  }
})(typeof self !== "undefined" ? self : this, function (Raizes, Kinship) {
  "use strict";

  var N = Raizes.normalize;


  // Everything a person can be found by, computed once.
  function buildIndex(data) {
    var kin = data.central ? new Kinship.FamilyGraph(data).walk(data.central) : null;
    return data.people.map(function (person) {
      return {
        person: person,
        names: N([person.name, person.given, person.surname, person.nickname, person.otherNames].join(" ")),
        birthYear: person.birth ? person.birth[0] : null,
        // Place identifiers, compared whole: "rio" never matches "rio-de-janeiro".
        born: [person.birthPlace].filter(Boolean),
        lived: [person.livesIn].concat(person.livedIn).filter(Boolean),
        occupation: N(person.occupation),
        tags: person.tags.map(N),
        distance: kin ? kin.distance[person.id] : undefined,
        generation: kin ? kin.generation[person.id] : undefined,
      };
    });
  }

  function words(text) {
    return N(text).split(/\s+/).filter(Boolean);
  }

  // criteria: {text, from, to, born, lived, distance, generation,
  //            status ("living"|"deceased"), occupation, tag, photos, interview, recipe}
  function filterPeople(index, criteria) {
    var textWords = words(criteria.text);
    var occupationWords = words(criteria.occupation);
    var from = criteria.from ? Number(criteria.from) : null;
    var to = criteria.to ? Number(criteria.to) : null;
    return index.filter(function (entry) {
      var person = entry.person;
      if (!textWords.every(function (word) { return entry.names.indexOf(word) !== -1; })) {
        return false;
      }
      if ((from !== null || to !== null) && entry.birthYear === null) {
        return false;
      }
      if (from !== null && entry.birthYear < from) {
        return false;
      }
      if (to !== null && entry.birthYear > to) {
        return false;
      }
      if (criteria.born && entry.born.indexOf(criteria.born) === -1) {
        return false;
      }
      if (criteria.lived && entry.lived.indexOf(criteria.lived) === -1) {
        return false;
      }
      if (criteria.distance !== undefined && criteria.distance !== "" && !(entry.distance <= Number(criteria.distance))) {
        return false;
      }
      if (criteria.generation !== undefined && criteria.generation !== "" && entry.generation !== Number(criteria.generation)) {
        return false;
      }
      if (criteria.status === "living" && person.deceased) {
        return false;
      }
      if (criteria.status === "deceased" && !person.deceased) {
        return false;
      }
      if (!occupationWords.every(function (word) { return entry.occupation.indexOf(word) !== -1; })) {
        return false;
      }
      if (criteria.tag && entry.tags.indexOf(N(criteria.tag)) === -1) {
        return false;
      }
      if (criteria.photos && !person.photos) {
        return false;
      }
      if (criteria.interview && !person.interview) {
        return false;
      }
      if (criteria.recipe && !person.recipes) {
        return false;
      }
      return true;
    }).sort(function (a, b) {
      return N(a.person.name) < N(b.person.name) ? -1 : N(a.person.name) > N(b.person.name) ? 1 : 0;
    });
  }

  function filterRecipes(data, text) {
    var textWords = words(text);
    if (!textWords.length) {
      return [];
    }
    return data.recipes.filter(function (recipe) {
      var title = N(recipe.title);
      return textWords.every(function (word) { return title.indexOf(word) !== -1; });
    });
  }

  // ----- Page -----

  function start(doc, data) {
    var form = doc.getElementById("search-form");
    if (!form || !data) {
      return;
    }
    var strings = JSON.parse(doc.getElementById("search-strings").textContent);
    var lang = doc.documentElement.getAttribute("data-lang");
    var root = Raizes.siteRoot(doc);
    var people = Raizes.byId(data.people);
    var index = buildIndex(data);
    var kin = data.central ? new Kinship.FamilyGraph(data).walk(data.central) : null;

    // labelsAreHtml: the labels come from Raizes.format, already escaped.
    function options(select, list, labelsAreHtml) {
      select.insertAdjacentHTML("beforeend", list.map(function (option) {
        var label = labelsAreHtml ? option[1] : Raizes.escapeHtml(option[1]);
        return '<option value="' + Raizes.escapeHtml(option[0]) + '">' + label + "</option>";
      }).join(""));
    }

    var places = Object.keys(data.places).map(function (slug) {
      return [slug, data.places[slug].name];
    }).sort(function (a, b) { return N(a[1]) < N(b[1]) ? -1 : 1; });
    options(form.elements.born, places);
    options(form.elements.lived, places);
    var tags = {};
    data.people.forEach(function (person) {
      person.tags.forEach(function (tag) { tags[tag] = true; });
    });
    options(form.elements.tag, Object.keys(tags).sort().map(function (tag) { return [tag, tag]; }));

    if (kin) {
      var centralName = people[data.central].name;
      var maxDistance = 0;
      var generations = {};
      Object.keys(kin.distance).forEach(function (id) {
        maxDistance = Math.max(maxDistance, kin.distance[id]);
        generations[kin.generation[id]] = true;
      });
      var steps = [];
      for (var d = 1; d <= maxDistance; d++) {
        steps.push([String(d), Raizes.format(Raizes.plural(strings.steps, d), { count: d })]);
      }
      options(form.elements.distance, steps, true);
      options(form.elements.generation, Object.keys(generations).map(Number).sort(function (a, b) { return a - b; }).map(function (value) {
        return [String(value), Raizes.format(strings.generations[String(value)] || strings.generationOther, { name: centralName, number: value })];
      }), true);
    } else {
      ["distance", "generation"].forEach(function (name) {
        form.elements[name].closest("label").hidden = true;
      });
    }

    function criteria() {
      var elements = form.elements;
      return {
        text: elements.text.value,
        from: elements.from.value,
        to: elements.to.value,
        born: elements.born.value,
        lived: elements.lived.value,
        distance: elements.distance.value,
        generation: elements.generation.value,
        status: elements.status.value,
        occupation: elements.occupation.value,
        tag: elements.tag.value,
        photos: elements.photos.checked,
        interview: elements.interview.checked,
        recipe: elements.recipe.checked,
      };
    }

    function render() {
      var wanted = criteria();
      var found = filterPeople(index, wanted);
      var recipes = filterRecipes(data, wanted.text);
      var html = '<p class="results-count">' + Raizes.format(Raizes.plural(strings.results, found.length), { count: found.length }) + "</p>";
      if (!found.length) {
        html += '<p class="notice">' + Raizes.escapeHtml(strings.noResults) + "</p>";
      }
      html += '<ul class="results">' + found.map(function (entry) {
        var person = entry.person;
        var picture = person.avatar
          ? '<img class="mini-avatar" src="' + Raizes.fileUrl(root, person.avatar) + '" alt="" loading="lazy">'
          : '<span class="mini-avatar mini-initials" aria-hidden="true">' + Raizes.escapeHtml(person.initials) + "</span>";
        return '<li><a class="result" href="' + Raizes.pageUrl(root, lang + "/people/" + person.id + "/") + '">' + picture +
          '<span class="result-text"><span class="result-name">' + Raizes.escapeHtml(person.name) + "</span>" +
          (person.years ? ' <span class="years">' + Raizes.escapeHtml(person.years) + "</span>" : "") +
          (person.occupation ? '<span class="result-detail">' + Raizes.escapeHtml(person.occupation) + "</span>" : "") + "</span></a></li>";
      }).join("") + "</ul>";
      if (recipes.length) {
        html += "<h2>" + Raizes.escapeHtml(strings.recipes) + '</h2><ul class="results">' + recipes.map(function (recipe) {
          var author = recipe.author && people[recipe.author] ? Raizes.format(strings.recipeBy, { name: people[recipe.author].name }) : "";
          return '<li><a class="result" href="' + Raizes.pageUrl(root, lang + "/recipes/" + recipe.slug + "/") + '">' +
            (recipe.thumb ? '<img class="mini-avatar" src="' + Raizes.fileUrl(root, recipe.thumb) + '" alt="" loading="lazy">' : '<span class="mini-avatar mini-initials" aria-hidden="true">🍲</span>') +
            '<span class="result-text"><span class="result-name">' + Raizes.escapeHtml(recipe.title) + "</span>" +
            (author ? '<span class="result-detail">' + author + "</span>" : "") + "</span></a></li>";
        }).join("") + "</ul>";
      }
      doc.getElementById("search-results").innerHTML = html;
    }

    form.hidden = false;
    form.addEventListener("input", render);
    form.addEventListener("change", render);
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      render();
    });
    form.addEventListener("reset", function () {
      setTimeout(render, 0);
    });
    render();
  }

  return { buildIndex: buildIndex, filterPeople: filterPeople, filterRecipes: filterRecipes, start: start };
});
