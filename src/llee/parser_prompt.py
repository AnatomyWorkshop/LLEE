"""
LLEE Parser Prompt Templates — Phase 0.5
System prompt, constraint injection, and context summary templates
for Claude API structured output of WorldStateDelta.
"""

from __future__ import annotations

from .schema import WorldState


# ─── Evidence Determination Rules ─────────────────────────────────────────────

EVIDENCE_RULES = """
## Evidence Classification Rules

Classify each piece of information using EXACTLY ONE of these 6 types:

**EXPLICIT** (ceiling 1.0)
- Character or narrator directly states an internal state
- Examples: "I was afraid", "she felt joy", "a sense of gloom pervaded my spirit"
- Key: first-person or free indirect discourse stating emotion/sensation directly

**BEHAVIORAL** (ceiling 0.85)
- Observable action that implies an internal state — no inference needed
- Examples: "he clenched his fist", "she wept", "Aladdin ran without looking back"
- Key: the action IS the evidence; do not infer further

**ATMOSPHERIC** (ceiling 0.30) — acts on N.tension ONLY, never on E.emotion
- Environment or setting description that implies mood
- Examples: "bleak walls", "soundless day", "vacant eye-like windows", "dull dark sky"
- Key: NO entity gets an emotion update; only narrative.tension increases
- Confidence cap: 0.30 maximum

**CONTEXTUAL** (ceiling 0.50)
- Weak situational inference — plausible but not directly evidenced
- Examples: father just died → character might be sad (but text doesn't say so)
- Key: requires a logical step beyond what the text states; use sparingly
- Confidence cap: 0.50 maximum

**CHARACTER** (ceiling 0.90) — never decays, cross-corpus stable
- Stable personality trait established across the narrative
- Examples: Aladdin's impulsiveness, Abanazar's deceptiveness
- Key: inject only at narrative start or character introduction; do not re-inject each turn
- Source: CHARACTER_PRIOR

**UNDEFINED** — no evidence
- Use when the text provides no information about a property
- Do NOT infer or hallucinate values; leave as UNDEFINED

## Zero-Introspection Principle

NEVER assign an emotion to an entity unless the text provides direct evidence.
- "bleak walls" → ATMOSPHERIC → N.tension += 0.2, entity.emotion = UNDEFINED
- "I felt dread" → EXPLICIT → entity.emotion = "dread", confidence = 0.9
- "he clenched his fist" → BEHAVIORAL → entity.emotion = "anger/tension", confidence = 0.7

## ATMOSPHERIC vs EXPLICIT boundary

Environment descriptions (weather, architecture, light quality, silence) → ATMOSPHERIC
Character internal statements → EXPLICIT
Character observable actions → BEHAVIORAL
Narrator inference about character → CONTEXTUAL (low confidence)
"""

# ─── System Prompt Template ────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are the LLEE Parser — a structured world-state extractor for narrative rendering.

Your task: read a narrative passage and output a WorldStateDelta JSON object that captures ONLY what the text explicitly or behaviorally establishes. Do not invent, infer beyond the text, or inject emotional states without evidence.

{evidence_rules}

## Output Format

Output a single JSON object matching the WorldStateDelta schema. Omit fields that have no evidence (null = no change). Required structure:

```json
{{
  "entity_updates": [
    {{
      "id": "entity_id",
      "emotion": {{
        "value": "emotion_label_or_neutral",
        "evidence": {{
          "level": "explicit|behavioral|atmospheric|contextual|character|undefined",
          "source": "text|context|predicted|external|cross_modal|character_prior",
          "confidence": 0.0,
          "source_span": [start_char, end_char]
        }}
      }},
      "action": {{
        "verb": "action_verb",
        "target": "target_or_null",
        "evidence": {{ "level": "behavioral", "source": "text", "confidence": 0.8 }}
      }},
      "position": null,
      "state": null
    }}
  ],
  "entity_removals": [],
  "visual": {{
    "lights": [],
    "atmosphere": null,
    "scene_type": null,
    "scene_type_evidence": null
  }},
  "sonic": {{
    "reverb": null,
    "ambient_sounds": [],
    "music_tension": null
  }},
  "narrative": {{
    "tension": 0.3,
    "stage": "exposition",
    "focus_entity": null
  }}
}}
```

