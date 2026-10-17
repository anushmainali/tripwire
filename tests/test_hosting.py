from src.contracts import Entities
from src.investigator.checks.link import check_links, hosting_suffix


def _kinds(host, brand=None):
    return {e.check: e for e in check_links(Entities(domains=[host], claimed_brand=brand))}


def test_hosting_suffix_detection():
    assert hosting_suffix("abc.svls.customers.gcp.chalk.ai")
    assert hosting_suffix("x.vercel.app")
    assert hosting_suffix("vercel.app") is None
    assert hosting_suffix("chalk.ai") is None


def test_throwaway_hosting_never_names_provider():
    ev = _kinds("nknw-tripwire-demo.mdwje5.svls.customers.gcp.chalk.ai", "postalplus")
    assert "throwaway_hosting" in ev
    assert "POSTALPLUS" in ev["throwaway_hosting"].finding.upper()
    assert all("chalk.ai" not in e.finding.replace("throwaway", "") or e.check == "long_host" for e in ev.values())
    assert "brand_domain_mismatch" not in ev


def test_hosting_with_known_brand_lookalike():
    ev = _kinds("usps-redeliver.netlify.app", "usps")
    assert "throwaway_hosting" in ev and "lookalike_domain" in ev
