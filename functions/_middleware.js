// Raízes: the family password, checked on the server before every request.
//
// This file runs on Cloudflare Pages, in front of every page, photo and data
// file of the exported site (section 3 of the plan):
// - the password is never in the pages: it is the SITE_PASSWORD secret of
//   the Cloudflare project;
// - whoever types it gets a cookie for one year, so the grandparents type it
//   once per device;
// - wrong attempts are limited per connection (10 every 15 minutes);
// - changing SITE_PASSWORD logs everybody out, because the cookie is signed
//   with it;
// - search engines are asked not to index anything.
//
// The attempt counter is kept in a KV namespace bound as RAIZES_KV when there
// is one (see README); without it, it is kept in memory, which still slows
// down guessing but resets more often.

const COOKIE = "raizes_session";
const MAX_AGE = 365 * 24 * 60 * 60; // seconds
const LOGIN_PATH = "/__login";
const LOGOUT_PATH = "/__logout";
const MAX_FAILURES = 10;
const FAILURE_WINDOW = 15 * 60; // seconds
const PUBLIC_PATHS = new Set(["/robots.txt"]);
export const CONTENT_SECURITY_POLICY = [
  "default-src 'self'",
  "script-src 'self'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: https://tile.openstreetmap.org",
  "media-src 'self'",
  "frame-src https://www.youtube-nocookie.com",
  "connect-src 'self'",
  "object-src 'none'",
  "base-uri 'none'",
  "form-action 'self'",
  "frame-ancestors 'none'",
].join("; ");

const memoryFailures = new Map();

const TEXTS = {
  pt: {
    lang: "pt-BR",
    title: "Entrar",
    intro: "Este site é privado. Digite a senha da família.",
    password: "Senha",
    enter: "Entrar",
    wrong: "Senha errada. Tente de novo.",
    tooMany: "Muitas tentativas erradas. Espere 15 minutos e tente de novo.",
    notConfigured: "O site ainda não tem senha configurada.",
  },
  es: {
    lang: "es",
    title: "Entrar",
    intro: "Este sitio es privado. Escribe la contraseña de la familia.",
    password: "Contraseña",
    enter: "Entrar",
    wrong: "Contraseña incorrecta. Inténtalo de nuevo.",
    tooMany: "Demasiados intentos fallidos. Espera 15 minutos e inténtalo de nuevo.",
    notConfigured: "El sitio todavía no tiene contraseña configurada.",
  },
};

const encoder = new TextEncoder();

