"""
Phase 1 Round 2 — Decay Rate Sensitivity Analysis

Perturbs ATMOSPHERIC and CONTEXTUAL decay rates by ±20%,
re-runs WSM on existing F-condition deltas, measures how long
evidence persists above threshold.

No API calls needed — operates on saved experiment data.
"""

from __future__ import annotations

import json
from pathlib import Path
from copy import deepcopy

from .schema import (
    WorldStateDelta,
    Evidence,
    EvidenceLevel,
    EVIDENCE_DECAY_RATE,
    EVIDENCE_CONFIDENCE_CEILING,
    NARRATIVE_BREAK_PENALTY,
)
from .stability_test import normalize_delta


def simulate_decay_sequence(
    deltas: list[dict],
    atm_rate: float,
    ctx_rate: float,
    threshold: float = 0.05,
) -> dict:
    """Simulate WSM decay on a sequence of deltas with custom rates.

    Returns stats on how long each evidence type persists above threshold.
    """
    custom_rates = dict(EVIDENCE_DECAY_RATE)
    custom_rates[EvidenceLevel.ATMOSPHERIC] = atm_rate
    custom_rates[EvidenceLevel.CONTEXTUAL] = ctx_rate

    atm_persist_turns = []
    ctx_persist_turns = []

    atm_confidence_trajectory = []
    ctx_confidence_trajectory = []

    current_atm_conf = 0.0
    current_ctx_conf = 0.0
    atm_turns_since_set = 0
    ctx_turns_since_set = 0

    for i, delta in enumerate(deltas):
        evidence_levels = []
        for eu in delta.get("entity_updates", []):
            if not isinstance(eu, dict):
                continue
            ev = (eu.get("emotion") or {}).get("evidence") or {}
            level = ev.get("level", "undefined")
            conf = ev.get("confidence", 0.0)
            if isinstance(conf, (int, float)):
                if level == "atmospheric":
                    current_atm_conf = min(conf, EVIDENCE_CONFIDENCE_CEILING.get(EvidenceLevel.ATMOSPHERIC, 0.3))
                    atm_turns_since_set = 0
                elif level == "contextual":
                    current_ctx_conf = min(conf, EVIDENCE_CONFIDENCE_CEILING.get(EvidenceLevel.CONTEXTUAL, 0.5))
                    ctx_turns_since_set = 0

        narrative = delta.get("narrative") or {}
        is_break = narrative.get("narrative_break", False)

        if current_atm_conf > threshold:
            current_atm_conf *= atm_rate
            if is_break:
                current_atm_conf *= NARRATIVE_BREAK_PENALTY.get(EvidenceLevel.ATMOSPHERIC, 0.0)
            atm_turns_since_set += 1
        else:
            if atm_turns_since_set > 0:
                atm_persist_turns.append(atm_turns_since_set)
            atm_turns_since_set = 0

        if current_ctx_conf > threshold:
            current_ctx_conf *= ctx_rate
            if is_break:
                current_ctx_conf *= NARRATIVE_BREAK_PENALTY.get(EvidenceLevel.CONTEXTUAL, 0.5)
            ctx_turns_since_set += 1
        else:
            if ctx_turns_since_set > 0:
                ctx_persist_turns.append(ctx_turns_since_set)
            ctx_turns_since_set = 0

        atm_confidence_trajectory.append(round(current_atm_conf, 4))
        ctx_confidence_trajectory.append(round(current_ctx_conf, 4))

    if atm_turns_since_set > 0:
        atm_persist_turns.append(atm_turns_since_set)
    if ctx_turns_since_set > 0:
        ctx_persist_turns.append(ctx_turns_since_set)

    return {
        "atm_rate": atm_rate,
        "ctx_rate": ctx_rate,
        "atm_avg_persist": sum(atm_persist_turns) / len(atm_persist_turns) if atm_persist_turns else 0,
        "ctx_avg_persist": sum(ctx_persist_turns) / len(ctx_persist_turns) if ctx_persist_turns else 0,
        "atm_persist_events": len(atm_persist_turns),
        "ctx_persist_events": len(ctx_persist_turns),
        "atm_trajectory": atm_confidence_trajectory,
        "ctx_trajectory": ctx_confidence_trajectory,
    }


