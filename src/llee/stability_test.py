"""
Phase 0.5 — Parser Stability Validation (multi-model)

Supported providers (all via OpenAI-compatible chat completions):
  glm        — GLM-4.5-air (ZhipuAI)
  deepseek   — DeepSeek Reasoner
  claude     — Claude Opus via relay
  doubao     — Doubao Seed (Volcengine)

Usage:
  python -m llee.stability_test --provider glm --runs 1 --segments 2   # quick smoke test
  python -m llee.stability_test --provider claude --runs 5             # 5 runs, all segments
  python -m llee.stability_test --dry-run                              # no API calls
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=True)

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore

from .corpus_selections import CORPUS_SEGMENTS
from .parser_prompt import build_parse_prompt
from .schema import WorldStateDelta

PROVIDERS = {
    "glm": {
        "api_key_env": "GLM_API_KEY",
        "base_url_env": "GLM_BASE_URL",
        "model_env": "GLM_MODEL",
    },
    "deepseek": {
        "api_key_env": "DEEPSEEK_API_KEY",
        "base_url_env": "DEEPSEEK_BASE_URL",
        "model_env": "DEEPSEEK_MODEL",
    },
    "claude": {
        "api_key_env": "ANTHROPIC_API_KEY",
        "base_url_env": "ANTHROPIC_BASE_URL",
        "model_env": "ANTHROPIC_MODEL",
    },
    "doubao": {
        "api_key_env": "DOUBAO_API_KEY",
        "base_url_env": "DOUBAO_BASE_URL",
        "model_env": "DOUBAO_MODEL",
    },
    "deepseek-chat": {
        "api_key_env": "DEEPSEEK_API_KEY",
        "base_url_env": "DEEPSEEK_BASE_URL",
        "model_env": "DEEPSEEK_MODEL",
    },
    "claude-sonnet": {
        "api_key_env": "ANTHROPIC_API_KEY",
        "base_url_env": "ANTHROPIC_BASE_URL",
        "model_env": "ANTHROPIC_MODEL",
    },
    "claude-opus": {
        "api_key_env": "ANTHROPIC_API_KEY",
        "base_url_env": "ANTHROPIC_BASE_URL",
        "model_env": "ANTHROPIC_MODEL",
    },
}

# Model overrides per provider alias
MODEL_OVERRIDES = {
    "deepseek-chat": "deepseek-chat",
    "claude-sonnet": "claude-sonnet-4-6",
    "claude-opus": "claude-opus-4-6",
}


def make_client(provider: str) -> tuple["OpenAI", str]:
    if OpenAI is None:
        print("ERROR: openai package not installed. Run: pip install openai")
        sys.exit(1)
    cfg = PROVIDERS[provider]
    api_key = os.environ.get(cfg["api_key_env"])
    base_url = os.environ.get(cfg["base_url_env"])
    model = MODEL_OVERRIDES.get(provider) or os.environ.get(cfg["model_env"], "")
    if not api_key:
        print(f"ERROR: {cfg['api_key_env']} not set in .env")
        sys.exit(1)
    # base_url should point to the OpenAI-compatible endpoint
    # GLM: https://open.bigmodel.cn/api/paas/v4/ already has the right path
    # DeepSeek: https://api.deepseek.com/v1 already correct
    # Claude relay: needs /v1 appended
    # Doubao: special endpoint, use as-is
    client = OpenAI(api_key=api_key, base_url=base_url)
    return client, model


# ─── Schema Validation ────────────────────────────────────────────────────────

VALID_SOURCES = {"text", "context", "predicted", "external", "cross_modal", "character_prior"}
SOURCE_MAP = {
    "text": "text", "context": "context", "predicted": "predicted",
    "external": "external", "cross_modal": "cross_modal", "character_prior": "character_prior",
    "narrative": "text", "dialogue": "text", "description": "text",
    "direct_text": "text", "text_explicit": "text", "text_behavioral": "text",
    "inference": "context", "contextual": "context", "implied": "context",
    "observation": "text", "behavioral": "text",
}

VALID_LEVELS = {"explicit", "behavioral", "atmospheric", "contextual", "character", "undefined"}
LEVEL_MAP = {
    "explicit": "explicit", "behavioral": "behavioral", "atmospheric": "atmospheric",
    "contextual": "contextual", "character": "character", "undefined": "undefined",
    "direct": "explicit", "implied": "contextual", "inferred": "contextual",
    "environmental": "atmospheric", "ambient": "atmospheric",
}


def _normalize_evidence(ev: dict):
    """Normalize evidence source and level to valid enum values."""
    src = ev.get("source")
    if isinstance(src, str) and src.lower().replace(" ", "_") not in VALID_SOURCES:
        ev["source"] = SOURCE_MAP.get(src.lower().replace(" ", "_"), "text")

    lvl = ev.get("level")
    if isinstance(lvl, str) and lvl.lower().replace(" ", "_") not in VALID_LEVELS:
        ev["level"] = LEVEL_MAP.get(lvl.lower().replace(" ", "_"), "undefined")

    span = ev.get("source_span")
    if isinstance(span, list) and len(span) == 2:
        ev["source_span"] = tuple(span)
    elif span is not None and not isinstance(span, tuple):
        ev["source_span"] = None


def normalize_delta(raw: dict) -> dict:
    """Fix common type mismatches from LLM output before Pydantic validation."""
    for eu in raw.get("entity_updates", []):
        # position: convert dict/list to tuple
        pos = eu.get("position")
        if isinstance(pos, dict):
            eu["position"] = (pos.get("x", 0), pos.get("y", 0), pos.get("z", 0))
        elif isinstance(pos, list) and len(pos) == 3:
            eu["position"] = tuple(pos)

        # state: convert dict to string
        if isinstance(eu.get("state"), dict):
            eu["state"] = str(eu["state"].get("value", eu["state"]))

        # emotion.evidence: normalize source and source_span
        em = eu.get("emotion") or {}
        ev = em.get("evidence") or {}
        _normalize_evidence(ev)

        # action.evidence: same normalization
        act = eu.get("action")
        if isinstance(act, str):
            eu["action"] = {"verb": act}
            act = eu["action"]
        if isinstance(act, dict):
            aev = act.get("evidence") or {}
            _normalize_evidence(aev)

    # sonic: normalize reverb to valid enum values
    sonic = raw.get("sonic") or {}
    reverb = sonic.get("reverb")
    if isinstance(reverb, str):
        REVERB_MAP = {
            "none": "none", "room_small": "room_small", "room_large": "room_large",
            "cave": "cave", "outdoor_open": "outdoor_open", "outdoor_forest": "outdoor_forest",
            "small_room": "room_small", "large_room": "room_large", "large_hall": "room_large",
            "hall": "room_large", "cathedral": "room_large", "outdoor": "outdoor_open",
            "forest": "outdoor_forest", "open": "outdoor_open", "interior": "room_small",
            "classroom": "room_small", "indoor": "room_small",
        }
        sonic["reverb"] = REVERB_MAP.get(reverb.lower().replace(" ", "_"), "none")

    # sonic.ambient_sounds: ensure each is a dict with 'id'
    sonic = raw.get("sonic") or {}
    sounds = sonic.get("ambient_sounds") or []
    normalized_sounds = []
    for snd in sounds:
        if isinstance(snd, str):
            snd = {"id": snd, "sound_type": snd, "intensity": 0.5}
        if isinstance(snd, dict):
            if "id" not in snd:
                snd["id"] = snd.get("sound_type", "unknown")
            if "sound_type" not in snd:
                snd["sound_type"] = snd.get("id", "unknown")
        normalized_sounds.append(snd)
    if sonic.get("ambient_sounds") is not None:
        sonic["ambient_sounds"] = normalized_sounds

    # visual.atmosphere: convert string to VisualAtmosphere-compatible dict
    vis = raw.get("visual") or {}
    atm = vis.get("atmosphere")
    if isinstance(atm, str):
        vis["atmosphere"] = {"fog_density": 0.0}
    elif isinstance(atm, list):
        vis["atmosphere"] = {"fog_density": 0.0}

    # visual.scene_type_evidence: normalize
    ste = vis.get("scene_type_evidence")
    if isinstance(ste, str):
        vis["scene_type_evidence"] = {"level": ste or "undefined", "source": "text", "confidence": 0.5}
    elif isinstance(ste, dict):
        lvl = ste.get("level", "")
        if not isinstance(lvl, str) or not lvl.strip():
            ste["level"] = "undefined"
        _normalize_evidence(ste)

    # visual.lights: ensure each is a dict with 'id'
    lights = vis.get("lights") or []
    normalized_lights = []
    for lt in lights:
        if isinstance(lt, str):
            lt = {"id": lt, "source_type": lt}
        if isinstance(lt, dict):
            if "id" not in lt:
                lt["id"] = lt.get("source_type", "light_0")
            d = lt.get("direction")
            if isinstance(d, (list, tuple)) and len(d) == 2:
                lt["direction"] = tuple(d)
            elif d is not None and not (isinstance(d, tuple) and len(d) == 2):
                lt["direction"] = None
        normalized_lights.append(lt)
    if vis.get("lights") is not None:
        vis["lights"] = normalized_lights

    # narrative.stage: normalize to valid values
    narr = raw.get("narrative") or {}
    stage = narr.get("stage")
    if isinstance(stage, str):
        VALID_STAGES = {"exposition", "rising", "climax", "falling", "resolution"}
        normalized = stage.lower().replace(" ", "_").replace("-", "_")
        STAGE_MAP = {
            "rising_action": "rising", "falling_action": "falling",
            "introduction": "exposition", "denouement": "resolution",
            "development": "rising", "setup": "exposition",
            "descriptive": "exposition", "establishing": "exposition",
            "tension": "rising", "suspense": "rising",
        }
        narr["stage"] = STAGE_MAP.get(normalized, normalized if normalized in VALID_STAGES else "exposition")

    return raw


def validate_delta(raw: dict) -> tuple[bool, str]:
    try:
        WorldStateDelta.model_validate(raw)
        return True, ""
    except Exception as e:
        return False, str(e)


def extract_evidence_levels(delta: dict) -> list[str]:
    levels = []
    for eu in delta.get("entity_updates", []):
        em = eu.get("emotion") or {}
        ev = em.get("evidence") or {}
        if lv := ev.get("level"):
            levels.append(lv)
        act = eu.get("action") or {}
        ev2 = act.get("evidence") or {}
        if lv2 := ev2.get("level"):
            levels.append(lv2)
    return levels


def extract_emotion_labels(delta: dict) -> list[str]:
    return [
        (eu.get("emotion") or {}).get("value", "")
        for eu in delta.get("entity_updates", [])
        if eu.get("emotion")
    ]


# ─── Single Run ───────────────────────────────────────────────────────────────

def run_single(client: "OpenAI", passage_id: str, passage: str, model: str) -> dict | None:
    system, user = build_parse_prompt(passage, passage_id=passage_id)

    try:
        response = client.chat.completions.create(
            model=model,
            max_tokens=2048,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.3,
        )
    except Exception as e:
        print(f"  [API error] {type(e).__name__}: {e}", file=sys.stderr)
        return None

    # Handle different response formats from various providers
    try:
        if isinstance(response, str):
            text = response
        elif hasattr(response, "choices") and response.choices:
            choice = response.choices[0]
            msg = choice.message
            # DeepSeek Reasoner: thinking goes in reasoning_content, answer in content
            text = msg.content or ""
            reasoning = ""
            if hasattr(msg, "reasoning_content") and msg.reasoning_content:
                reasoning = msg.reasoning_content
            # If content has no JSON, try reasoning_content as fallback
            if "{" not in text and reasoning:
                text = reasoning
        else:
            print(f"  [API error] unexpected response type: {type(response)}", file=sys.stderr)
            return None
    except Exception as e:
        print(f"  [Parse error] {type(e).__name__}: {e}", file=sys.stderr)
        return None

    text = text.strip()
    if not text:
        print(f"  [API error] empty content", file=sys.stderr)
        return None

    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    else:
        # Try to find a JSON object in free text (e.g. DeepSeek reasoning output)
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
        return json.loads(text)
    except json.JSONDecodeError:
        # Some models output "..." as placeholder — remove and retry
        cleaned = text.replace('"..."', 'null').replace("'...'", "null").replace(", ...", "").replace("...", "")
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            print(f"  [JSON parse error] {e}", file=sys.stderr)
            print(f"  Raw (first 200 chars): {text[:200]}", file=sys.stderr)
            return None


# ─── Consistency Metrics ──────────────────────────────────────────────────────

def consistency_score(items: list[list[str]]) -> float:
    if not items or all(len(x) == 0 for x in items):
        return 1.0
    max_len = max(len(x) for x in items)
    if max_len == 0:
        return 1.0
    scores = []
    for i in range(max_len):
        vals = [x[i] for x in items if i < len(x)]
        if not vals:
            continue
        majority_count = Counter(vals).most_common(1)[0][1]
        scores.append(majority_count / len(vals))
    return sum(scores) / len(scores) if scores else 1.0


# ─── Main ─────────────────────────────────────────────────────────────────────

def run_validation(
    n_runs: int,
    provider: str,
    dry_run: bool = False,
    max_segments: int = 0,
) -> dict[str, Any]:
    if not dry_run:
        client, model = make_client(provider)
        print(f"Provider: {provider} | Model: {model}")
    else:
        client, model = None, "dry-run"  # type: ignore

    results: dict[str, Any] = {}
    segments = list(CORPUS_SEGMENTS.items())
    if max_segments > 0:
        segments = segments[:max_segments]

    for seg_id, seg in segments:
        print(f"\n[{seg_id}] {n_runs} runs...")
        passage = seg["text"]

        compliance = 0
        evidence_runs: list[list[str]] = []
        emotion_runs: list[list[str]] = []
        errors: list[str] = []

        for i in range(n_runs):
            if dry_run:
                raw = {
                    "entity_updates": [],
                    "entity_removals": [],
                    "narrative": {"tension": 0.3, "stage": "exposition"},
                }
            else:
                raw = run_single(client, seg_id, passage, model)

            if raw is None:
                errors.append(f"run {i}: API/JSON failure")
                continue

            try:
                raw = normalize_delta(raw)
            except Exception as e:
                errors.append(f"run {i}: normalize — {str(e)[:60]}")
                continue

            ok, err = validate_delta(raw)
            if ok:
                compliance += 1
                evidence_runs.append(extract_evidence_levels(raw))
                emotion_runs.append(extract_emotion_labels(raw))
            else:
                errors.append(f"run {i}: schema — {err[:80]}")

            if n_runs >= 5 and (i + 1) % 5 == 0:
                print(f"  {i+1}/{n_runs} done, compliance: {compliance}/{i+1}")

        compliance_rate = compliance / n_runs if n_runs > 0 else 0.0
        ev_consistency = consistency_score(evidence_runs)
        em_consistency = consistency_score(emotion_runs)

        results[seg_id] = {
            "compliance_rate": compliance_rate,
            "evidence_consistency": ev_consistency,
            "emotion_consistency": em_consistency,
            "errors": errors,
            "n_runs": n_runs,
            "n_valid": compliance,
        }

        status = "PASS" if (
            compliance_rate == 1.0
            and ev_consistency >= 0.8
            and em_consistency >= 0.9
        ) else "FAIL"

        print(f"  compliance={compliance_rate:.0%}  "
              f"evidence={ev_consistency:.0%}  "
              f"emotion={em_consistency:.0%}  [{status}]")
        for e in errors[:3]:
            print(f"  ERR: {e}")

    return results


def print_summary(results: dict[str, Any]):
    print("\n" + "=" * 60)
    print("STABILITY VALIDATION SUMMARY")
    print("=" * 60)
    all_pass = True
    for seg_id, r in results.items():
        passed = (
            r["compliance_rate"] == 1.0
            and r["evidence_consistency"] >= 0.8
            and r["emotion_consistency"] >= 0.9
        )
        all_pass = all_pass and passed
        mark = "PASS" if passed else "FAIL"
        print(f"[{mark}] {seg_id}")
        print(f"       compliance={r['compliance_rate']:.0%}  "
              f"evidence={r['evidence_consistency']:.0%}  "
              f"emotion={r['emotion_consistency']:.0%}")

    print()
    if all_pass:
        print("RESULT: PASS — proceed to Phase 1")
    else:
        print("RESULT: FAIL — iterate prompt before Phase 1")
    print("=" * 60)


def save_results(results: dict[str, Any], provider: str, model: str):
    """Save results to D:/LLEE/tasks/ as JSON."""
    import datetime
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = Path(__file__).resolve().parents[2] / "tasks"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"stability-{provider}-{ts}.json"
    record = {
        "timestamp": ts,
        "provider": provider,
        "model": model,
        "segments": {},
    }
    for seg_id, r in results.items():
        record["segments"][seg_id] = {
            "compliance_rate": r["compliance_rate"],
            "evidence_consistency": r["evidence_consistency"],
            "emotion_consistency": r["emotion_consistency"],
            "n_runs": r["n_runs"],
            "n_valid": r["n_valid"],
            "errors": r["errors"],
        }
    total = len(results)
    passed = sum(
        1 for r in results.values()
        if r["compliance_rate"] == 1.0
        and r["evidence_consistency"] >= 0.8
        and r["emotion_consistency"] >= 0.9
    )
    record["summary"] = {"total": total, "passed": passed, "pass_rate": f"{passed}/{total}"}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LLEE Parser Stability Validation")
    parser.add_argument("--provider", default="glm", choices=list(PROVIDERS.keys()),
                        help="API provider")
    parser.add_argument("--runs", type=int, default=1, help="Runs per segment")
    parser.add_argument("--segments", type=int, default=0, help="Max segments (0=all)")
    parser.add_argument("--dry-run", action="store_true", help="No API calls")
    args = parser.parse_args()

    results = run_validation(args.runs, args.provider, args.dry_run, args.segments)
    print_summary(results)
    if not args.dry_run:
        model_name = MODEL_OVERRIDES.get(args.provider) or os.environ.get(
            PROVIDERS[args.provider]["model_env"], args.provider
        )
        save_results(results, args.provider, model_name)