function base64url(bytes) {
  let text = "";
  for (const byte of new Uint8Array(bytes)) {
    text += String.fromCharCode(byte);
  }
  return btoa(text).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

async function sign(secret, message) {
  const key = await crypto.subtle.importKey("raw", encoder.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  return base64url(await crypto.subtle.sign("HMAC", key, encoder.encode(message)));
}

// Compares without leaking, through timing, how much of the text matched.
async function sameText(a, b) {
  const [x, y] = await Promise.all([
    crypto.subtle.digest("SHA-256", encoder.encode(String(a))),
    crypto.subtle.digest("SHA-256", encoder.encode(String(b))),
  ]);
  const left = new Uint8Array(x);
  const right = new Uint8Array(y);
  let difference = 0;
  for (let i = 0; i < left.length; i++) {
    difference |= left[i] ^ right[i];
  }
  return difference === 0;
}

export async function makeSession(password, issuedAt) {
  return `${issuedAt}.${await sign(password, `raizes-session:${issuedAt}`)}`;
}

async function validSession(value, password, now) {
  if (!value) {
    return false;
  }
  const [issued, signature] = value.split(".");
  const issuedAt = Number(issued);
  if (!Number.isInteger(issuedAt) || !signature || issuedAt > now + 60 || now - issuedAt > MAX_AGE) {
    return false;
  }
  return sameText(signature, await sign(password, `raizes-session:${issuedAt}`));
}

function readCookie(request, name) {
  const header = request.headers.get("Cookie") || "";
  for (const part of header.split(";")) {
    const [key, ...rest] = part.trim().split("=");
    if (key === name) {
      return rest.join("=");
    }
  }
  return "";
}

function language(request) {
  const header = (request.headers.get("Accept-Language") || "").toLowerCase();
  const es = header.indexOf("es");
  const pt = header.indexOf("pt");
  return es !== -1 && (pt === -1 || es < pt) ? "es" : "pt";
}

// Only addresses inside this site: one "/" followed by ordinary characters.
// Browsers ignore tabs and line breaks in addresses and read "\" as "/", so
// "/\t/other-site" or "/\other-site" would leave the site: both are refused.
function safeNext(value) {
  // Visible ASCII only (no spaces, no backslash): anything else is refused.
  return typeof value === "string" && /^\/(?![\/\\])[\x21-\x5b\x5d-\x7e]*$/.test(value) ? value : "/";
}

function escapeHtml(text) {
  return String(text).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

function protectHeaders(headers) {
  headers.set("X-Robots-Tag", "noindex, nofollow");
  headers.set("Cache-Control", "private, no-store");
  // Other sites (the map images) only learn the address of the site, never
  // the page; OpenStreetMap asks for that much.
  headers.set("Referrer-Policy", "strict-origin-when-cross-origin");
  headers.set("X-Content-Type-Options", "nosniff");
  // The browser may only run the site's own scripts, show its own pictures
  // plus the map images, and play the YouTube interviews; the site cannot be
  // shown inside another site.
  headers.set("Content-Security-Policy", CONTENT_SECURITY_POLICY);
  headers.set("X-Frame-Options", "DENY");
  return headers;
}

function page(texts, { status, message = "", next = "/", siteTitle = "Raízes" }) {
  const html = `<!DOCTYPE html>
<html lang="${texts.lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>${escapeHtml(texts.title)} · ${escapeHtml(siteTitle)}</title>
<style>
  body { margin: 0; min-height: 100vh; display: flex; align-items: center; justify-content: center; background: #faf7f1; color: #2a2622; font: 18px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
  main { width: min(92vw, 24rem); padding: 2rem; background: #fff; border: 1px solid #e3dcd0; border-radius: 14px; }
  h1 { margin: 0 0 0.4rem; font: bold 1.8rem Georgia, serif; }
  p { margin: 0 0 1rem; }
  label { display: block; margin-bottom: 0.3rem; color: #6a625a; }
  input { box-sizing: border-box; width: 100%; padding: 0.7rem; font-size: 1.2rem; border: 1px solid #cfc6b8; border-radius: 8px; }
  button { width: 100%; margin-top: 1rem; padding: 0.8rem; border: 0; border-radius: 8px; background: #3f5a36; color: #fff; font-size: 1.15rem; cursor: pointer; }
  .error { padding: 0.6rem 0.8rem; border-radius: 8px; background: #fde2e1; color: #8a1c14; }
</style>
</head>
<body>
<main>
  <h1>${escapeHtml(siteTitle)}</h1>
  <p>${escapeHtml(texts.intro)}</p>
  ${message ? `<p class="error" role="alert">${escapeHtml(message)}</p>` : ""}
  <form method="post" action="${LOGIN_PATH}">
    <input type="hidden" name="next" value="${escapeHtml(next)}">
    <label for="password">${escapeHtml(texts.password)}</label>
    <input id="password" name="password" type="password" autocomplete="current-password" required autofocus>
    <button type="submit">${escapeHtml(texts.enter)}</button>
  </form>
</main>
</body>
</html>`;
  return new Response(html, { status, headers: protectHeaders(new Headers({ "Content-Type": "text/html; charset=utf-8" })) });
}

async function failures(env, key, now) {
  if (env.RAIZES_KV) {
    const stored = await env.RAIZES_KV.get(`failures:${key}`, { type: "json" });
    return stored && now - stored.first < FAILURE_WINDOW ? stored : { count: 0, first: now };
  }
  const stored = memoryFailures.get(key);
  return stored && now - stored.first < FAILURE_WINDOW ? stored : { count: 0, first: now };
}

async function saveFailures(env, key, value) {
  if (env.RAIZES_KV) {
    if (value) {
      await env.RAIZES_KV.put(`failures:${key}`, JSON.stringify(value), { expirationTtl: FAILURE_WINDOW + 60 });
    } else {
      await env.RAIZES_KV.delete(`failures:${key}`);
    }
    return;
  }
  if (value) {
    memoryFailures.set(key, value);
  } else {
    memoryFailures.delete(key);
  }
}

export function resetMemory() {
  memoryFailures.clear();
}

export async function onRequest(context) {
  const { request, env, next } = context;
  const url = new URL(request.url);
  const texts = TEXTS[language(request)];
  const siteTitle = env.SITE_TITLE || "Raízes";
  const now = Math.floor(Date.now() / 1000);
  const password = env.SITE_PASSWORD;

  // Without a password nothing is shown: better closed than open by mistake.
  if (!password) {
    return new Response(texts.notConfigured, { status: 503, headers: protectHeaders(new Headers({ "Content-Type": "text/plain; charset=utf-8" })) });
  }

  if (PUBLIC_PATHS.has(url.pathname)) {
    const response = await next();
    const headers = new Headers(response.headers);
    headers.set("X-Robots-Tag", "noindex, nofollow");
    return new Response(response.body, { status: response.status, headers });
  }

  if (url.pathname === LOGOUT_PATH) {
    const headers = protectHeaders(new Headers({ Location: "/" }));
    headers.append("Set-Cookie", `${COOKIE}=; Max-Age=0; Path=/; HttpOnly; Secure; SameSite=Lax`);
    return new Response(null, { status: 303, headers });
  }

  if (url.pathname === LOGIN_PATH && request.method === "POST") {
    let form;
    try {
      form = await request.formData();
    } catch (error) {
      return page(texts, { status: 400, message: texts.wrong, siteTitle });
    }
    const target = safeNext(form.get("next"));
    const who = request.headers.get("CF-Connecting-IP") || "unknown";
    const record = await failures(env, who, now);
    if (record.count >= MAX_FAILURES) {
      return page(texts, { status: 429, message: texts.tooMany, next: target, siteTitle });
    }
    if (await sameText(form.get("password") || "", password)) {
      await saveFailures(env, who, null);
      const headers = protectHeaders(new Headers({ Location: target }));
      headers.append("Set-Cookie", `${COOKIE}=${await makeSession(password, now)}; Max-Age=${MAX_AGE}; Path=/; HttpOnly; Secure; SameSite=Lax`);
      return new Response(null, { status: 303, headers });
    }
    await saveFailures(env, who, { count: record.count + 1, first: record.first });
    return page(texts, { status: 401, message: texts.wrong, next: target, siteTitle });
  }

  if (await validSession(readCookie(request, COOKIE), password, now)) {
    const response = await next();
    return new Response(response.body, { status: response.status, headers: protectHeaders(new Headers(response.headers)) });
  }

  return page(texts, { status: 401, next: safeNext(url.pathname + url.search), siteTitle });
}
