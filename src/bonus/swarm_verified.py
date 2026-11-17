"""Bonus B3 — swarm plus a code verifier before the write.

Same flow, same model calls and same REFERENCE_WEAKNESS as
`lab8.shapes.swarm_reference` (peer, parse, read-only investigators, one seed in
five trusts the ticket delay). The only change: before `issue_refund`, a
verifier written in code compares every fact used for the quote
(`delay_days`, `status`, `damage_verified`) with the structured order from
`lookup_order`. If any fact disagrees, it re-quotes once from the structured
order and records a `verifier_override` event in the trace.

Register at run time, do not edit lab8/shapes/__init__.py:

    python -m lab8.benchmark --shapes workflow,swarm,swarm_verified \
        --extra-shape swarm_verified=bonus.swarm_verified:run_claim ...
"""

from __future__ import annotations

import sqlite3
from typing import Any

from lab8.db import connect
from lab8.durability import InjectedCrash, issue_refund
from lab8.handoff import make_handoff
from lab8.mock_llm import complete, parse_delay_days
from lab8.runtime import run_readonly_investigators
from lab8.schemas import Budget, RunResult, make_run_id
from lab8.shapes.common import finish, safe_dump
from lab8.tools import compute_compensation, tool_cost
from lab8.trace import Trace

SHAPE = "swarm_verified"
VERIFIED_FACTS = ("delay_days", "status", "damage_verified")
MAX_REPAIR_ROUNDS = 1


def run_claim(
    claim_id: str,
    *,
    seed: int,
    store_path: str,
    crash_at: str | None = None,
) -> RunResult:
    conn = connect(store_path)
    try:
        return _run(conn, claim_id, seed=seed, crash_at=crash_at)
    finally:
        conn.close()


def verify_facts(used: dict[str, Any], structured: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Facts the quote relied on that disagree with the structured order row."""
    mismatches = {}
    for key in VERIFIED_FACTS:
        if used.get(key) != structured.get(key):
            mismatches[key] = {"used": used.get(key), "structured": structured.get(key)}
    return mismatches


def _run(conn: sqlite3.Connection, claim_id: str, *, seed: int, crash_at: str | None) -> RunResult:
    budget = Budget()
    trace = Trace(make_run_id(SHAPE, claim_id, seed))

    def done(status: str, proposal: int, reason: str | None) -> RunResult:
        trace.add("decision", {"status": status, "proposal_amount": proposal, "reason": reason})
        return finish(
            conn,
            shape=SHAPE,
            claim_id=claim_id,
            seed=seed,
            status=status,
            proposal_amount=proposal,
            budget=budget,
            trace=trace,
            error_reason=reason,
        )

    # --- unchanged swarm flow -------------------------------------------------
    budget.add_tool(tool_cost())
    claim_row = conn.execute(
        "SELECT claim_id, principal_id, order_id, ticket FROM claims WHERE claim_id = ?",
        (claim_id,),
    ).fetchone()
    if claim_row is None:
        trace.add("error", {"reason": "unknown_claim"})
        return done("failed", 0, "unknown_claim")

    ticket = claim_row["ticket"]
    complete(budget, seed=seed, purpose="peer", prompt=ticket)
    parsed_delay = parse_delay_days(ticket)
    complete(budget, seed=seed, purpose="parse", prompt=ticket)

    if not claim_row["order_id"]:
        complete(budget, seed=seed, purpose="draft", prompt="needs_info")
        return done("needs_info", 0, "missing_order_id")

    handoff = make_handoff(
        request_id=f"REQ-{claim_id}",
        claim_id=claim_id,
        task="check_applicable_policy",
        facts={},
        allowed_tools=["lookup_order", "lookup_policy", "compute_compensation"],
    )
    trace.add("handoff", safe_dump(handoff))
    investigated = run_readonly_investigators(conn, budget, handoff, principal_id=claim_row["principal_id"])
    order_view = investigated["tools"].get("lookup_order", {})
    trace.add(
        "investigator",
        {
            "lookup_order": order_view,
            "policy_count": len((investigated["tools"].get("lookup_policy") or {}).get("policies") or []),
        },
    )
    if not order_view.get("visible"):
        complete(budget, seed=seed, purpose="draft", prompt="escalated")
        return done("escalated", 0, order_view.get("reason"))

    structured = dict(order_view["order"])
    order = dict(structured)
    # REFERENCE_WEAKNESS kept on purpose: one seed in five trusts the ticket delay.
    if parsed_delay is not None and parsed_delay != int(order["delay_days"]) and seed % 5 == 0:
        order["delay_days"] = parsed_delay
        trace.add("model_override", {"delay_days": parsed_delay})

    quote_payload = investigated["tools"]["compute_compensation"]
    if order["delay_days"] != structured["delay_days"]:
        budget.add_tool(tool_cost())
        quote_payload = compute_compensation(conn, order)

    # --- B3: code verifier before the write ----------------------------------
    for _ in range(MAX_REPAIR_ROUNDS):
        mismatches = verify_facts(order, structured)
        if not mismatches:
            break
        budget.add_tool(tool_cost())
        repaired = compute_compensation(conn, structured)
        trace.add(
            "verifier_override",
            {
                "mismatches": mismatches,
                "amount_before": int(quote_payload["amount_vnd"]),
                "amount_after": int(repaired["amount_vnd"]),
            },
        )
        order, quote_payload = structured, repaired
    else:
        if verify_facts(order, structured):
            return done("failed", 0, "verifier_unresolved")

    proposal = int(quote_payload["amount_vnd"])
    trace.add("quote", quote_payload)
    complete(budget, seed=seed, purpose="draft", prompt=f"proposal={proposal}")

    if proposal <= 0:
        return done("denied", 0, quote_payload.get("reason"))

    try:
        outcome = issue_refund(conn, claim_id, proposal, crash_at=crash_at)
    except InjectedCrash:
        trace.add("crash", {"at": crash_at})
        trace.write()
        raise

    if not outcome["ok"]:
        return done("failed" if outcome["conflict"] else "denied", proposal, outcome["reason"])
    return done("resolved", proposal, None)
