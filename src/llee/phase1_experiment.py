"""
Phase 1 — Parser Fidelity Experiment

Runs all corpus segments through 5 conditions and computes metrics:
  A: Baseline — unconstrained LLM free text (no schema)
  B: Baseline — JSON schema, no evidence grading
  C: Ablation — LLEE with binary evidence (HAS_EVIDENCE / NO_EVIDENCE)
  D: Ablation — LLEE with coarse materials (3 values only)
  F: LLEE Full — complete pipeline

Usage:
  python -m llee.phase1_experiment --provider glm --condition F --segments 3
  python -m llee.phase1_experiment --provider glm --condition all
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=True)

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore

from .corpus_selections import CORPUS_SEGMENTS
from .parser_prompt import SYSTEM_PROMPT, EVIDENCE_RULES, build_parse_prompt
from .schema import WorldStateDelta
from .stability_test import (
    make_client,
    normalize_delta,
    validate_delta,
    extract_evidence_levels,
    extract_emotion_labels,
)

# ─── Condition Prompts ────────────────────────────────────────────────────────

PROMPT_A = """You are a narrative analysis assistant. Read the passage and describe the scene in free text. Include:
- Characters present and their emotional states
- Visual environment (lighting, colors, materials)
- Sounds and atmosphere
- Any actions taking place

Output your analysis as plain text paragraphs."""

PROMPT_B = """You are a narrative scene extractor. Read the passage and output a JSON object with this structure:
{{
  "entities": [{{ "id": "name", "emotion": "label", "action": "verb" }}],
  "scene_type": "type",
  "lighting": "description",
  "sounds": ["sound1", "sound2"],
  "atmosphere": "description",
  "tension": 0.0
}}
No evidence grading. Just extract what you see."""

PROMPT_C = """You are the LLEE Parser — a structured world-state extractor for narrative rendering.

Your task: read a narrative passage and output a WorldStateDelta JSON object.

Evidence is BINARY only:
- HAS_EVIDENCE: the text provides some basis for this value (confidence = 0.7)
- NO_EVIDENCE: no textual basis (confidence = 0.0, value = UNDEFINED)

Do NOT use fine-grained evidence levels. Every piece of information is either evidenced or not.

{output_format}"""

PROMPT_D_RULES = """
Materials are LIMITED to 3 coarse values only:
- "organic" (wood, cloth, skin, plants)
- "mineral" (stone, metal, glass, crystal)
- "fluid" (water, fog, smoke, fire)

