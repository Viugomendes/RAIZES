// 1 · News: the automatic mural. It is calculated in the browser from
// today's date, so it changes every day without publishing anything.
(function (root, factory) {
  "use strict";
  if (typeof module === "object" && module.exports) {
    module.exports = factory(require("./common.js"));
  } else {
    root.RaizesMural = factory(root.Raizes);
    if (root.document) {
      root.document.addEventListener("DOMContentLoaded", function () {
        root.RaizesMural.start(root.document, root.RAIZES_DATA);
      });
    }
  }
})(typeof self !== "undefined" ? self : this, function (Raizes) {
  "use strict";

  var WEEK = 7;
  var NEWS_SHOWN = 10;

  function isLeap(year) {
    return (year % 4 === 0 && year % 100 !== 0) || year % 400 === 0;
  }

  // Month and day on which an anniversary falls in the given year:
  // someone born on 29 February celebrates on the 28th in other years.
  function anniversary(date, year) {
    if (date[1] === 2 && date[2] === 29 && !isLeap(year)) {
      return [2, 28];
    }
    return [date[1], date[2]];
  }

  function exact(date, approximate) {
    return Array.isArray(date) && date.length === 3 && !approximate;
  }

  function addDays(day, count) {
    var moment = new Date(Date.UTC(day.y, day.m - 1, day.d + count));
    return { y: moment.getUTCFullYear(), m: moment.getUTCMonth() + 1, d: moment.getUTCDate() };
  }

  function dayNumber(day) {
    return Math.floor(Date.UTC(day.y, day.m - 1, day.d) / 86400000);
  }

  function iso(day) {
    function two(n) {
      return (n < 10 ? "0" : "") + n;
    }
    return day.y + "-" + two(day.m) + "-" + two(day.d);
  }

  function fallsOn(date, day) {
    var mark = anniversary(date, day.y);
    return mark[0] === day.m && mark[1] === day.d && date[0] < day.y;
  }

  // Everything the mural shows on a given day, without any HTML.
  function buildMural(data, today) {
    var people = Raizes.byId(data.people);
    var result = { week: [], onThisDay: [], inMemory: [], memoryOfTheDay: null, news: [], newsMore: 0 };

    // Birthdays of the living, today and the next six days.
    for (var offset = 0; offset < WEEK; offset++) {
      var day = addDays(today, offset);
      data.people.forEach(function (person) {
        if (person.deceased || !exact(person.birth, person.birthApprox)) {
          return;
        }
        if (fallsOn(person.birth, day)) {
          result.week.push({ person: person.id, day: day, years: day.y - person.birth[0], isToday: offset === 0 });
        }
      });
    }

    data.people.forEach(function (person) {
      // The living are already in the strip of birthdays.
      if (person.deceased && exact(person.birth, person.birthApprox) && fallsOn(person.birth, today)) {
        result.onThisDay.push({ kind: "birth", person: person.id, years: today.y - person.birth[0] });
      }
      if (exact(person.death, person.deathApprox) && fallsOn(person.death, today)) {
        result.inMemory.push({ kind: "death", person: person.id, years: today.y - person.death[0] });
      }
    });
    data.unions.forEach(function (union) {
      if (union.partners.length === 2 && exact(union.start, false) && fallsOn(union.start, today)) {
        result.onThisDay.push({
          kind: union.kind === "dating" ? "dating" : union.kind === "marriage" ? "marriage" : "union",
          people: union.partners.slice(),
          years: today.y - union.start[0],
        });
      }
    });
    data.photos.forEach(function (photo) {
      if (exact(photo.date, false) && fallsOn(photo.date, today)) {
        result.onThisDay.push({ kind: "photo", photo: photo.id, years: today.y - photo.date[0] });
      }
    });

    // Nothing on this date: a photo, a phrase or a recipe chosen by the date,
    // so the mural is never empty and changes every day.
    if (result.onThisDay.length === 0) {
      var pool = [];
      data.photos.forEach(function (photo) {
        pool.push({ kind: "photo", photo: photo.id });
      });
      data.phrases.forEach(function (phrase, index) {
        if (people[phrase.person]) {
          pool.push({ kind: "phrase", phrase: index });
        }
      });
      data.recipes.forEach(function (recipe) {
        pool.push({ kind: "recipe", recipe: recipe.slug });
      });
      if (pool.length) {
        result.memoryOfTheDay = pool[dayNumber(today) % pool.length];
      }
    }

    var oldest = iso(addDays(today, -data.newsDays));
    var fresh = data.news.filter(function (item) {
      return item.date >= oldest && item.date <= iso(today);
    }).sort(function (a, b) {
      return a.date < b.date ? 1 : a.date > b.date ? -1 : 0; // newest first
    });
    result.news = fresh.slice(0, NEWS_SHOWN);
    result.newsMore = Math.max(0, fresh.length - NEWS_SHOWN);
    return result;
  }

  // ----- Drawing ------------------------------------------------------------

  function render(doc, data, today, strings, lang) {
    var mural = buildMural(data, today);
    var root = Raizes.siteRoot(doc);
    var people = Raizes.byId(data.people);
    var photos = Raizes.byId(data.photos);
    var recipes = Raizes.byId(data.recipes, "slug");
    var f = Raizes.format;
    var p = Raizes.plural;
    var weekday = new Intl.DateTimeFormat(lang, { weekday: "short", day: "numeric", month: "numeric", timeZone: "UTC" });

    function personLink(id) {
      var person = people[id];
      return '<a href="' + Raizes.pageUrl(root, lang + "/people/" + id + "/") + '">' + Raizes.escapeHtml(person.given) + "</a>";
    }

    function fullLink(id) {
      var person = people[id];
      return '<a href="' + Raizes.pageUrl(root, lang + "/people/" + id + "/") + '">' + Raizes.escapeHtml(person.name) + "</a>";
    }

    function avatar(id) {
      var person = people[id];
      if (person.avatar) {
        return '<img class="mini-avatar" src="' + Raizes.fileUrl(root, person.avatar) + '" alt="">';
      }
      return '<span class="mini-avatar mini-initials" aria-hidden="true">' + Raizes.escapeHtml(person.initials) + "</span>";
    }

    function photoFigure(photo, title) {
      var tagged = photo.people.map(personLink).join(", ");
      return (
        '<figure class="mural-photo"><a class="photo-link" href="' + Raizes.fileUrl(root, photo.large) + '" data-caption="' + Raizes.escapeHtml(photo.caption) + '">' +
        '<img src="' + Raizes.fileUrl(root, photo.thumb) + '" alt="' + Raizes.escapeHtml(photo.caption) + '" loading="lazy"></a>' +
        "<figcaption>" + (title ? "<strong>" + Raizes.escapeHtml(title) + "</strong> " : "") + Raizes.escapeHtml(photo.caption) +
        (tagged ? '<span class="tagged">' + tagged + "</span>" : "") + "</figcaption></figure>"
      );
    }

    function item(entry) {
      if (entry.kind === "birth") {
        return '<li class="mural-item">' + avatar(entry.person) + "<p>" + f(p(strings.bornAgo, entry.years), { years: entry.years, name: fullLink(entry.person) }, { name: true }) + "</p></li>";
      }
      if (entry.kind === "marriage" || entry.kind === "union" || entry.kind === "dating") {
        var key = entry.kind === "marriage" ? "marriageAgo" : entry.kind === "dating" ? "datingAgo" : "unionAgo";
        return '<li class="mural-item">' + avatar(entry.people[0]) + avatar(entry.people[1]) + "<p>" +
          f(p(strings[key], entry.years), { years: entry.years, a: fullLink(entry.people[0]), b: fullLink(entry.people[1]) }, { a: true, b: true }) + "</p></li>";
      }
      if (entry.kind === "photo") {
        return '<li class="mural-item mural-item-photo">' + photoFigure(photos[entry.photo], f(p(strings.photoAgo, entry.years), { years: entry.years })) + "</li>";
      }
      return "";
    }

    function memoryOfTheDay(entry) {
      if (entry.kind === "photo") {
        return photoFigure(photos[entry.photo], "");
      }
      if (entry.kind === "phrase") {
        var phrase = data.phrases[entry.phrase];
        return '<blockquote class="mural-quote"><p>' + Raizes.escapeHtml(phrase.text) + "</p><footer>— " + fullLink(phrase.person) + "</footer></blockquote>";
      }
      var recipe = recipes[entry.recipe];
      return '<p class="mural-recipe">' +
        (recipe.thumb ? '<img src="' + Raizes.fileUrl(root, recipe.thumb) + '" alt="" loading="lazy">' : "") +
        '<a href="' + Raizes.pageUrl(root, lang + "/recipes/" + recipe.slug + "/") + '">' + Raizes.escapeHtml(recipe.title) + "</a>" +
        (recipe.author && people[recipe.author] ? '<span class="muted">' + f(strings.recipeBy, { name: fullLink(recipe.author) }, { name: true }) + "</span>" : "") + "</p>";
    }

    function newsItem(entry) {
      if (entry.type === "person" && people[entry.key]) {
        return "<li>" + f(strings.newPerson, { name: fullLink(entry.key) }, { name: true }) + "</li>";
      }
      if (entry.type === "photo" && photos[entry.key]) {
        var photo = photos[entry.key];
        return '<li><a class="photo-link" href="' + Raizes.fileUrl(root, photo.large) + '" data-caption="' + Raizes.escapeHtml(photo.caption) + '">' + Raizes.escapeHtml(strings.newPhoto) + "</a>" +
          (photo.caption ? ": " + Raizes.escapeHtml(photo.caption) : "") + "</li>";
      }
      if (entry.type === "recipe" && recipes[entry.key]) {
        var recipe = recipes[entry.key];
        var link = '<a href="' + Raizes.pageUrl(root, lang + "/recipes/" + recipe.slug + "/") + '">' + Raizes.escapeHtml(recipe.title) + "</a>";
        return "<li>" + f(strings.newRecipe, { title: link }, { title: true }) + "</li>";
      }
      return "";
    }

    var html = "";
    if (mural.week.length) {
      html += '<section class="mural-week" aria-labelledby="mural-week-title"><h2 id="mural-week-title">' + Raizes.escapeHtml(strings.weekBirthdays) + "</h2><ul>";
      mural.week.forEach(function (entry) {
        var when = entry.isToday ? strings.today : weekday.format(new Date(Date.UTC(entry.day.y, entry.day.m - 1, entry.day.d)));
        html += '<li class="birthday' + (entry.isToday ? " is-today" : "") + '">' + avatar(entry.person) +
          '<span><span class="when">' + Raizes.escapeHtml(when) + "</span> " + personLink(entry.person) +
          ' <span class="muted">' + f(p(strings.turns, entry.years), { years: entry.years }) + "</span></span></li>";
      });
      html += "</ul></section>";
    }

    html += '<div class="mural-columns"><div class="mural-main">';
    if (mural.onThisDay.length) {
      html += '<section class="mural-section"><h2>' + Raizes.escapeHtml(strings.onThisDay) + '</h2><ul class="mural-list">' + mural.onThisDay.map(item).join("") + "</ul></section>";
    } else if (mural.memoryOfTheDay) {
      html += '<section class="mural-section"><h2>' + Raizes.escapeHtml(strings.memoryOfTheDay) + "</h2>" + memoryOfTheDay(mural.memoryOfTheDay) + "</section>";
    } else if (!mural.week.length) {
      html += '<p class="notice">' + Raizes.escapeHtml(strings.nothing) + "</p>";
    }
    if (mural.inMemory.length) {
      html += '<section class="mural-memory"><h2>' + Raizes.escapeHtml(strings.inMemory) + "</h2><ul>" + mural.inMemory.map(function (entry) {
        return "<li>" + f(p(strings.deathAgo, entry.years), { years: entry.years, name: fullLink(entry.person) }, { name: true }) + "</li>";
      }).join("") + "</ul></section>";
    }
    html += '</div><aside class="mural-side">';
    if (mural.news.length) {
      html += '<section class="mural-news"><h2>' + Raizes.escapeHtml(strings.newOnSite) + "</h2><ul>" + mural.news.map(newsItem).join("") + "</ul>" +
        (mural.newsMore ? '<p class="muted">' + f(strings.andMore, { count: mural.newsMore }) + "</p>" : "") + "</section>";
    }
    html += "</aside></div>";
    return html;
  }

  function start(doc, data) {
    var target = doc.getElementById("mural");
    if (!target || !data) {
      return;
    }
    var strings = JSON.parse(doc.getElementById("mural-strings").textContent);
    var now = new Date();
    var today = { y: now.getFullYear(), m: now.getMonth() + 1, d: now.getDate() };
    target.innerHTML = render(doc, data, today, strings, doc.documentElement.getAttribute("data-lang"));
  }

  return { buildMural: buildMural, render: render, start: start, anniversary: anniversary };
});
