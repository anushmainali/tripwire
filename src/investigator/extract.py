"""Pull structured entities out of an untrusted forwarded message (pure string analysis, no network)."""

import re
from urllib.parse import urlsplit

from src.contracts import Entities

# Brand -> official registrable domains. Used for claimed-brand detection, lookalike checks and safe-verify advice.
BRANDS: dict[str, list[str]] = {
    "usps": ["usps.com"],
    "ups": ["ups.com"],
    "fedex": ["fedex.com"],
    "dhl": ["dhl.com"],
    "paypal": ["paypal.com"],
    "chase": ["chase.com"],
    "wellsfargo": ["wellsfargo.com", "wf.com"],
    "bankofamerica": ["bankofamerica.com", "bofa.com"],
    "citi": ["citi.com", "citibank.com"],
    "capitalone": ["capitalone.com"],
    "amazon": ["amazon.com", "amazon.co.uk", "amzn.to", "a.co"],
    "apple": ["apple.com", "icloud.com"],
    "microsoft": ["microsoft.com", "live.com", "outlook.com"],
    "google": ["google.com", "gmail.com"],
    "netflix": ["netflix.com"],
    "irs": ["irs.gov"],
    "ssa": ["ssa.gov"],
    "venmo": ["venmo.com"],
    "zelle": ["zellepay.com"],
    "cashapp": ["cash.app", "cash.me", "squareup.com"],
    "coinbase": ["coinbase.com"],
    "binance": ["binance.com", "binance.us"],
    "geico": ["geico.com"],
    "att": ["att.com"],
    "verizon": ["verizon.com", "vzw.com"],
    "tmobile": ["t-mobile.com"],
    "ezpass": ["e-zpassny.com", "ezpassnj.com", "e-zpassiag.com", "ezdrivema.com"],
    "dmv": ["dmv.ca.gov", "dmv.ny.gov"],
    # Fictional brand used only by our harmless demo trap page (demo_site/). Its "official" domain is reserved.
    "postalplus": ["postalplus.example"],
}

# Phrases in the message text that indicate which brand the sender claims to be.
BRAND_ALIASES: dict[str, list[str]] = {
    "usps": ["usps", "postal service", "us post"],
    "ups": ["ups "],
    "fedex": ["fedex", "fed ex"],
    "dhl": ["dhl"],
    "paypal": ["paypal"],
    "chase": ["chase"],
    "wellsfargo": ["wells fargo", "wellsfargo"],
    "bankofamerica": ["bank of america", "bofa", "bankofamerica"],
    "citi": ["citibank", "citi "],
    "capitalone": ["capital one", "capitalone"],
    "amazon": ["amazon"],
    "apple": ["apple id", "icloud", "apple pay", "apple support"],
    "microsoft": ["microsoft", "windows defender", "outlook"],
    "google": ["google", "gmail"],
    "netflix": ["netflix"],
    "irs": ["irs", "internal revenue"],
    "ssa": ["social security"],
    "venmo": ["venmo"],
    "zelle": ["zelle"],
    "cashapp": ["cash app", "cashapp"],
    "coinbase": ["coinbase"],
    "binance": ["binance"],
    "geico": ["geico"],
    "att": ["at&t"],
    "verizon": ["verizon"],
    "tmobile": ["t-mobile", "tmobile"],
    "ezpass": ["e-zpass", "ezpass", "e-z pass", "toll"],
    "dmv": ["dmv", "department of motor vehicles"],
    "postalplus": ["postalplus", "postal plus"],
}

_TLDS = (
    "com|net|org|gov|edu|io|co|us|uk|info|biz|xyz|top|click|link|live|shop|online|site|app|me|ly|gl|to|ru|cn|"
    "tk|ml|ga|cf|gq|cc|ws|vip|club|icu|buzz|support|help|services|cloud|ai|dev|page|world|life|today|store|tech|"
    "ca|de|fr|in|au|win|bid|loan|work|rest|cyou|sbs|lol|mobi|pro|asia|su|pw|ink|fun|space|website|news|ws|io"
)
URL_RE = re.compile(r"\b(?:https?://|hxxps?://|www\.)[^\s<>\"'()]+", re.IGNORECASE)
BARE_DOMAIN_RE = re.compile(
    rf"(?<![@\w.-])((?:[a-z0-9](?:[a-z0-9-]{{0,61}}[a-z0-9])?\.)+(?:{_TLDS}|xn--[a-z0-9-]+))(/[^\s<>\"']*)?(?![\w-])",
    re.IGNORECASE,
)
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(r"(?<!\w)(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}(?!\d)")
AMOUNT_RE = re.compile(
    r"(?:\$\s?\d[\d,]*(?:\.\d{1,2})?|\b\d[\d,]*(?:\.\d{1,2})?\s?(?:USD|dollars|USDT|BTC|ETH)\b)", re.I
)
CASHTAG_RE = re.compile(r"(?<![\w$])\$[A-Za-z][A-Za-z0-9_-]{1,20}\b")
AT_HANDLE_RE = re.compile(r"(?<![\w@.])@[A-Za-z0-9][A-Za-z0-9_-]{2,30}\b")
CRYPTO_RES = {
    "btc": re.compile(r"\b(?:bc1[ac-hj-np-z02-9]{25,62}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})\b"),
    "eth": re.compile(r"\b0x[a-fA-F0-9]{40}\b"),
    "tron": re.compile(r"\bT[1-9A-HJ-NP-Za-km-z]{33}\b"),
    "sol": re.compile(r"\b[1-9A-HJ-NP-Za-km-z]{32,44}\b"),
}
PAYMENT_WORDS = ("venmo", "zelle", "cash app", "cashapp", "paypal", "apple pay")


