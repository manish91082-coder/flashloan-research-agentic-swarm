"""Conservative, deterministic Solidity protocol-path checks.

This module reports source observations only. It does not prove exploitability and
never treats an omitted/partial excerpt as proof that a check is absent.
"""
from __future__ import annotations

import re
from typing import Any


def _topic(status: str, detail: str, evidence_ids: list[str] | None = None) -> dict[str, Any]:
    return {"status": status, "detail": detail, "evidence_ids": sorted(set(evidence_ids or []))}


def _joined(excerpts: list[dict[str, Any]]) -> str:
    chunks = []
    for item in excerpts:
        if isinstance(item, dict) and isinstance(item.get("excerpt"), str):
            chunks.append(item["excerpt"])
    return "\n".join(chunks)


def _evidence_for(excerpts: list[dict[str, Any]], patterns: tuple[str, ...]) -> list[str]:
    # IDs are attached only when supplied explicitly and the matching excerpt contains
    # the source text. No IDs are manufactured from paths or line numbers.
    found = []
    for item in excerpts:
        if not isinstance(item, dict):
            continue
        text = str(item.get("excerpt", "")).casefold()
        if any(p.casefold() in text for p in patterns):
            ids = item.get("evidence_ids", [])
            if isinstance(ids, list):
                found.extend(x for x in ids if isinstance(x, str) and re.fullmatch(r"EV[0-9]{5}", x))
    return found


def _function_body(source: str, name: str) -> tuple[str | None, bool]:
    match = re.search(r"\\bfunction\\s+" + re.escape(name) + r"\\b[^{}]*\\{", source)
    if not match:
        return None, False
    start = match.end()
    depth = 1
    for i in range(start, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[start:i], True
    return source[start:], False


def review_aave(excerpts: list[dict[str, Any]]) -> dict[str, Any]:
    source = _joined(excerpts)
    lower = source.casefold()
    ids = _evidence_for(excerpts, ("IPoolAddressesProvider", "IPool(", "executeOperation", "amount + premium", "approve"))
    provider_cast = bool(re.search(r"IPoolAddressesProvider\\s*\\(", source))
    pool_cast = bool(re.search(r"IPool\\s*\\(", source))
    provider_expr = re.search(r"IPoolAddressesProvider\\s*\\(\\s*([^)]*)\\)", source)
    pool_expr = re.search(r"IPool\\s*\\(\\s*([^)]*)\\)", source)
    if provider_cast and pool_cast and provider_expr and pool_expr:
        same = re.sub(r"\\s+", "", provider_expr.group(1)) == re.sub(r"\\s+", "", pool_expr.group(1))
        wiring = _topic("source_observed", "Both provider and Pool casts are present; constructor arguments " +
                        ("use the same expression." if same else "use different expressions; semantic correctness requires constructor context."), ids)
    else:
        wiring = _topic("unknown", "Provider/Pool constructor wiring is not fully visible in supplied excerpts.", ids)

    body, complete = _function_body(source, "executeOperation")
    if body is None or not complete:
        callback = _topic("unknown", "A complete executeOperation function body is not available in supplied excerpts.", ids)
        repayment = _topic("unknown", "A complete callback body is not available to assess repayment and approval.", ids)
    else:
        b = body.casefold()
        sender_check = bool(re.search(r"require\\s*\\(\\s*msg\\.sender\\s*==", b) or
                           re.search(r"if\\s*\\(\\s*msg\\.sender\\s*!=", b))
        initiator_check = "initiator" in b and ("address(this)" in b or "address (this)" in b)
        callback = _topic("source_observed", f"Complete callback body: trusted-caller comparison {'visible' if sender_check else 'not visible'}; initiator/address(this) binding {'visible' if initiator_check else 'not visible'}. This is a lexical observation, not exploitability proof.", ids)
        amount_check = bool(re.search(r"amount\\s*\\+\\s*premium", b))
        approval = "approve(" in b or "safeapprove(" in b or "forceapprove(" in b
        repayment = _topic("source_observed", f"Complete callback body: amount + premium arithmetic {'visible' if amount_check else 'not visible'}; approval call {'visible' if approval else 'not visible'}. Token, spender and control-flow correctness require deeper analysis.", ids)
    return {"protocol": "aave", "topics": {"pool_provider_wiring": wiring, "callback_authentication": callback, "repayment_premium": repayment}}


def review_uniswap_v2(excerpts: list[dict[str, Any]]) -> dict[str, Any]:
    source = _joined(excerpts)
    lower = source.casefold()
    ids = _evidence_for(excerpts, ("uniswapV2Call", "factory", "token0", "token1", "getReserves", "transfer"))
    body, complete = _function_body(source, "uniswapV2Call")
    if body is None:
        callback = _topic("unknown", "uniswapV2Call body is not present in supplied excerpts.", ids)
        auth = _topic("unknown", "Pair authentication cannot be assessed without source context.", ids)
        repayment = _topic("unknown", "Repayment cannot be assessed without callback body.", ids)
    elif not complete:
        callback = _topic("unknown", "uniswapV2Call excerpt is truncated; TODO/implementation status is not established.", ids)
        auth = _topic("unknown", "Pair authentication cannot be assessed from a truncated callback.", ids)
        repayment = _topic("unknown", "Repayment cannot be assessed from a truncated callback.", ids)
    else:
        b = body.casefold()
        todo = bool(re.search(r"\\b(todo|implement me|not implemented|placeholder)\\b", b))
        callback = _topic("source_observed", "Complete uniswapV2Call body contains an explicit placeholder." if todo else "Complete uniswapV2Call body is present; this alone does not establish correctness.", ids)
        pair_auth = ("msg.sender" in b and ("factory" in b or "pair" in b)) or ("require" in b and "msg.sender" in b)
        auth = _topic("source_observed", "Callback contains a msg.sender/pair-related guard pattern." if pair_auth else "No recognizable msg.sender pair guard pattern appears in the complete callback body; verify factory derivation and call graph before treating this as a defect.", ids)
        repay = bool(re.search(r"(transfer|safeTransfer)\\s*\\(", b))
        repayment = _topic("source_observed", "Callback contains a token transfer call; repayment amount/fee correctness remains unproven." if repay else "No token transfer call appears in the complete callback body.", ids)
    token_order = _topic("source_observed" if ("token0" in lower and "token1" in lower and ("getreserves" in lower or "reserve" in lower)) else "unknown",
                         "token0/token1 and reserve-related references are visible." if ("token0" in lower and "token1" in lower and ("getreserves" in lower or "reserve" in lower)) else "Token ordering and reserve source are not both established by supplied excerpts.",
                         ids)
    return {"protocol": "uniswap_v2", "topics": {"callback_implementation": callback, "pair_authentication": auth, "token_order_reserves": token_order, "repayment": repayment}}


def deterministic_protocol_review(repository: str, excerpts: list[dict[str, Any]]) -> dict[str, Any]:
    """Dispatch only recognized protocol families; fail closed for unsupported inputs."""
    if not isinstance(repository, str) or not isinstance(excerpts, list):
        raise TypeError("repository must be a string and excerpts must be a list")
    name = repository.casefold()
    if "aave" in name:
        result = review_aave(excerpts)
    elif "uniswap" in name:
        result = review_uniswap_v2(excerpts)
    else:
        result = {"protocol": "unknown", "topics": {}, "status": "unsupported_protocol"}
    result["source_scope"] = "verified_excerpt_only"
    result["exploitability_assessed"] = False
    return result
