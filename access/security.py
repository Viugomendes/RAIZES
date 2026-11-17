"""Security headers on every answer of the Django server.

The same rules as the Cloudflare function (functions/_middleware.js) for the
static site; a test checks that both policies stay identical.
"""

# The browser may only run the site's own scripts, show its own pictures plus
# the map images, and play the YouTube interviews; nobody may frame the site.
CONTENT_SECURITY_POLICY = "; ".join(
    [
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
    ]
)

HEADERS = {
    "Content-Security-Policy": CONTENT_SECURITY_POLICY,
    "X-Frame-Options": "DENY",
    # Other sites (the map images) only learn the address of the site, never the page.
    "Referrer-Policy": "strict-origin-when-cross-origin",
    # A private family site: search engines must not list it.
    "X-Robots-Tag": "noindex, nofollow",
}


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        for name, value in HEADERS.items():
            response.headers[name] = value
        return response
