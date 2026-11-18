// Runs the browser scripts under Node for the Python tests.
// Reads {"task": ..., "data": ..., ...} on stdin and prints the result as JSON.
"use strict";

const path = require("path");
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
  } else if (request.task === "theme") {
    result = request.steps.map(([current, prefersDark]) => Theme.nextTheme(current, prefersDark));
  } else {
    throw new Error("unknown task " + request.task);
  }
  process.stdout.write(JSON.stringify(result));
});
