"""
LLEE World State Schema — Phase 0.3 (rev2)
Core Data Model: W = (E, V, S, O, H, T, N)
Demo implements E + V + S; O/H/T/N are placeholders.

Evidence types (6):
  EXPLICIT     — direct statement of internal state ("I am afraid")
  BEHAVIORAL   — observable action implying state ("he clenched his fist")
  ATMOSPHERIC  — environment implies mood; acts on N.tension only, not E.emotion
  CONTEXTUAL   — weak situational inference; confidence ceiling 0.5
  CHARACTER    — stable personality prior, cross-corpus, never decays
  UNDEFINED    — no evidence
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ─── Evidence System ───────────────────────────────────────────────────────────

class EvidenceLevel(str, Enum):
    EXPLICIT = "explicit"
    BEHAVIORAL = "behavioral"
    ATMOSPHERIC = "atmospheric"   # environment → N.tension only
    CONTEXTUAL = "contextual"
    CHARACTER = "character"       # stable personality prior
    UNDEFINED = "undefined"


# Decay rate per narrative turn for inherited (not re-confirmed) attributes.
# 1.0 = no decay. Applied by WSM after each delta.
EVIDENCE_DECAY_RATE: dict[EvidenceLevel, float] = {
    EvidenceLevel.EXPLICIT:    1.0,   # facts don't fade
    EvidenceLevel.BEHAVIORAL:  1.0,   # past actions are historical facts
    EvidenceLevel.ATMOSPHERIC: 0.7,   # mood dissipates quickly
    EvidenceLevel.CONTEXTUAL:  0.9,   # situational inference weakens
    EvidenceLevel.CHARACTER:   1.0,   # personality is stable
    EvidenceLevel.UNDEFINED:   1.0,
}

# Hard ceiling on confidence per evidence level.
EVIDENCE_CONFIDENCE_CEILING: dict[EvidenceLevel, float] = {
    EvidenceLevel.EXPLICIT:    1.0,
    EvidenceLevel.BEHAVIORAL:  0.85,
    EvidenceLevel.ATMOSPHERIC: 0.30,  # can never be high-confidence
    EvidenceLevel.CONTEXTUAL:  0.50,
    EvidenceLevel.CHARACTER:   0.90,
    EvidenceLevel.UNDEFINED:   0.0,
}

# On narrative break (scene change, time jump): extra multiplier applied once.
NARRATIVE_BREAK_PENALTY: dict[EvidenceLevel, float] = {
    EvidenceLevel.EXPLICIT:    1.0,
    EvidenceLevel.BEHAVIORAL:  1.0,
    EvidenceLevel.ATMOSPHERIC: 0.0,   # reset completely on scene change
    EvidenceLevel.CONTEXTUAL:  0.5,
    EvidenceLevel.CHARACTER:   1.0,
    EvidenceLevel.UNDEFINED:   1.0,
}


class EvidenceSource(str, Enum):
    TEXT = "text"
    CONTEXT = "context"
    PREDICTED = "predicted"
    EXTERNAL = "external"
    CROSS_MODAL = "cross_modal"
    CHARACTER_PRIOR = "character_prior"  # from personality profile


SOURCE_CONFIDENCE_CEILING = {
    EvidenceSource.TEXT: 1.0,
    EvidenceSource.CONTEXT: 0.8,
    EvidenceSource.PREDICTED: 0.4,
    EvidenceSource.EXTERNAL: 0.9,
    EvidenceSource.CROSS_MODAL: 0.7,
}


class Evidence(BaseModel):
    level: EvidenceLevel = EvidenceLevel.UNDEFINED
    source: EvidenceSource = EvidenceSource.TEXT
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    source_span: Optional[tuple[int, int]] = None

    def render_intensity(self) -> float:
        if self.confidence > 0.8:
            return 1.0
        elif self.confidence > 0.5:
            return 0.3 + (self.confidence - 0.5) * 1.0
        elif self.confidence > 0.3:
            return 0.1 + (self.confidence - 0.3) * 1.0
        return 0.0

    @property
    def display_level(self) -> EvidenceLevel:
        """Scheme C: continuous confidence → discrete display level."""
        if self.confidence > 0.8:
            return EvidenceLevel.EXPLICIT
        elif self.confidence > 0.5:
            return EvidenceLevel.BEHAVIORAL
        elif self.confidence > 0.3:
            return EvidenceLevel.CONTEXTUAL
        return EvidenceLevel.UNDEFINED


# ─── E: Entity Group ───────────────────────────────────────────────────────────

class EmotionState(BaseModel):
    value: str = "neutral"
    evidence: Evidence = Field(default_factory=Evidence)


class EntityAction(BaseModel):
    verb: str
    target: Optional[str] = None
    evidence: Evidence = Field(default_factory=Evidence)


class MaterialParams(BaseModel):
    roughness: float = Field(default=0.5, ge=0.0, le=1.0)
    metallic: float = Field(default=0.0, ge=0.0, le=1.0)
    ior: float = Field(default=1.5, ge=1.0, le=3.0)
    subsurface: float = Field(default=0.0, ge=0.0, le=1.0)


class Entity(BaseModel):
    id: str
    label: str
    position: Optional[tuple[float, float, float]] = None
    material_tag: Optional[str] = None
    material_params: Optional[MaterialParams] = None
    emotion: EmotionState = Field(default_factory=EmotionState)
    action: Optional[EntityAction] = None
    state: Optional[str] = None


# ─── V: Visual Field Group ─────────────────────────────────────────────────────

class LightSource(BaseModel):
    id: str
    source_type: str = "ambient"
    color_temperature: float = Field(default=5600.0, ge=1000.0, le=12000.0)
    intensity: float = Field(default=1.0, ge=0.0)
    direction: Optional[tuple[float, float]] = None  # azimuth, elevation
    evidence: Evidence = Field(default_factory=Evidence)


class VisualAtmosphere(BaseModel):
    fog_density: float = Field(default=0.0, ge=0.0, le=1.0)
    fog_color: Optional[tuple[float, float, float]] = None
    color_grade_warmth: float = Field(default=0.0, ge=-1.0, le=1.0)
    contrast: float = Field(default=1.0, ge=0.0, le=2.0)
    saturation: float = Field(default=1.0, ge=0.0, le=2.0)


class VisualField(BaseModel):
    lights: list[LightSource] = Field(default_factory=list)
    atmosphere: VisualAtmosphere = Field(default_factory=VisualAtmosphere)
    scene_type: Optional[str] = None
    scene_type_evidence: Evidence = Field(default_factory=Evidence)


# ─── S: Sonic Field Group ──────────────────────────────────────────────────────

class ReverbPreset(str, Enum):
    NONE = "none"
    ROOM_SMALL = "room_small"
    ROOM_LARGE = "room_large"
    CAVE = "cave"
    OUTDOOR_OPEN = "outdoor_open"
    OUTDOOR_FOREST = "outdoor_forest"


class AmbientSound(BaseModel):
    id: str
    sound_type: str  # "wind", "water", "insects", "fire", "silence"
    intensity: float = Field(default=0.5, ge=0.0, le=1.0)


class SonicField(BaseModel):
    reverb: ReverbPreset = ReverbPreset.NONE
    ambient_sounds: list[AmbientSound] = Field(default_factory=list)
    music_tension: float = Field(default=0.0, ge=0.0, le=1.0)
    overall_volume: float = Field(default=0.7, ge=0.0, le=1.0)


# ─── O/H/T/N: Placeholder Groups ──────────────────────────────────────────────

class OlfactoryField(BaseModel):
    """Placeholder. Scent annotations only, no renderer in Demo."""
    scent_tags: list[str] = Field(default_factory=list)
    intensity: float = Field(default=0.0, ge=0.0, le=1.0)


class HapticField(BaseModel):
    """Placeholder. Tactile annotations only."""
    temperature: Optional[str] = None  # "cold", "cool", "warm", "hot"
    humidity: Optional[str] = None     # "dry", "damp", "wet"
    wind_speed: float = Field(default=0.0, ge=0.0)


class TemporalState(BaseModel):
    """Placeholder. Time tracking."""
    story_time: Optional[str] = None  # narrative time description
    pace: str = "normal"              # "slow", "normal", "fast", "pause"


class NarrativeMeta(BaseModel):
    """Placeholder. Narrative structure annotations."""
    stage: str = "exposition"  # "exposition", "rising", "climax", "falling", "resolution"
    tension: float = Field(default=0.3, ge=0.0, le=1.0)
    focus_entity: Optional[str] = None


# ─── World State ───────────────────────────────────────────────────────────────

class WorldState(BaseModel):
    """Complete world state W = (E, V, S, O, H, T, N)"""
    entities: dict[str, Entity] = Field(default_factory=dict)
    visual: VisualField = Field(default_factory=VisualField)
    sonic: SonicField = Field(default_factory=SonicField)
    olfactory: OlfactoryField = Field(default_factory=OlfactoryField)
    haptic: HapticField = Field(default_factory=HapticField)
    temporal: TemporalState = Field(default_factory=TemporalState)
    narrative: NarrativeMeta = Field(default_factory=NarrativeMeta)


# ─── Delta Format ──────────────────────────────────────────────────────────────

class EntityDelta(BaseModel):
    """Partial update to an entity. None fields = no change."""
    id: str
    position: Optional[tuple[float, float, float]] = None
    material_tag: Optional[str] = None
    material_params: Optional[MaterialParams] = None
    emotion: Optional[EmotionState] = None
    action: Optional[EntityAction] = None
    state: Optional[str] = None


class VisualDelta(BaseModel):
    lights: Optional[list[LightSource]] = None
    atmosphere: Optional[VisualAtmosphere] = None
    scene_type: Optional[str] = None
    scene_type_evidence: Optional[Evidence] = None


class SonicDelta(BaseModel):
    reverb: Optional[ReverbPreset] = None
    ambient_sounds: Optional[list[AmbientSound]] = None
    music_tension: Optional[float] = None


class WorldStateDelta(BaseModel):
    """LLEE Delta — only changed fields are present."""
    entity_updates: list[EntityDelta] = Field(default_factory=list)
    entity_removals: list[str] = Field(default_factory=list)
    visual: Optional[VisualDelta] = None
    sonic: Optional[SonicDelta] = None
    olfactory: Optional[OlfactoryField] = None
    haptic: Optional[HapticField] = None
    temporal: Optional[TemporalState] = None
    narrative: Optional[NarrativeMeta] = None
