"""Smoke tests: schema + WSM + parser prompt."""

from llee.schema import (
    WorldStateDelta,
    EntityDelta,
    EmotionState,
    Evidence,
    EvidenceLevel,
    EvidenceSource,
    VisualDelta,
    LightSource,
    SonicDelta,
    ReverbPreset,
    AmbientSound,
    NarrativeMeta,
)
from llee.wsm import WorldStateMachine


def test_basic_delta_application():
    wsm = WorldStateMachine()

    delta = WorldStateDelta(
        entity_updates=[
            EntityDelta(
                id="aladdin",
                position=(0.0, 0.0, -5.0),
                emotion=EmotionState(
                    value="neutral",
                    evidence=Evidence(
                        level=EvidenceLevel.UNDEFINED,
                        source=EvidenceSource.TEXT,
                        confidence=0.0,
                    ),
                ),
            ),
            EntityDelta(id="mustafa", state="DECEASED"),
        ],
        visual=VisualDelta(
            scene_type="cave_interior",
            lights=[
                LightSource(
                    id="lamp",
                    source_type="artificial",
                    color_temperature=4000.0,
                    intensity=0.15,
                    direction=(127.0, 34.0),
                    evidence=Evidence(
                        level=EvidenceLevel.EXPLICIT,
                        source=EvidenceSource.TEXT,
                        confidence=0.95,
                        source_span=(45, 78),
                    ),
                )
            ],
        ),
        sonic=SonicDelta(
            reverb=ReverbPreset.CAVE,
            ambient_sounds=[AmbientSound(id="drip", sound_type="water", intensity=0.3)],
        ),
    )

    state = wsm.apply_delta(delta)

    assert "aladdin" in state.entities
    assert state.entities["aladdin"].emotion.value == "neutral"
    assert state.entities["aladdin"].emotion.evidence.display_level == EvidenceLevel.UNDEFINED
    assert state.entities["mustafa"].state == "DECEASED"
    assert state.visual.scene_type == "cave_interior"
    assert state.sonic.reverb == ReverbPreset.CAVE
    assert len(state.sonic.ambient_sounds) == 1


def test_context_summary():
    wsm = WorldStateMachine()
    delta = WorldStateDelta(
        entity_updates=[
            EntityDelta(
                id="aladdin",
                position=(0.0, 0.0, -5.0),
                emotion=EmotionState(
                    value="neutral",
                    evidence=Evidence(level=EvidenceLevel.UNDEFINED, confidence=0.0),
                ),
            )
        ],
        visual=VisualDelta(scene_type="cave_interior"),
        sonic=SonicDelta(reverb=ReverbPreset.CAVE),
    )
    wsm.apply_delta(delta)
    summary = wsm.get_context_summary()
    assert "aladdin" in summary
    assert "cave_interior" in summary
    assert "WORLD STATE CONSTRAINT" in summary


def test_evidence_render_intensity():
    assert Evidence(confidence=0.95).render_intensity() == 1.0
    assert 0.3 < Evidence(confidence=0.65).render_intensity() < 0.8
    assert Evidence(confidence=0.1).render_intensity() == 0.0


def test_context_decay():
    wsm = WorldStateMachine()
    delta = WorldStateDelta(
        entity_updates=[
            EntityDelta(
                id="aladdin",
                emotion=EmotionState(
                    value="curious",
                    evidence=Evidence(
                        level=EvidenceLevel.CONTEXTUAL,
                        source=EvidenceSource.CONTEXT,
                        confidence=0.7,
                    ),
                ),
            )
        ]
    )
    wsm.apply_delta(delta)
    c1 = wsm.state.entities["aladdin"].emotion.evidence.confidence

    wsm.apply_delta(WorldStateDelta())
    c2 = wsm.state.entities["aladdin"].emotion.evidence.confidence

    assert c2 < c1
    assert abs(c2 - c1 * 0.9) < 0.001


def test_parser_prompt_builder():
    from llee.parser_prompt import build_parse_prompt

    wsm = WorldStateMachine()
    passage = "Aladdin ran into the cave, his heart pounding."
    system, user = build_parse_prompt(passage, passage_id="test_01", wsm=wsm)

    assert "LLEE Parser" in system
    assert "ATMOSPHERIC" in system
    assert "Zero-Introspection" in system
    assert "test_01" in user
    assert "Aladdin ran" in user
    assert "WORLD STATE CONSTRAINT" in user