def defang(text: str) -> str:
    """Undo common defanging so 'hxxp://evil[.]com' is analyzed as a URL."""
    return (
        text.replace("[.]", ".").replace("(.)", ".").replace("[dot]", ".").replace("hxxp", "http").replace("[:]", ":")
    )


def host_of(url: str) -> str:
    if not re.match(r"^[a-z]+://", url, re.I):
        url = "http://" + url
    try:
        host = urlsplit(url).hostname or ""
    except ValueError:
        return ""
    return host.lower().rstrip(".")


def registrable_domain(host: str) -> str:
    """Approximate eTLD+1 (handles common two-level suffixes like co.uk)."""
    parts = host.lower().strip(".").split(".")
    if len(parts) <= 2:
        return host.lower()
    if parts[-2] in ("co", "com", "org", "net", "gov", "ac") and len(parts[-1]) == 2:
        return ".".join(parts[-3:])
    if parts[-1] == "gov" and parts[-2] in ("ca", "ny"):
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def _dedupe(items: list[str]) -> list[str]:
    seen: dict[str, None] = {}
    for item in items:
        seen.setdefault(item, None)
    return list(seen)


FREEMAIL = r"@(?:gmail|googlemail|yahoo|outlook|hotmail|live|icloud|me|aol|proton|protonmail)\.[a-z.]+"


def _claimed_brand(text: str, domains: list[str]) -> str | None:
    """Earliest brand named in the text (free-mail addresses ignored), else a brand embedded in a domain."""
    lower = re.sub(FREEMAIL, " ", text.lower())
    best: tuple[int, str] | None = None
    for brand, aliases in BRAND_ALIASES.items():
        for alias in aliases:
            m = re.search(rf"(?<![a-z0-9]){re.escape(alias.strip())}(?![a-z0-9])", lower)
            if m and (best is None or m.start() < best[0]):
                best = (m.start(), brand)
    if best:
        return best[1]
    for domain in domains:  # brand name embedded in a domain, e.g. usps-redeliver.co
        compact = domain.replace("-", "").replace(".", "")
        for brand in BRANDS:
            if len(brand) >= 4 and brand in compact:
                return brand
    return None


def extract(text: str) -> Entities:
    clean = defang(text)
    urls = [u.rstrip(".,;:!?)]}") for u in URL_RE.findall(clean)]
    emails = _dedupe(EMAIL_RE.findall(clean))
    without_urls_emails = EMAIL_RE.sub(" ", URL_RE.sub(" ", clean))
    for match in BARE_DOMAIN_RE.finditer(without_urls_emails):
        urls.append(match.group(0).rstrip(".,;:!?)]}"))
    urls = _dedupe(urls)
    domains = _dedupe([h for h in (host_of(u) for u in urls) if h and "." in h])

    scrubbed = BARE_DOMAIN_RE.sub(" ", without_urls_emails)
    crypto: list[str] = []
    for kind in ("btc", "eth", "tron"):
        crypto += CRYPTO_RES[kind].findall(scrubbed)
    for cand in CRYPTO_RES["sol"].findall(scrubbed):
        # Solana base58 is ambiguous with long words; require mixed case + digits and not already matched.
        if cand not in crypto and re.search(r"\d", cand) and re.search(r"[a-z]", cand) and re.search(r"[A-Z]", cand):
            if not any(cand in c or c in cand for c in crypto):
                crypto.append(cand)
    crypto = _dedupe(crypto)

    scrub_crypto = scrubbed
    for c in crypto:
        scrub_crypto = scrub_crypto.replace(c, " ")
    phones = _dedupe([re.sub(r"[^\d+]", "", p) for p in PHONE_RE.findall(scrub_crypto)])
    amounts = _dedupe([a.strip() for a in AMOUNT_RE.findall(clean)])

    handles = list(CASHTAG_RE.findall(scrub_crypto))
    lower = clean.lower()
    if any(w in lower for w in PAYMENT_WORDS):
        handles += AT_HANDLE_RE.findall(scrub_crypto)
    handles = _dedupe(handles)

    return Entities(
        urls=urls,
        domains=domains,
        phones=phones,
        emails=emails,
        payment_handles=handles,
        crypto_addresses=crypto,
        amounts=amounts,
        claimed_brand=_claimed_brand(clean, domains),
    )
