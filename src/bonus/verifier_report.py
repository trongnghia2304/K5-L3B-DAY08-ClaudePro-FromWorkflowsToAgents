"""Summarize B3 benchmark reports and count verifier interventions from traces.

Run after the two benchmark commands in report/team/bonus_report.md:

    python -m bonus.verifier_report

Reads reports/bonus_b3_public.json and reports/bonus_b3_adversarial.json plus
traces/<run_id>.json of every swarm_verified trial, writes reports/bonus_b3.json.
"""

from __future__ import annotations

import json
from pathlib import Path

REPORTS = {
    "public": Path("reports/bonus_b3_public.json"),
    "adversarial": Path("reports/bonus_b3_adversarial.json"),
}
METRICS = ("pass_rate", "pass_5", "seed_variance", "seed_min", "seed_max", "cost_per_success_vnd", "mean_model_calls", "mean_tool_calls")
OUT = Path("reports/bonus_b3.json")


def _overrides(trace_path: Path) -> list[dict]:
    if not trace_path.exists():
        return []
    body = json.loads(trace_path.read_text(encoding="utf-8"))
    return [e["payload"] for e in body.get("events", []) if e.get("kind") == "verifier_override"]


def summarize(report: dict, traces_dir: Path = Path("traces")) -> dict:
    by_shape = {shape: {k: stats.get(k) for k in METRICS} for shape, stats in report["by_shape"].items()}
    failures = {
        shape: sorted(f"{t['claim_id']}@s{t['seed']}:{t['reason']}" for t in report["trials"] if t["shape"] == shape and not t["passed"])
        for shape in report["by_shape"]
    }
    interventions = []
    for trial in report["trials"]:
        if trial["shape"] != "swarm_verified":
            continue
        for payload in _overrides(traces_dir / f"{trial['run_id']}.json"):
            interventions.append(
                {
                    "run_id": trial["run_id"],
                    "fields": sorted(payload["mismatches"]),
                    "amount_before": payload["amount_before"],
                    "amount_after": payload["amount_after"],
                    "changed_amount": payload["amount_before"] != payload["amount_after"],
                    "passed": trial["passed"],
                }
            )
    sv_trials = sum(1 for t in report["trials"] if t["shape"] == "swarm_verified")
    return {
        "controlled_variables": report["controlled_variables"],
        "by_shape": by_shape,
        "failures": failures,
        "verifier": {
            "trials": sv_trials,
            "interventions": len(interventions),
            "interventions_changed_amount": sum(1 for i in interventions if i["changed_amount"]),
            "details": interventions,
        },
    }


def main() -> int:
    out = {name: summarize(json.loads(path.read_text(encoding="utf-8"))) for name, path in REPORTS.items()}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for name, part in out.items():
        v = part["verifier"]
        print(f"{name}: verifier interventions {v['interventions']}/{v['trials']} (changed amount {v['interventions_changed_amount']})")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