Scene types are LIMITED to 3 values:
- "interior"
- "exterior"
- "abstract"
"""

# ─── Condition Runner ─────────────────────────────────────────────────────────

def run_condition_a(client: "OpenAI", model: str, passage: str, seg_id: str) -> dict:
    """Baseline A: free text, no schema."""
    try:
        response = client.chat.completions.create(
            model=model,
            max_tokens=1024,
            messages=[
                {"role": "system", "content": PROMPT_A},
                {"role": "user", "content": f"Analyze this passage:\n\n{passage}"},
            ],
            temperature=0.3,
        )
        text = response.choices[0].message.content or ""
        return {
            "raw_text": text,
            "word_count": len(text.split()),
            "has_emotion_words": any(w in text.lower() for w in [
                "fear", "joy", "sad", "anger", "happy", "afraid", "anxious",
                "calm", "tense", "gloomy", "dread", "panic",
            ]),
        }
    except Exception as e:
        return {"error": str(e)}


def run_condition_structured(
    client: "OpenAI", model: str, passage: str, seg_id: str, system_prompt: str
) -> dict | None:
    """Run a structured output condition (B, C, D, F)."""
    try:
        response = client.chat.completions.create(
            model=model,
            max_tokens=2048,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Parse this passage into structured output:\n\n{passage}"},
            ],
            temperature=0.3,
        )
    except Exception as e:
        return {"error": str(e)}

    msg = response.choices[0].message
    text = msg.content or ""
    if "{" not in text and hasattr(msg, "reasoning_content") and msg.reasoning_content:
        text = msg.reasoning_content

    text = text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    else:
        start = text.find("{")
        if start >= 0:
            depth = 0
            end = start
            for j in range(start, len(text)):
                if text[j] == "{":
                    depth += 1
                elif text[j] == "}":
                    depth -= 1
                    if depth == 0:
                        end = j + 1
                        break
            text = text[start:end]

    try:
        raw = json.loads(text)
    except json.JSONDecodeError:
        cleaned = text.replace('"..."', 'null').replace("'...'", "null").replace(", ...", "").replace("...", "")
        try:
            raw = json.loads(cleaned)
        except json.JSONDecodeError:
            return {"error": "JSON parse failure", "raw_preview": text[:200]}

    return raw


# ─── Metrics ──────────────────────────────────────────────────────────────────

def compute_fill_rate(delta: dict) -> float:
    """Fraction of non-None fields in the delta."""
    fields_checked = 0
    fields_filled = 0

    for eu in delta.get("entity_updates", []):
        if not isinstance(eu, dict):
            continue
        for key in ["emotion", "action", "position", "state", "material_tag"]:
            fields_checked += 1
            if eu.get(key) is not None:
                fields_filled += 1

    for group in ["visual", "sonic", "narrative"]:
        g = delta.get(group) or {}
        if not isinstance(g, dict):
            continue
        for key, val in g.items():
            fields_checked += 1
            if val is not None:
                fields_filled += 1

    return fields_filled / fields_checked if fields_checked > 0 else 0.0


def compute_env_fill_rate(delta: dict) -> float:
    """Fraction of environment-specific fields that are filled."""
    env_fields = 0
    env_filled = 0

    vis = delta.get("visual") or {}
    for key in ["lights", "atmosphere", "scene_type", "scene_features"]:
        env_fields += 1
        val = vis.get(key)
        if val is not None and val != [] and val != {}:
            env_filled += 1

    sonic = delta.get("sonic") or {}
    for key in ["reverb", "ambient_sounds", "music_tension"]:
        env_fields += 1
        val = sonic.get(key)
        if val is not None and val != [] and val != "none":
            env_filled += 1

    return env_filled / env_fields if env_fields > 0 else 0.0


def check_iei_leak(delta: dict, expected_neutral: bool) -> bool:
    """Returns True if IEI leak detected (emotion assigned on neutral passage)."""
    if not expected_neutral:
        return False
    for eu in delta.get("entity_updates", []):
        if not isinstance(eu, dict):
            continue
        em = eu.get("emotion") or {}
        val = em.get("value", "neutral")
        ev = em.get("evidence") or {}
        level = ev.get("level", "undefined")
        if val not in ("neutral", "undefined", "") and level != "undefined":
            return True
    return False


# ─── Main Experiment ──────────────────────────────────────────────────────────

OUTPUT_FORMAT_HINT = """
Output a WorldStateDelta JSON. Include entity_updates, visual, sonic, narrative fields.
Use evidence levels: explicit, behavioral, atmospheric, contextual, character, undefined.
"""

CONDITIONS = {
    "A": "free_text",
    "B": "json_no_evidence",
    "C": "binary_evidence",
    "D": "coarse_material",
    "F": "llee_full",
}


def run_experiment(
    provider: str,
    condition: str,
    max_segments: int = 0,
) -> dict[str, Any]:
    client, model = make_client(provider)
    print(f"Provider: {provider} | Model: {model} | Condition: {condition}")

    segments = list(CORPUS_SEGMENTS.items())
    if max_segments > 0:
        segments = segments[:max_segments]

    results: dict[str, Any] = {}

    for seg_id, seg in segments:
        passage = seg["text"]
        is_neutral = seg.get("expected_iei", False) is False and "neutral" in seg_id
        print(f"\n[{seg_id}] condition={condition}...", end=" ")

        if condition == "A":
            raw = run_condition_a(client, model, passage, seg_id)
            results[seg_id] = {
                "condition": "A",
                "output": raw,
                "fill_rate": None,
                "env_fill_rate": None,
                "iei_leak": None,
                "schema_valid": None,
            }
            print(f"words={raw.get('word_count', '?')}")
            continue

        # Build system prompt per condition
        if condition == "B":
            sys_prompt = PROMPT_B
        elif condition == "C":
            sys_prompt = PROMPT_C.format(output_format=OUTPUT_FORMAT_HINT)
        elif condition == "D":
            sys_prompt = SYSTEM_PROMPT + "\n" + PROMPT_D_RULES
        elif condition == "F":
            sys_prompt, _ = build_parse_prompt(passage, passage_id=seg_id)
            # For F, use the full prompt builder
            _, user_msg = build_parse_prompt(passage, passage_id=seg_id)
        else:
            print(f"Unknown condition: {condition}")
            continue

        if condition == "F":
            raw = run_condition_structured(client, model, passage, seg_id, sys_prompt)
        else:
            raw = run_condition_structured(client, model, passage, seg_id, sys_prompt)

        if raw is None or "error" in raw:
            results[seg_id] = {
                "condition": condition,
                "output": raw,
                "fill_rate": None,
                "env_fill_rate": None,
                "iei_leak": None,
                "schema_valid": False,
            }
            print(f"ERROR: {raw.get('error', 'unknown') if raw else 'null response'}")
            continue

        # For conditions B-F, try to validate as WorldStateDelta
        try:
            normalized = normalize_delta(raw)
        except Exception:
            normalized = raw

        schema_ok, schema_err = validate_delta(normalized)
        fill = compute_fill_rate(raw)
        env_fill = compute_env_fill_rate(raw)
        iei = check_iei_leak(raw, is_neutral)

        evidence_levels = extract_evidence_levels(raw)
        emotion_labels = extract_emotion_labels(raw)

        results[seg_id] = {
            "condition": condition,
            "schema_valid": schema_ok,
            "fill_rate": round(fill, 3),
            "env_fill_rate": round(env_fill, 3),
            "iei_leak": iei,
            "evidence_levels": evidence_levels,
            "emotion_labels": emotion_labels,
            "output": raw,
        }

        status = "OK" if schema_ok else "SCHEMA_ERR"
        print(f"fill={fill:.0%} env={env_fill:.0%} iei={'LEAK' if iei else 'clean'} [{status}]")

    return results


def save_experiment(results: dict[str, Any], provider: str, condition: str, model: str):
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = Path(__file__).resolve().parents[2] / "tasks"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"phase1-{condition}-{provider}-{ts}.json"

    record = {
        "timestamp": ts,
        "provider": provider,
        "model": model,
        "condition": condition,
        "segments": {},
    }
    for seg_id, r in results.items():
        entry = {k: v for k, v in r.items() if k != "output"}
        entry["output_preview"] = str(r.get("output", ""))[:300]
        record["segments"][seg_id] = entry

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to {out_path}")


def print_experiment_summary(results: dict[str, Any], condition: str):
    print(f"\n{'='*60}")
    print(f"PHASE 1 — CONDITION {condition} SUMMARY")
    print(f"{'='*60}")

    valid = sum(1 for r in results.values() if r.get("schema_valid"))
    total = len(results)
    fills = [r["fill_rate"] for r in results.values() if r["fill_rate"] is not None]
    env_fills = [r["env_fill_rate"] for r in results.values() if r["env_fill_rate"] is not None]
    iei_leaks = sum(1 for r in results.values() if r.get("iei_leak"))

    print(f"Schema valid: {valid}/{total}")
    if fills:
        print(f"Avg fill rate: {sum(fills)/len(fills):.0%}")
    if env_fills:
        print(f"Avg env fill rate: {sum(env_fills)/len(env_fills):.0%}")
    print(f"IEI leaks: {iei_leaks}")
    print(f"{'='*60}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LLEE Phase 1 Experiment")
    parser.add_argument("--provider", default="glm", help="API provider")
    parser.add_argument("--condition", default="F", choices=["A", "B", "C", "D", "F", "all"],
                        help="Experiment condition")
    parser.add_argument("--segments", type=int, default=0, help="Max segments (0=all)")
    args = parser.parse_args()

    from .stability_test import PROVIDERS, MODEL_OVERRIDES

    conditions = ["A", "B", "C", "D", "F"] if args.condition == "all" else [args.condition]

    for cond in conditions:
        results = run_experiment(args.provider, cond, args.segments)
        print_experiment_summary(results, cond)
        model_name = MODEL_OVERRIDES.get(args.provider) or os.environ.get(
            PROVIDERS[args.provider]["model_env"], args.provider
        )
        save_experiment(results, args.provider, cond, model_name)