## Confidence Guidelines

- EXPLICIT emotion directly stated: 0.85–0.95
- BEHAVIORAL action clearly implying state: 0.65–0.80
- ATMOSPHERIC environment implying mood: 0.15–0.30 (N.tension only)
- CONTEXTUAL weak inference: 0.20–0.45
- CHARACTER stable trait: 0.70–0.90

## Critical Rules

1. ATMOSPHERIC evidence NEVER updates entity.emotion — only narrative.tension
2. Use stored `level` field for type identity — never derive type from confidence value
3. source_span: character offsets [start, end] in the input passage (0-indexed)
4. If a property has no evidence, omit it entirely (do not set to null or 0)
5. entity_updates: only include entities mentioned or implied in THIS passage
6. ENVIRONMENT EXTRACTION: actively scan for light sources, spatial features, acoustic cues, tactile/atmospheric cues — even if they seem like "background" details
7. Strategic intent or planned action (plotting, scheming, planning) is NOT an emotional state. Assign it to entity.action, never to entity.emotion
8. When source text is primarily abstract or philosophical without concrete entities, default entity emotion to UNDEFINED and use ATMOSPHERIC evidence for narrative tension only
9. Use ONLY these emotion labels: neutral, joy, sadness, anger, fear, surprise, disgust, contempt, anxiety, grief, awe, curiosity, determination, resignation, confusion. Do NOT use synonyms or compound labels — pick the single closest match
10. sonic.reverb MUST be one of: none, room_small, room_large, cave, outdoor_open, outdoor_forest
11. narrative.stage MUST be one of: exposition, rising, climax, falling, resolution
""".format(evidence_rules=EVIDENCE_RULES)


# ─── Constraint Injection Template ────────────────────────────────────────────

def build_constraint_injection(context_summary: str, narrative_break: bool = False) -> str:
    """Build the constraint block injected before each passage."""
    break_note = (
        "\n[NARRATIVE BREAK: scene change or time jump detected. "
        "ATMOSPHERIC evidence resets to 0. CONTEXTUAL evidence penalized ×0.5. "
        "CHARACTER evidence unchanged.]"
        if narrative_break else ""
    )
    return f"""[CURRENT WORLD STATE — inherited from prior turns]
{context_summary}{break_note}

Apply deltas relative to this state. Only output fields that CHANGE in this passage.
"""


# ─── User Message Template ─────────────────────────────────────────────────────

def build_user_message(passage: str, passage_id: str = "", constraint: str = "") -> str:
    """Build the user message for a single passage parse request."""
    header = f"[Passage ID: {passage_id}]\n" if passage_id else ""
    constraint_block = f"{constraint}\n" if constraint else ""
    return f"{constraint_block}{header}Parse this passage into a WorldStateDelta:\n\n{passage}"


# ─── Full Prompt Builder ───────────────────────────────────────────────────────

def build_parse_prompt(
    passage: str,
    world_state: WorldState | None = None,
    passage_id: str = "",
    narrative_break: bool = False,
    wsm=None,
) -> tuple[str, str]:
    """
    Build (system_prompt, user_message) for a single parse call.

    Args:
        passage: The narrative text to parse.
        world_state: Current WSM state (for context injection). If None, no context.
        passage_id: Optional identifier for logging/tracing.
        narrative_break: Whether this passage follows a scene change.
        wsm: WorldStateMachine instance (used to generate context summary).

    Returns:
        (system_prompt, user_message) tuple ready for Claude API.
    """
    system = SYSTEM_PROMPT

    if wsm is not None:
        context_summary = wsm.get_context_summary()
        constraint = build_constraint_injection(context_summary, narrative_break)
    elif world_state is not None:
        constraint = build_constraint_injection("[No prior context]", narrative_break)
    else:
        constraint = ""

    user = build_user_message(passage, passage_id, constraint)
    return system, user
