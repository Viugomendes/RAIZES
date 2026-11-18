// Runs the browser scripts under Node for the Python tests.
// Reads {"task": ..., "data": ..., ...} on stdin and prints the result as JSON.
"use strict";

const fs = require("fs");
const path = require("path");
const vm = require("vm");
const staticDir = path.join(__dirname, "..", "..", "..", "static", "js");
const Kinship = require(path.join(staticDir, "kinship.js"));
const Mural = require(path.join(staticDir, "mural.js"));
const Search = require(path.join(staticDir, "search.js"));
const Header = require(path.join(staticDir, "header.js"));
const Theme = require(path.join(staticDir, "theme.js"));

let input = "";
process.stdin.on("data", (chunk) => (input += chunk));
process.stdin.on("end", () => {
  const request = JSON.parse(input);
  const data = request.data;
  let result;
  if (request.task === "kinship") {
    const graph = new Kinship.FamilyGraph(data);
    result = {};
    for (const person of data.people) {
      result[person.id] = graph.walk(person.id);
    }
  } else if (request.task === "mural") {
    result = request.days.map((day) => Mural.buildMural(data, day));
  } else if (request.task === "search") {
    const index = Search.buildIndex(data);
    result = request.criteria.map((criteria) => Search.filterPeople(index, criteria).map((entry) => entry.person.id));
  } else if (request.task === "recipes") {
    result = request.texts.map((text) => Search.filterRecipes(data, text).map((recipe) => recipe.slug));
  } else if (request.task === "quick-search") {
    const index = Search.buildIndex(data);
    result = request.texts.map((text) => {
      const found = Header.suggest(Search, index, text);
      return {
        people: found.people.map((person) => person.id),
        details: found.people.map(Header.detail),
        total: found.total,
        seeAll: Header.seeAllUrl(request.searchHref, text),
      };
    });
  } else if (request.task === "initial-text") {
    result = request.searches.map((search) => Search.initialText(search));
  } else if (request.task === "search-without-kinship") {
    // As in the browser when kinship.js is not on the page (the header search).
    const context = { self: { Raizes: require(path.join(staticDir, "common.js")) }, URLSearchParams };
    vm.runInNewContext(fs.readFileSync(path.join(staticDir, "search.js"), "utf-8"), context);
    const index = context.self.RaizesSearch.buildIndex(data);
    result = {
      found: context.self.RaizesSearch.filterPeople(index, request.criteria).map((entry) => entry.person.id),
      kinship: index.some((entry) => entry.distance !== undefined || entry.generation !== undefined),
    };
  } else if (request.task === "script-loader") {
    // Scripts settle only when the test says so, as on a slow network.
    const added = [];
    const pending = {};
    const log = [];
    const load = Header.scriptLoader((src, settled) => {
      added.push(src);
      pending[src] = settled;
    });
    const settle = (src, ok) => { const settled = pending[src]; delete pending[src]; settled(ok); };
    load(["data", "common", "search"], (ok) => log.push(["first", ok]));
    settle("data", false);
    load(["data", "common", "search"], (ok) => log.push(["reopened while loading", ok]));
    settle("common", true);
    settle("search", true);
    const afterFirst = added.slice();
    load(["data", "common", "search"], (ok) => log.push(["retry", ok]));
    settle("data", true);
    result = { afterFirst, added, log };
  } else if (request.task === "theme") {
    result = request.steps.map(([current, prefersDark]) => Theme.nextTheme(current, prefersDark));
  } else {
    throw new Error("unknown task " + request.task);
  }
  process.stdout.write(JSON.stringify(result));
});
