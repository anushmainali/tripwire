"""Payment checks: crypto address lookups on public explorers + P2P handle flags."""

import httpx

from src.contracts import Entities, Evidence

TIMEOUT_S = 6.0


def _btc(addr: str, client: httpx.Client) -> Evidence:
    resp = client.get(f"https://blockstream.info/api/address/{addr}")
    resp.raise_for_status()
    stats = resp.json()
    chain, mem = stats["chain_stats"], stats["mempool_stats"]
    txs = chain["tx_count"] + mem["tx_count"]
    received = (chain["funded_txo_sum"] + mem["funded_txo_sum"]) / 1e8
    return _crypto_evidence("Bitcoin", addr, txs, f"{received:.4f} BTC received")


def _eth(addr: str, client: httpx.Client) -> Evidence:
    resp = client.get(f"https://api.blockcypher.com/v1/eth/main/addrs/{addr[2:].lower()}/balance")
    resp.raise_for_status()
    data = resp.json()
    txs = data.get("n_tx", 0)
    received = data.get("total_received", 0) / 1e18
    return _crypto_evidence("Ethereum", addr, txs, f"{received:.4f} ETH received")


def _crypto_evidence(chain: str, addr: str, txs: int, received: str) -> Evidence:
    short = f"{addr[:6]}…{addr[-4:]}"
    if txs == 0:
        return Evidence("crypto_explorer", f"{chain} wallet {short} is brand new (no transactions yet)", "red")
    if txs > 500:
        return Evidence(
            "crypto_explorer", f"{chain} wallet {short} has {txs} transactions ({received}) — high churn", "red"
        )
    return Evidence("crypto_explorer", f"{chain} wallet {short} has {txs} transactions ({received})", "yellow")


def check_payment(entities: Entities) -> list[Evidence]:
    out: list[Evidence] = []
    if entities.crypto_addresses:
        out.append(
            Evidence("crypto_request", "Asks you to pay in crypto — payments can't be reversed or disputed", "red")
        )
        with httpx.Client(timeout=TIMEOUT_S, headers={"User-Agent": "Tripwire/1.0"}) as client:
            for addr in entities.crypto_addresses[:2]:
                lookup = _btc if addr.startswith(("bc1", "1", "3")) else _eth if addr.startswith("0x") else None
                if lookup is None:
                    continue
                try:
                    out.append(lookup(addr, client))
                except (httpx.HTTPError, KeyError, ValueError) as error:
                    msg = f"Couldn't look up wallet {addr[:6]}… ({type(error).__name__})"
                    out.append(Evidence("crypto_explorer", msg, "info", ok=False))
    if entities.payment_handles:
        handles = ", ".join(entities.payment_handles[:3])
        out.append(
            Evidence(
                "p2p_handle",
                f"Asks you to pay a personal handle ({handles}) — P2P payments to strangers are rarely refundable",
                "yellow",
            )
        )
    return out
