"""Safe-verify advice: how to confirm through an official channel, never the one in the message."""

from src.investigator.extract import BRANDS

BRAND_ADVICE = {
    "usps": "go to usps.com yourself and enter your tracking number. USPS never texts asking for fees.",
    "ups": "open ups.com or the UPS app yourself and enter your tracking number.",
    "fedex": "open fedex.com yourself and enter your tracking number.",
    "irs": "the IRS contacts people by mail first. Check irs.gov/account or call 800-829-1040.",
    "ssa": "call Social Security at 800-772-1213 or sign in at ssa.gov. They never demand payment by phone or text.",
    "zelle": "Zelle has no customer 'refund' agents. Call the number on the back of your bank card.",
    "venmo": "open the Venmo app directly (not a link) and check your activity.",
    "cashapp": "open Cash App directly. Cash App support never asks for your PIN or a payment.",
    "postalplus": "open the PostalPlus app or type its official website yourself and enter your tracking number.",
    "ezpass": "type your toll agency's official site into your browser yourself, or call the number on your statement.",
}
TYPE_ADVICE = {
    "fake_landlord_rental": "never pay a deposit before seeing the place in person and signing a lease. "
    "Look up the owner in county property records.",
    "job_or_check_scam": "real employers never send you a check and ask you to send money back. "
    "Look the company up independently.",
    "investment_romance": "never send money or crypto to someone you've only met online. "
    "Check the platform at sec.gov or finra.org BrokerCheck.",
    "family_emergency": "hang up and call your family member back on the number you already have for them.",
    "tech_support": "close the message. Contact the company only through its official website — "
    "real tech support never cold-contacts you.",
    "prize_lottery": "you can't win a prize you didn't enter, and real prizes never require a fee.",
    "government_impersonation": "look up the agency's official number on its .gov website and call them yourself.",
}
GENERIC = "contact the company or person through a number or website you already trust — not the one in the message."


def safe_verify(brand: str | None, scam_type: str | None) -> str:
    if brand in BRAND_ADVICE:
        return BRAND_ADVICE[brand]
    if brand in BRANDS:
        site = BRANDS[brand][0]
        if scam_type in TYPE_ADVICE and scam_type not in ("bank_impersonation", "account_locked", "fake_delivery"):
            return TYPE_ADVICE[scam_type]
        return f"go to {site} by typing it yourself, or call the number on the back of your card / on your statement."
    if scam_type in TYPE_ADVICE:
        return TYPE_ADVICE[scam_type]
    if scam_type in ("bank_impersonation", "account_locked"):
        return (
            "call the number on the back of your card or open your bank's app directly. Don't use the message's link."
        )
    return GENERIC