def test_narrative_break_decay():
    """ATMOSPHERIC (narrative.tension) resets to 0 on break; CHARACTER does not decay."""
    wsm = WorldStateMachine()

    delta = WorldStateDelta(
        entity_updates=[
            EntityDelta(
                id="narrator",
                emotion=EmotionState(
                    value="dread",
                    evidence=Evidence(
                        level=EvidenceLevel.CHARACTER,
                        source=EvidenceSource.CHARACTER_PRIOR,
                        confidence=0.85,
                    ),
                ),
            )
        ],
        narrative=NarrativeMeta(tension=0.8, stage="rising"),
    )
    wsm.apply_delta(delta)

    char_conf_before = wsm.state.entities["narrator"].emotion.evidence.confidence
    wsm.apply_delta(WorldStateDelta(), narrative_break=True)
    char_conf_after = wsm.state.entities["narrator"].emotion.evidence.confidence

    assert char_conf_after == char_conf_before          # CHARACTER never decays
    assert wsm.state.narrative.tension == 0.0           # ATMOSPHERIC resets


def test_confidence_ceiling_clamp():
    """WSM clamps confidence to EVIDENCE_CONFIDENCE_CEILING on apply."""
    from llee.schema import EVIDENCE_CONFIDENCE_CEILING

    wsm = WorldStateMachine()

    # ATMOSPHERIC ceiling is 0.30 — feed in 0.9, should be clamped
    delta = WorldStateDelta(
        entity_updates=[
            EntityDelta(
                id="env_mood",
                emotion=EmotionState(
                    value="gloomy",
                    evidence=Evidence(
                        level=EvidenceLevel.ATMOSPHERIC,
                        source=EvidenceSource.TEXT,
                        confidence=0.9,
                    ),
                ),
            )
        ]
    )
    wsm.apply_delta(delta)
    clamped = wsm.state.entities["env_mood"].emotion.evidence.confidence
    # Clamped to 0.30, then ATMOSPHERIC decay ×0.7 → 0.21
    assert clamped <= EVIDENCE_CONFIDENCE_CEILING[EvidenceLevel.ATMOSPHERIC]
    assert abs(clamped - 0.30 * 0.7) < 0.001

    # CONTEXTUAL ceiling is 0.50 — feed in 0.8, should be clamped
    delta2 = WorldStateDelta(
        entity_updates=[
            EntityDelta(
                id="inferred",
                emotion=EmotionState(
                    value="sad",
                    evidence=Evidence(
                        level=EvidenceLevel.CONTEXTUAL,
                        source=EvidenceSource.CONTEXT,
                        confidence=0.8,
                    ),
                ),
            )
        ]
    )
    wsm.apply_delta(delta2)
    clamped2 = wsm.state.entities["inferred"].emotion.evidence.confidence
    # Clamped to 0.50, then CONTEXTUAL decay ×0.9 → 0.45
    assert clamped2 <= EVIDENCE_CONFIDENCE_CEILING[EvidenceLevel.CONTEXTUAL]
    assert abs(clamped2 - 0.50 * 0.9) < 0.001

    # EXPLICIT ceiling is 1.0 — 0.95 should pass through
    delta3 = WorldStateDelta(
        entity_updates=[
            EntityDelta(
                id="speaker",
                emotion=EmotionState(
                    value="afraid",
                    evidence=Evidence(
                        level=EvidenceLevel.EXPLICIT,
                        source=EvidenceSource.TEXT,
                        confidence=0.95,
                    ),
                ),
            )
        ]
    )
    wsm.apply_delta(delta3)
    assert wsm.state.entities["speaker"].emotion.evidence.confidence == 0.95


if __name__ == "__main__":
    test_basic_delta_application()
    test_context_summary()
    test_evidence_render_intensity()
    test_context_decay()
    test_parser_prompt_builder()
    test_narrative_break_decay()
    test_confidence_ceiling_clamp()
    print("All tests passed.")
