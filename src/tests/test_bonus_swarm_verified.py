from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from bonus import build_cases
from bonus.swarm_verified import run_claim as swarm_verified, verify_facts
from lab8.db import connect, init_store, load_json, load_jsonl
from lab8.durability import InjectedCrash
from lab8.metrics import trial_pass
from lab8.shapes import SHAPES

BONUS = Path(__file__).resolve().parents[1] / "bonus"
B_WORLD = load_json(BONUS / "world.json")
B_CLAIMS = load_jsonl(BONUS / "cases.jsonl")
B_BY_ID = {row["claim_id"]: row for row in B_CLAIMS}
SEEDS = [11, 22, 33, 44, 55]


def _events(result, kind: str) -> list[dict]:
    body = json.loads(Path(result.trace_path).read_text(encoding="utf-8"))
    assert body["run_id"] == result.run_id
    return [e["payload"] for e in body["events"] if e["kind"] == kind]


def _ledger(store, claim_id: str) -> int:
    conn = connect(store)
    try:
        return conn.execute("SELECT COUNT(*) FROM refund_ledger WHERE claim_id = ?", (claim_id,)).fetchone()[0]
    finally:
        conn.close()


@pytest.fixture
def bonus_db(tmp_path: Path) -> Path:
    store = tmp_path / "bonus.sqlite"
    init_store(store, B_WORLD, B_CLAIMS).close()
    return store


def test_verify_facts_reports_only_disagreeing_fields():
    structured = {"delay_days": 2, "status": "delivered", "damage_verified": False, "shipping_fee_vnd": 20000}
    assert verify_facts(dict(structured), structured) == {}
    used = dict(structured, delay_days=5, shipping_fee_vnd=1)  # fee is not a verified fact
    assert verify_facts(used, structured) == {"delay_days": {"used": 5, "structured": 2}}


def test_verifier_fixes_swarm_seed55_weakness_on_public_c002(public_db, tmp_path):
    # Swarm gốc trả 20.000 cho C-002 ở seed 55 vì tin "trễ 5 ngày" trong ticket.
    other = tmp_path / "swarm.sqlite"
    other.write_bytes(Path(public_db).read_bytes())
    baseline = SHAPES["swarm"]("C-002", seed=55, store_path=str(other))
    assert baseline.status == "resolved" and baseline.proposal_amount == 20000

    result = swarm_verified("C-002", seed=55, store_path=str(public_db))
    assert result.status == "denied"
    assert result.proposal_amount == 0
    assert _ledger(public_db, "C-002") == 0
    overrides = _events(result, "verifier_override")
    assert len(overrides) == 1
    assert overrides[0]["mismatches"] == {"delay_days": {"used": 5, "structured": 2}}
    assert (overrides[0]["amount_before"], overrides[0]["amount_after"]) == (20000, 0)


def test_no_override_when_facts_agree(public_db):
    result = swarm_verified("C-001", seed=11, store_path=str(public_db))
    assert result.status == "resolved" and result.proposal_amount == 35000
    assert _events(result, "verifier_override") == []


@pytest.mark.parametrize("shape", ["workflow", "swarm_verified"])
@pytest.mark.parametrize("claim_id", sorted(B_BY_ID))
def test_adversarial_cases_pass_every_seed(bonus_db, tmp_path, shape, claim_id):
    run = swarm_verified if shape == "swarm_verified" else SHAPES[shape]
    for seed in SEEDS:
        store = tmp_path / f"{shape}-{claim_id}-{seed}.sqlite"
        store.write_bytes(Path(bonus_db).read_bytes())
        started_at = time.time()
        result = run(claim_id, seed=seed, store_path=str(store))
        conn = connect(store)
        try:
            passed, reason = trial_pass(result.as_dict(), B_BY_ID[claim_id]["expected"], conn, started_at=started_at)
        finally:
            conn.close()
        assert passed, f"{shape} {claim_id} seed {seed}: {reason}"


def test_crash_propagates_and_resume_keeps_one_refund(public_db):
    with pytest.raises(InjectedCrash):
        swarm_verified("C-001", seed=11, store_path=str(public_db), crash_at="after_effect_before_checkpoint")
    result = swarm_verified("C-001", seed=11, store_path=str(public_db))
    assert result.status == "resolved"
    assert _ledger(public_db, "C-001") == 1
    assert result.committed_audit_count == 1


def test_case_files_match_handwritten_builder():
    world, claims = build_cases.build()
    assert world == B_WORLD
    assert claims == B_CLAIMS
    assert len(claims) >= 8
