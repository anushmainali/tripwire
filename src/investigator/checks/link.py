"""Offline link checks: lookalike/typosquat, punycode/homoglyph, suspicious TLD, shorteners, brand mismatch.

Pure string analysis: never contacts the suspicious site.
"""

import ipaddress
import unicodedata

from src.contracts import Entities, Evidence
from src.investigator.extract import BRANDS, registrable_domain

SHORTENERS = {
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "is.gd", "buff.ly", "cutt.ly", "rb.gy", "shorturl.at",
    "t.ly", "rebrand.ly", "tiny.cc", "s.id", "bit.do", "lnkd.in", "qrco.de", "short.io", "bl.ink", "v.gd",
}  # fmt: skip
SUSPICIOUS_TLDS = {
    "xyz", "top", "click", "link", "live", "shop", "online", "site", "icu", "buzz", "tk", "ml", "ga", "cf", "gq",
    "cc", "ws", "vip", "club", "support", "help", "services", "win", "bid", "loan", "work", "rest", "cyou", "sbs",
    "lol", "mobi", "su", "pw", "fun", "space", "website", "info", "ru", "cn", "zip", "mov", "co",
}  # fmt: skip
HOSTING_SUFFIXES = (
    "svls.customers.gcp.chalk.ai", "vercel.app", "netlify.app", "pages.dev", "workers.dev", "github.io", "web.app",
    "firebaseapp.com", "herokuapp.com", "onrender.com", "glitch.me", "replit.app", "repl.co", "surge.sh",
    "fly.dev", "railway.app", "azurewebsites.net", "blogspot.com", "weebly.com", "wixsite.com",
)  # fmt: skip
HOMOGLYPHS = str.maketrans({"0": "o", "1": "l", "3": "e", "5": "s", "7": "t", "@": "a", "$": "s", "|": "l"})
OFFICIAL = {d for domains in BRANDS.values() for d in domains}


def levenshtein(a: str, b: str) -> int:
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def hosting_suffix(host: str) -> str | None:
    """Free/shared cloud-hosting suffix this host is a subdomain of, if any."""
    host = host.lower().rstrip(".")
    for suffix in HOSTING_SUFFIXES:
        if host.endswith("." + suffix):
            return suffix
    return None


def is_official(host: str) -> str | None:
    """Return the brand if host is (a subdomain of) an official brand domain."""
    reg = registrable_domain(host)
    for brand, domains in BRANDS.items():
        if reg in domains or host in domains:
            return brand
    return None


def lookalike_brand(host: str) -> str | None:
    """Brand that this (non-official) host imitates, if any."""
    if is_official(host):
        return None
    reg = registrable_domain(host)
    label = reg.split(".")[0]
    normalized = label.translate(HOMOGLYPHS).replace("rn", "m").replace("vv", "w")
    full = host.replace("-", "").replace(".", "")
    for brand in BRANDS:
        if len(brand) < 3:
            continue
        if len(brand) >= 4 and brand in full:  # brand embedded: usps-redeliver.co, secure.paypal.com.evil.io
            return brand
        if normalized == brand or (len(brand) >= 5 and levenshtein(normalized, brand) <= 1):
            return brand
        if len(brand) >= 4 and brand in normalized:
            return brand
    return None


def check_links(entities: Entities) -> list[Evidence]:
    out: list[Evidence] = []
    for host in entities.domains[:5]:
        reg = registrable_domain(host)
        tld = reg.rsplit(".", 1)[-1]
        hosted = hosting_suffix(host)
        if hosted:
            reg = host  # never present the hosting provider's own brand as the site
        official = None if hosted else is_official(host)
        if official:
            out.append(Evidence("official_domain", f"{host} is an official {official} domain", "green"))
            continue
        try:
            ipaddress.ip_address(host)
            out.append(Evidence("raw_ip_link", f"The link goes to a bare IP address ({host}), not a named site", "red"))
            continue
        except ValueError:
            pass
        if host.startswith("xn--") or ".xn--" in host:
            out.append(Evidence("punycode", f"{host} uses punycode, often used to fake a familiar name", "red"))
        if any(unicodedata.category(c).startswith("L") and ord(c) > 127 for c in host):
            out.append(Evidence("homoglyph", f"{host} contains look-alike non-Latin characters", "red"))
        brand = lookalike_brand(host)
        claimed = entities.claimed_brand
        if hosted:
            who = f"{claimed.upper()}'s" if claimed and claimed in BRANDS else "the sender's"
            out.append(
                Evidence(
                    "throwaway_hosting",
                    f"The link goes to a throwaway cloud-hosting subdomain, not {who} own site",
                    "red",
                )
            )
            if not brand:
                continue
        if brand:
            real = BRANDS[brand][0]
            out.append(
                Evidence(
                    "lookalike_domain",
                    f"{host if hosted else reg} imitates {brand.upper()} — the real site is {real}",
                    "red",
                )
            )
        if reg in SHORTENERS:
            out.append(
                Evidence("url_shortener", f"{reg} is a link shortener that hides the real destination", "yellow")
            )
        if tld in SUSPICIOUS_TLDS:
            out.append(
                Evidence(
                    "suspicious_tld",
                    f"The link ends in .{tld}, an unusual ending for a business or official notice",
                    "yellow",
                )
            )
        if host.count(".") >= 4 or len(host) > 40:
            out.append(Evidence("long_host", f"{host} is an unusually long, nested address", "yellow"))
        if claimed and claimed in BRANDS and not brand and reg not in SHORTENERS:
            real = BRANDS[claimed][0]
            out.append(
                Evidence(
                    "brand_domain_mismatch",
                    f"Message claims to be {claimed.upper()} but links to {reg}, not {real}",
                    "red",
                )
            )
    return out
