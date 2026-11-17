// Tests of the password function (functions/_middleware.js). Run with:
//   node --test family/tests/js/
// The Python tests run them too.
import assert from "node:assert/strict";
import { beforeEach, test } from "node:test";

import { makeSession, onRequest, resetMemory } from "../../../functions/_middleware.js";

const PASSWORD = "bolo-de-fuba";
const SECRET_PAGE = "<h1>Árvore</h1> página secreta";

function call(path, { method = "GET", cookie = "", body = null, ip = "1.2.3.4", lang = "pt-BR", env = {} } = {}) {
  const headers = new Headers({ "CF-Connecting-IP": ip, "Accept-Language": lang });
  if (cookie) {
    headers.set("Cookie", cookie);
  }
  let requestBody;
  if (body) {
    requestBody = new URLSearchParams(body).toString();
    headers.set("Content-Type", "application/x-www-form-urlencoded");
  }
  const request = new Request("https://familia.example" + path, { method, headers, body: requestBody });
  let reached = false;
  const next = async () => {
    reached = true;
    return new Response(SECRET_PAGE, { headers: { "Content-Type": "text/html" } });
  };
  return onRequest({ request, env: { SITE_PASSWORD: PASSWORD, ...env }, next }).then((response) => ({ response, reached: () => reached }));
}

function sessionFrom(response) {
  const header = response.headers.get("Set-Cookie") || "";
  return header.split(";")[0];
}

async function login(password, extra = {}) {
  return call("/__login", { method: "POST", body: { password, next: "/pt-br/tree/" }, ...extra });
}

beforeEach(() => resetMemory());

test("without the cookie the visitor sees only the password page", async () => {
  const { response, reached } = await call("/pt-br/");
  const html = await response.text();

  assert.equal(response.status, 401);
  assert.equal(reached(), false);
  assert.ok(!html.includes("página secreta"));
  assert.ok(html.includes('type="password"'));
  assert.equal(response.headers.get("X-Robots-Tag"), "noindex, nofollow");
});

test("photos and the data file are protected too", async () => {
  for (const path of ["/media/v/480/photos/a.png.jpg", "/data/family.js", "/static/js/tree.js"]) {
    const { response, reached } = await call(path);
    assert.equal(response.status, 401, path);
    assert.equal(reached(), false, path);
  }
});

test("the right password gives a cookie for one year and goes back to the page", async () => {
  const { response } = await login(PASSWORD);
  const cookie = response.headers.get("Set-Cookie");

  assert.equal(response.status, 303);
  assert.equal(response.headers.get("Location"), "/pt-br/tree/");
  assert.match(cookie, /^raizes_session=\d+\.[\w-]+;/);
  assert.match(cookie, /Max-Age=31536000/);
  assert.match(cookie, /HttpOnly/);
  assert.match(cookie, /Secure/);
  assert.match(cookie, /SameSite=Lax/);
  assert.ok(!cookie.includes(PASSWORD));
});

test("with the cookie the pages are delivered", async () => {
  const session = sessionFrom((await login(PASSWORD)).response);
  const { response, reached } = await call("/pt-br/", { cookie: "other=1; " + session });

  assert.equal(response.status, 200);
  assert.equal(reached(), true);
  assert.equal(await response.text(), SECRET_PAGE);
  assert.equal(response.headers.get("X-Robots-Tag"), "noindex, nofollow");
  assert.equal(response.headers.get("Cache-Control"), "private, no-store");
});

test("a wrong password shows an error and gives no cookie", async () => {
  const { response } = await login("errada");

  assert.equal(response.status, 401);
  assert.equal(response.headers.get("Set-Cookie"), null);
  assert.ok((await response.text()).includes("Senha errada"));
});

test("a forged or changed cookie is refused", async () => {
  const session = sessionFrom((await login(PASSWORD)).response);
  const [name, value] = session.split("=");
  const [issued, signature] = value.split(".");
  for (const forged of [`${name}=${Number(issued) + 1}.${signature}`, `${name}=${issued}.x${signature.slice(1)}`, `${name}=abc`, `${name}=`]) {
    const { reached } = await call("/pt-br/", { cookie: forged });
    assert.equal(reached(), false, forged);
  }
});

test("changing the password logs everybody out", async () => {
  const session = sessionFrom((await login(PASSWORD)).response);
  const { reached } = await call("/pt-br/", { cookie: session, env: { SITE_PASSWORD: "nova-senha" } });

  assert.equal(reached(), false);
});

