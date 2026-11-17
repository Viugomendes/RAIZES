"""Small helpers to describe a device without storing sensitive details."""

# Order matters: Edge and Samsung also say "Chrome", Chrome also says "Safari".
BROWSERS = (("Edg", "Edge"), ("SamsungBrowser", "Samsung"), ("Firefox", "Firefox"),
            ("Chrome", "Chrome"), ("Safari", "Safari"))
SYSTEMS = (("Android", "Android"), ("iPhone", "iPhone"), ("iPad", "iPad"),
           ("Windows", "Windows"), ("Mac", "Mac"), ("Linux", "Linux"))


def describe_browser(user_agent: str) -> str:
    """Short text such as "Chrome · Android"; "?" when nothing is recognised."""
    browser = next((name for key, name in BROWSERS if key in user_agent), None)
    system = next((name for key, name in SYSTEMS if key in user_agent), None)
    parts = [part for part in (browser, system) if part]
    return " · ".join(parts) or "?"


def ip_prefix(ip: str) -> str:
    """Hide the end of the address: 192.168.1.37 -> 192.168.1.x."""
    if ":" in ip:
        return ":".join(ip.split(":")[:2]) + ":…"
    if ip.count(".") == 3:
        return ip.rsplit(".", 1)[0] + ".x"
    return ""
