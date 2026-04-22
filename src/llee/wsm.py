"""
LLEE World State Machine — Phase 1.1 (rev2)
Maintains current state, applies deltas, computes context summaries.

Decay rules (per EVIDENCE_DECAY_RATE in schema.py):
  EXPLICIT / BEHAVIORAL / CHARACTER: no decay (historical facts / stable traits)
  ATMOSPHERIC: × 0.7 per turn (mood dissipates quickly)
  CONTEXTUAL:  × 0.9 per turn (situational inference weakens)
  On narrative_break=True: ATMOSPHERIC resets to 0, CONTEXTUAL × 0.5 extra
"""

from __future__ import annotations

from copy import deepcopy
from collections import deque

from .schema import (
    WorldState,
    WorldStateDelta,
    Entity,
    Evidence,
    EvidenceLevel,
    EVIDENCE_DECAY_RATE,
    EVIDENCE_CONFIDENCE_CEILING,
    NARRATIVE_BREAK_PENALTY,
)


class WorldStateMachine:
    def __init__(self, context_buffer_size: int = 5):
        self.state = WorldState()
        self._history: deque[WorldStateDelta] = deque(maxlen=context_buffer_size)
        self._turn_count = 0

    def apply_delta(self, delta: WorldStateDelta, narrative_break: bool = False) -> WorldState:
        """Apply a delta to current state, return new state.

        Args:
            delta: The world state changes for this narrative turn.
            narrative_break: True on scene change or time jump — triggers
                             extra penalty on ATMOSPHERIC/CONTEXTUAL evidence.
        """
        for eu in delta.entity_updates:
            if eu.id not in self.state.entities:
                self.state.entities[eu.id] = Entity(id=eu.id, label=eu.id)
            entity = self.state.entities[eu.id]
            if eu.position is not None:
                entity.position = eu.position
            if eu.material_tag is not None:
                entity.material_tag = eu.material_tag
            if eu.material_params is not None:
                entity.material_params = eu.material_params
            if eu.emotion is not None:
                entity.emotion = eu.emotion
            if eu.action is not None:
                entity.action = eu.action
            if eu.state is not None:
                entity.state = eu.state

        for eid in delta.entity_removals:
            self.state.entities.pop(eid, None)

        if delta.visual:
            if delta.visual.lights is not None:
                self.state.visual.lights = delta.visual.lights
            if delta.visual.atmosphere is not None:
                self.state.visual.atmosphere = delta.visual.atmosphere
            if delta.visual.scene_type is not None:
                self.state.visual.scene_type = delta.visual.scene_type
            if delta.visual.scene_type_evidence is not None:
                self.state.visual.scene_type_evidence = delta.visual.scene_type_evidence

        if delta.sonic:
            if delta.sonic.reverb is not None:
                self.state.sonic.reverb = delta.sonic.reverb
            if delta.sonic.ambient_sounds is not None:
                self.state.sonic.ambient_sounds = delta.sonic.ambient_sounds
            if delta.sonic.music_tension is not None:
                self.state.sonic.music_tension = delta.sonic.music_tension

        if delta.olfactory:
            self.state.olfactory = delta.olfactory
        if delta.haptic:
            self.state.haptic = delta.haptic
        if delta.temporal:
            self.state.temporal = delta.temporal
        if delta.narrative:
            self.state.narrative = delta.narrative

        self._history.append(delta)
        self._turn_count += 1
        self._clamp_evidence()
        self._decay_evidence(narrative_break=narrative_break)
        return self.state

    def _clamp_evidence(self):
        """Enforce confidence ceilings per evidence level."""
        for entity in self.state.entities.values():
            ev = entity.emotion.evidence
            ceiling = EVIDENCE_CONFIDENCE_CEILING.get(ev.level, 1.0)
            if ev.confidence > ceiling:
                ev.confidence = ceiling

    def _decay_evidence(self, narrative_break: bool = False):
        """Decay confidence of inherited evidence according to type-specific rates."""
        for entity in self.state.entities.values():
            ev = entity.emotion.evidence
            # Use stored level (not display_level) for decay — display_level is
            # only a human-readable approximation of the continuous confidence.
            level = ev.level
            rate = EVIDENCE_DECAY_RATE.get(level, 1.0)
            if narrative_break:
                rate *= NARRATIVE_BREAK_PENALTY.get(level, 1.0)
            ev.confidence = max(0.0, ev.confidence * rate)

        if narrative_break:
            self.state.narrative.tension = max(
                0.0,
                self.state.narrative.tension
                * NARRATIVE_BREAK_PENALTY[EvidenceLevel.ATMOSPHERIC],
            )

    def get_context_summary(self) -> str:
        """Generate a concise summary of current state for prompt injection."""
        lines = ["[WORLD STATE CONSTRAINT]"]

        if self.state.entities:
            lines.append("Entities:")
            for eid, e in self.state.entities.items():
                parts = [f"  - {e.label}"]
                if e.position:
                    parts.append(f"pos={e.position}")
                if e.state:
                    parts.append(f"state={e.state}")
                em = e.emotion
                parts.append(f"emotion=({em.value}, {em.evidence.display_level.value})")
                lines.append(", ".join(parts))

        v = self.state.visual
        if v.scene_type:
            lines.append(f"Scene: type={v.scene_type}")
        for lt in v.lights:
            lines.append(
                f"  Light[{lt.id}]: {lt.source_type}, "
                f"temp={lt.color_temperature}K, intensity={lt.intensity}"
            )

        s = self.state.sonic
        if s.reverb.value != "none":
            lines.append(f"Audio: reverb={s.reverb.value}")
        if s.ambient_sounds:
            sounds = ", ".join(a.sound_type for a in s.ambient_sounds)
            lines.append(f"  Ambient: {sounds}")

        n = self.state.narrative
        if n.tension > 0.1:
            lines.append(f"Narrative: tension={n.tension:.2f}, stage={n.stage}")

        return "\n".join(lines)

    def get_state_snapshot(self) -> WorldState:
        return deepcopy(self.state)

    def reset(self):
        self.state = WorldState()
        self._history.clear()
        self._turn_count = 0