def run_sensitivity_analysis(experiment_file: str | Path) -> dict:
    """Run ±20% sensitivity analysis on a saved experiment file."""
    with open(experiment_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    deltas = []
    for seg_id, seg_data in data["segments"].items():
        preview = seg_data.get("output_preview", "")
        if preview.startswith("{"):
            try:
                raw = eval(preview + ("}" * (preview.count("{") - preview.count("}"))))
            except Exception:
                continue
        deltas.append(seg_data)

    all_outputs = []
    for seg_id in data["segments"]:
        seg = data["segments"][seg_id]
        all_outputs.append(seg)

    baseline_atm = EVIDENCE_DECAY_RATE[EvidenceLevel.ATMOSPHERIC]
    baseline_ctx = EVIDENCE_DECAY_RATE[EvidenceLevel.CONTEXTUAL]

    variants = {
        "baseline": (baseline_atm, baseline_ctx),
        "+20%": (min(baseline_atm * 1.2, 1.0), min(baseline_ctx * 1.2, 1.0)),
        "-20%": (baseline_atm * 0.8, baseline_ctx * 0.8),
    }

    results = {}
    for name, (atm, ctx) in variants.items():
        sim = simulate_decay_sequence(all_outputs, atm, ctx)
        results[name] = {
            "atm_rate": round(atm, 3),
            "ctx_rate": round(ctx, 3),
            "atm_avg_persist_turns": round(sim["atm_avg_persist"], 2),
            "ctx_avg_persist_turns": round(sim["ctx_avg_persist"], 2),
            "atm_persist_events": sim["atm_persist_events"],
            "ctx_persist_events": sim["ctx_persist_events"],
        }

    return {
        "source_file": str(experiment_file),
        "model": data.get("model", "unknown"),
        "n_segments": len(data["segments"]),
        "variants": results,
    }


def theoretical_persist_turns(rate: float, ceiling: float, threshold: float = 0.05) -> float:
    """Calculate theoretical number of turns for confidence to decay from ceiling to threshold."""
    if rate >= 1.0:
        return float("inf")
    if rate <= 0.0:
        return 0.0
    import math
    return math.log(threshold / ceiling) / math.log(rate)


if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("DECAY RATE SENSITIVITY ANALYSIS")
    print("=" * 60)

    print("\n--- Theoretical Persistence (turns to decay below 0.05) ---")
    for name, (atm, ctx) in [
        ("baseline", (0.7, 0.9)),
        ("+20%", (0.84, 1.0)),
        ("-20%", (0.56, 0.72)),
    ]:
        atm_turns = theoretical_persist_turns(atm, 0.30)
        ctx_turns = theoretical_persist_turns(ctx, 0.50)
        print(f"  {name:>8}: ATM(rate={atm}) = {atm_turns:.1f} turns, CTX(rate={ctx}) = {ctx_turns:.1f} turns")

    print("\n--- Empirical Analysis on Saved Experiments ---")
    tasks_dir = Path(__file__).resolve().parents[2] / "tasks"
    f_files = sorted(tasks_dir.glob("phase1-F-*.json"))

    for fpath in f_files:
        print(f"\n  File: {fpath.name}")
        result = run_sensitivity_analysis(fpath)
        for vname, vdata in result["variants"].items():
            print(f"    {vname:>8}: ATM persist={vdata['atm_avg_persist_turns']:.1f} turns "
                  f"({vdata['atm_persist_events']} events), "
                  f"CTX persist={vdata['ctx_avg_persist_turns']:.1f} turns "
                  f"({vdata['ctx_persist_events']} events)")

    out_path = tasks_dir / "sensitivity-analysis.json"
    all_results = {}
    for fpath in f_files:
        all_results[fpath.name] = run_sensitivity_analysis(fpath)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to {out_path}")