test("a cookie older than one year is refused", async () => {
  const old = Math.floor(Date.now() / 1000) - 366 * 24 * 60 * 60;
  const { reached } = await call("/pt-br/", { cookie: `raizes_session=${await makeSession(PASSWORD, old)}` });

  assert.equal(reached(), false);
});

test("after the password the visitor never leaves the site", async () => {
  for (const next of [
    "//evil.example/",
    "https://evil.example/",
    "/\\evil.example",
    "javascript:alert(1)",
    "/\t/evil.example/x",
    "/\n/evil.example/x",
    "/ /evil.example",
    "/\\/evil.example",
  ]) {
    const { response } = await call("/__login", { method: "POST", body: { password: PASSWORD, next } });
    assert.equal(response.headers.get("Location"), "/", next);
  }
});

test("a wrong password does not keep a dangerous return address", async () => {
  const { response } = await call("/__login", { method: "POST", body: { password: "errada", next: "/\t/evil.example/x" } });

  assert.ok((await response.text()).includes('name="next" value="/"'));
});

test("a login that is not a form gets a clean answer", async () => {
  const request = new Request("https://familia.example/__login", { method: "POST", body: "{}", headers: { "Content-Type": "application/json" } });
  const response = await onRequest({ request, env: { SITE_PASSWORD: PASSWORD }, next: async () => new Response("x") });

  assert.equal(response.status, 400);
});

test("map images may learn the site address but never the page", async () => {
  const { response } = await call("/pt-br/");

  assert.equal(response.headers.get("Referrer-Policy"), "strict-origin-when-cross-origin");
});

test("ten wrong attempts block even the right password for a while", async () => {
  for (let i = 0; i < 10; i++) {
    assert.equal((await login("errada")).response.status, 401);
  }
  const { response } = await login(PASSWORD);

  assert.equal(response.status, 429);
  assert.equal(response.headers.get("Set-Cookie"), null);
  assert.ok((await response.text()).includes("Muitas tentativas"));
});

test("the limit counts each connection separately", async () => {
  for (let i = 0; i < 10; i++) {
    await login("errada", { ip: "9.9.9.9" });
  }

  assert.equal((await login(PASSWORD, { ip: "5.5.5.5" })).response.status, 303);
});

test("a correct password clears the wrong attempts", async () => {
  for (let i = 0; i < 9; i++) {
    await login("errada");
  }
  await login(PASSWORD);
  for (let i = 0; i < 9; i++) {
    await login("errada");
  }

  assert.equal((await login(PASSWORD)).response.status, 303);
});

test("the counter uses the KV store when there is one", async () => {
  const store = new Map();
  const kv = {
    get: async (key) => (store.has(key) ? JSON.parse(store.get(key)) : null),
    put: async (key, value) => store.set(key, value),
    delete: async (key) => store.delete(key),
  };
  await login("errada", { env: { RAIZES_KV: kv } });

  assert.equal(JSON.parse(store.get("failures:1.2.3.4")).count, 1);
});

test("without SITE_PASSWORD nothing is shown", async () => {
  const request = new Request("https://familia.example/pt-br/");
  let reached = false;
  const response = await onRequest({ request, env: {}, next: async () => { reached = true; return new Response("x"); } });

  assert.equal(response.status, 503);
  assert.equal(reached, false);
});

test("robots.txt is public and says no", async () => {
  const { response, reached } = await call("/robots.txt");

  assert.equal(reached(), true);
  assert.equal(response.headers.get("X-Robots-Tag"), "noindex, nofollow");
});

test("the password page speaks Spanish to Spanish browsers", async () => {
  const { response } = await call("/es/", { lang: "es-ES,es;q=0.9" });

  assert.ok((await response.text()).includes("Contraseña"));
});

test("logging out removes the cookie", async () => {
  const { response } = await call("/__logout");

  assert.equal(response.status, 303);
  assert.match(response.headers.get("Set-Cookie"), /raizes_session=; Max-Age=0/);
});

test("the address asked for is kept through the password page", async () => {
  const { response } = await call("/es/people/lia-carvalho-1996/?x=1");

  assert.ok((await response.text()).includes('name="next" value="/es/people/lia-carvalho-1996/?x=1"'));
});
