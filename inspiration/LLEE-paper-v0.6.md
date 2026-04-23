# LLEE: An Evidence-Graded Intermediate Representation for Faithful Narrative Rendering

**Version 0.6 — April 2026**

---

## Abstract

Large Language Models (LLMs) can generate rich narrative descriptions, but converting these descriptions into deterministic rendering parameters introduces a critical failure mode: *Intentional Emotional Injection* (IEI), where the generation pipeline injects emotional states, atmospheric qualities, or character dispositions that lack textual evidence. We present LLEE (Latent Language Expansion Engine), a declarative intermediate representation that establishes a *trust boundary* between LLM-generated narrative interpretation and deterministic rendering execution. LLEE introduces three key innovations: (1) a six-type evidence-grading framework with type-specific decay rates and confidence ceilings, distinguishing between explicit statements, observable behaviors, environmental atmosphere, contextual inference, stable character traits, and undefined states; (2) the Zero-Introspection Principle, formally encoded so that atmospheric evidence acts on narrative tension only, never on entity emotion; and (3) a text-centric ontological framework where confidence measures textual evidence strength rather than physical plausibility, granting fictional and real worlds equal status within the rendering pipeline. We provide a complete open-source implementation (Schema, World State Machine, Parser prompt templates, and stability test framework) and describe a multi-phase experimental design spanning prompt stability validation, parser fidelity measurement, automated rendering evaluation, and human cognitive correlation studies. Our corpus covers six writing styles including AI-generated text, enabling direct comparison of parser behavior on human-authored versus machine-generated narratives. [PLACEHOLDER: Key quantitative findings from Phase 1-3 experiments.]

---

## 1. Introduction

The convergence of large language models and real-time rendering engines has created a new class of application: AI-driven narrative visualization, where textual descriptions are automatically converted into visual, auditory, and haptic rendering parameters. Systems such as NVIDIA's ChatUSD (GTC 2025) demonstrate the commercial appetite for this capability. However, current approaches face a fundamental problem that we term *Intentional Emotional Injection* (IEI): the tendency of LLM-based pipelines to inject emotional states, atmospheric qualities, and character dispositions that are not supported by the source text.

Consider a passage from Aladdin: "Next day the magician led Aladdin into some beautiful gardens a long way outside the city gates." A faithful rendering should depict two figures walking through gardens. An IEI-contaminated rendering might add ominous lighting, tense music, and a fearful expression on Aladdin's face—none of which are evidenced by the text. The magician's malicious intent is known to the reader from prior context, but the *text of this passage* does not describe fear, tension, or foreboding. A rendering system that adds these elements is not being faithful to the text; it is hallucinating emotional content.

IEI is not a minor aesthetic concern. In applications ranging from interactive fiction to educational visualization to accessibility tools for visually impaired readers, the distinction between "what the text says" and "what the AI thinks the text implies" is a matter of trust. If users cannot predict or audit the mapping from text to rendering, the system becomes a black box whose emotional editorializing may distort the source material.

### The Trust Boundary

LLEE addresses IEI by establishing a *trust boundary*: a formally defined interface where LLM uncertainty is isolated, quantified, and constrained before reaching the deterministic rendering pipeline. On one side of the boundary, the LLM Parser operates probabilistically, extracting world-state information from narrative text. On the other side, the World State Machine (WSM) and rendering adapters operate deterministically—given the same LLEE Delta, they always produce the same rendering parameters.

The trust boundary is enforced through three mechanisms:

1. **Evidence grading**: Every piece of extracted information carries a typed evidence label (one of six levels) and a continuous confidence score, making the Parser's certainty explicit and auditable.
2. **Confidence ceilings**: Each evidence type has a hard maximum confidence, preventing the system from expressing more certainty than the evidence warrants (e.g., atmospheric inference is capped at 0.30).
3. **Type-specific decay**: Inherited state decays at rates determined by evidence type, ensuring that weakly-evidenced states fade naturally rather than persisting indefinitely.

### Research Questions

This paper investigates five research questions:

- **RQ1**: Can a structured evidence-grading system (6 types with type-specific decay) suppress IEI while preserving legitimate emotional content in narrative rendering?
- **RQ2**: Does LLEE's differential world-state encoding achieve higher text-to-rendering fidelity than unconstrained LLM output, across both sparse and rich narrative styles?
- **RQ3**: How does LLM attention bias toward character/emotion (vs. environment/physics) affect world-state completeness, and can explicit extraction rules compensate?
- **RQ4**: Does the Parser exhibit different evidence-grading consistency when processing AI-generated vs. human-authored narrative text?
- **RQ5**: Do LLEE's type-specific decay rates correlate with human readers' cognitive state trajectories during narrative comprehension?

### Contributions

We make the following contributions:

- **C1**: A six-type evidence-grading framework (EXPLICIT, BEHAVIORAL, ATMOSPHERIC, CONTEXTUAL, CHARACTER, UNDEFINED) with type-specific decay rates and confidence ceilings, grounded in the distinction between foreground affect and background affect from emotion computation research.
- **C2**: The Zero-Introspection Principle and its formal encoding as a trust boundary—ATMOSPHERIC evidence acts on narrative tension (N.tension) only, never on entity emotion (E.emotion), preventing environmental descriptions from contaminating character emotional states.
- **C3**: A text-centric ontological framework where confidence measures textual evidence strength rather than physical plausibility, granting fictional and real worlds equal ontological status within the rendering pipeline.
- **C4**: A complete open-source implementation (Schema, WSM, Parser prompt, stability test) with a rigorous multi-phase experimental design including AI-vs-human corpus comparison across six narrative styles.

---

## 2. Related Work

### 2.1 LLM-to-Rendering Pipelines

**ChatUSD** (NVIDIA, GTC 2025) enables conversational scene editing through natural language, generating USD (Universal Scene Description) commands from dialogue. ChatUSD is designed for human-in-the-loop workflows where an artist iteratively refines a scene. It does not maintain cross-turn state consistency, does not grade evidence, and does not address IEI—the artist serves as the quality gate. LLEE is complementary: it targets automated, pipeline-mode rendering where no human is in the loop, and state consistency across narrative segments is essential.

**FactTrack** (Min et al., 2023) maintains factual consistency in long-form LLM generation by tracking entity states across turns. FactTrack addresses factual drift but does not distinguish between evidence types, does not model emotional states, and does not interface with rendering systems. LLEE extends the state-tracking paradigm with evidence grading and rendering-specific output.

**CRANE** (Lee et al., 2024) uses constrained decoding to enforce structural requirements on LLM output. CRANE operates at the token level, ensuring syntactic compliance. LLEE operates at the semantic level, ensuring that the *content* of the output is grounded in textual evidence. The two approaches are orthogonal and could be combined.

### 2.2 Universal Scene Description and Omniverse

USD (Pixar, 2016) is the industry standard for scene interchange. NVIDIA Omniverse extends USD with real-time collaboration, physics simulation (PhysicsUSD), and AI integration (Audio2Face, AI Foundation Models). LLEE is positioned as an *AI frontend* to USD/Omniverse—it translates narrative text into structured world-state deltas that can drive USD stage updates. LLEE does not replace USD; it provides the semantic layer that USD lacks. Where USD describes *what exists* in a scene, LLEE describes *why it exists* (the textual evidence) and *how certain we are* (the confidence score).

### 2.3 Emotion Computation and Affective Computing

The distinction between foreground affect (specific to an agent) and background affect (ambient environmental mood) is well-established in emotion computation (Russell, 2003; Scherer, 2005). LLEE's ATMOSPHERIC evidence type operationalizes this distinction: background affect influences global rendering parameters (music tension, color grading) but never entity-level emotional states. This is, to our knowledge, the first system to encode the foreground/background affect distinction directly into a rendering pipeline's evidence model.

### 2.4 World Models

LeCun's Joint Embedding Predictive Architecture (JEPA, 2022) learns world models through self-supervised prediction in latent space. JEPA captures dynamics—how the world changes over time—but its predictions are continuous vectors, not structured symbols consumable by rendering engines. LLEE and JEPA address complementary aspects of world modeling: JEPA predicts *what will happen next* (dynamics), while LLEE describes *what is happening now* (state). A future integration could use JEPA predictions as PREDICTED-level evidence within LLEE's framework (confidence ceiling 0.4).

---

## 3. Design Principles

### 3.1 The Zero-Introspection Principle

LLEE's foundational design principle is: **no emotional state shall be assigned to any entity unless the source text provides direct evidence.** This principle has three operational consequences:

1. If the text does not describe a character's emotion, the emotion field remains UNDEFINED—not "neutral," not "calm," but explicitly unknown.
2. Environmental descriptions ("bleak walls," "soundless day") influence narrative tension (N.tension) but never entity emotion (E.emotion). This is the ATMOSPHERIC evidence constraint.
3. Contextual inference ("his father just died, so he is probably sad") is permitted but capped at confidence 0.50, ensuring it never dominates the rendering.

The Zero-Introspection Principle is not a claim about what characters *feel*—it is a claim about what the *text establishes*. A character may well be terrified, but if the text does not say so, LLEE does not render terror. This is a deliberate trade-off: we sacrifice speculative richness for auditable fidelity.

### 3.2 Text-Centric Ontology

LLEE's confidence scores measure *textual evidence strength*, not *physical plausibility*. When a narrative states "an enormous genie rose out of the earth," this receives EXPLICIT evidence (confidence 0.9) regardless of the physical impossibility of genies. Conversely, "the cave was probably cold" receives CONTEXTUAL evidence (confidence ≤ 0.50) even though caves are physically cold—because the text did not explicitly state the temperature.

This design choice has a profound consequence: **fictional and real worlds enjoy equal ontological status within LLEE.** A genie's EXPLICIT evidence is identical in type and confidence to a chair's EXPLICIT evidence. The rendering pipeline treats both with equal fidelity. This is not a philosophical position about the nature of reality; it is an engineering decision that ensures LLEE works correctly for fantasy, science fiction, magical realism, and any other genre where physical plausibility is irrelevant to narrative truth.

### 3.3 The Fact-Statement Principle

LLEE models *what the text states*, not *what characters believe*. If the text says "the magician was a fraud," this is a world fact in LLEE's state, regardless of whether Aladdin knows it. Character beliefs, unreliable narration, and perspectival differences are not modeled in the current architecture (v0.6). The rendering of perspective (e.g., showing the magician as trustworthy from Aladdin's point of view) is delegated to the renderer's presentation layer, not LLEE's state layer. This separation ensures that LLEE's world state remains a single, consistent, auditable record of textual facts.

## 4. Architecture

### 4.1 World State Model

LLEE represents the narrative world as a seven-group state vector:

**W = (E, V, S, O, H, T, N)**

where E = Entities, V = Visual Field, S = Sonic Field, O = Olfactory Field, H = Haptic Field, T = Temporal State, and N = Narrative Meta. The current implementation (Phase 0) fully implements E, V, and S; O, H, T, and N are defined as placeholder schemas.

**[Fig 1: LLEE Pipeline Architecture]**
```
Narrative Text → [LLM Parser] → WorldStateDelta (JSON)
                                      ↓
                              [World State Machine]
                              ↓ clamp → decay → break
                              WorldState (current)
                                      ↓
                    ┌─────────────────┼─────────────────┐
              [Visual Adapter]  [Audio Adapter]  [Context Summary]
              Three.js / USD    Tone.js / FMOD   → next Parser call
```

Each group contains typed fields with evidence annotations. For example, the Entity group includes position, material parameters, emotional state, current action, and a general state tag—each backed by an Evidence record specifying the evidence level, source, confidence, and source text span.

### 4.2 Delta Format

LLEE uses differential encoding: each narrative segment produces a WorldStateDelta containing only the fields that change. Unchanged fields are omitted (null), not repeated. This design has three advantages:

1. **Bandwidth efficiency**: A passage that only changes lighting does not re-transmit entity positions.
2. **Auditability**: The delta explicitly shows what changed and why (via evidence annotations).
3. **Composability**: Deltas can be applied sequentially to reconstruct any historical state.

### 4.3 World State Machine

The WSM maintains the current world state and applies deltas through a three-phase update cycle:

1. **Apply**: Merge delta fields into current state (entity updates, visual/sonic changes, narrative metadata).
2. **Clamp**: Enforce confidence ceilings per evidence type (§5.3).
3. **Decay**: Reduce confidence of inherited (non-reconfirmed) evidence according to type-specific rates (§5.4). On narrative breaks (scene changes, time jumps), apply additional penalties.

The WSM also maintains a sliding context buffer (default: 5 most recent deltas) used to generate a text summary injected into the next Parser call, providing the LLM with awareness of accumulated world state.

## 5. Evidence System

The evidence system is LLEE's core theoretical contribution. It addresses a fundamental question: *how certain should the rendering be about each piece of world state?*

### 5.1 Evidence Types

LLEE defines six evidence types, ordered by decreasing confidence:

**[Table 1: Evidence Types]**

| Type | Definition | Decay Rate | Confidence Ceiling | Example |
|------|-----------|------------|-------------------|---------|
| EXPLICIT | Direct statement of internal state or world fact | 1.0 (none) | 1.00 | "I was afraid"; "the lamp glowed blue" |
| BEHAVIORAL | Observable action implying state | 1.0 (none) | 0.85 | "he clenched his fist"; "she wept" |
| ATMOSPHERIC | Environment description implying mood; acts on N.tension only, **never** on E.emotion | 0.7 per turn | 0.30 | "bleak walls"; "soundless day" |
| CONTEXTUAL | Weak situational inference | 0.9 per turn | 0.50 | Father died → character might be sad |
| CHARACTER | Stable personality prior; cross-corpus, never decays | 1.0 (none) | 0.90 | Aladdin's impulsiveness |
| UNDEFINED | No evidence | 1.0 | 0.00 | Text provides no information |

The ATMOSPHERIC type deserves special attention. It resolves a tension inherent in the Zero-Introspection Principle: Poe writes "dull, dark, and soundless day"—this is environmental description, not character emotion. Strictly applied, Zero-Introspection would ignore it entirely. But ignoring it would strip Poe's prose of its core atmospheric quality. ATMOSPHERIC evidence resolves this by channeling environmental mood into narrative tension (a global parameter affecting music, color grading, and fog density) without contaminating any entity's emotional state. The character's face remains neutral; the world around them darkens.

This distinction maps directly to the foreground/background affect distinction in emotion computation: foreground affect (EXPLICIT, BEHAVIORAL) is agent-specific; background affect (ATMOSPHERIC) is environmental.

### 5.2 Scheme C: Continuous Internal, Discrete External

Evidence confidence is stored as a continuous float (0.0–1.0), enabling future gradient-based optimization. For human-readable output, a `display_level` property maps continuous confidence to discrete labels:

```
confidence > 0.8  → EXPLICIT
confidence > 0.5  → BEHAVIORAL
confidence > 0.3  → CONTEXTUAL
confidence ≤ 0.3  → UNDEFINED
```

This is analogous to the softmax→argmax operation in language models: internal representations are continuous and differentiable; external outputs are discrete and interpretable.

A critical implementation insight: **decay must use the stored `level` field, not the derived `display_level`.** During development, a bug caused CONTEXTUAL evidence (level=contextual, confidence=0.7) to be misidentified as BEHAVIORAL via display_level (0.7 falls in the 0.5–0.8 range), resulting in no decay (BEHAVIORAL rate = 1.0). The fix—using the immutable semantic type for decay lookup—illustrates why the level/confidence/display_level separation is essential: `level` is the evidence's identity, `confidence` is its current strength, and `display_level` is a lossy projection for human consumption.

### 5.3 Confidence Ceilings

The WSM enforces hard confidence ceilings after each delta application:

```python
def _clamp_evidence(self):
    for entity in self.state.entities.values():
        ev = entity.emotion.evidence
        ceiling = EVIDENCE_CONFIDENCE_CEILING.get(ev.level, 1.0)
        if ev.confidence > ceiling:
            ev.confidence = ceiling
```

From a Bayesian perspective, these ceilings function as priors: they encode the belief that atmospheric inference can never be highly confident, regardless of how vivid the environmental description. The current ceilings are hand-set; Phase 4 proposes learning optimal prior distributions from human evaluation data.

### 5.4 Type-Specific Decay

After each narrative turn, the WSM decays confidence of all inherited (non-reconfirmed) evidence:

```
new_confidence = old_confidence × DECAY_RATE[level]
```

**[Table 3: Narrative Break Penalty Matrix]**

| Evidence Type | Normal Decay | On Narrative Break |
|--------------|-------------|-------------------|
| EXPLICIT | × 1.0 | × 1.0 |
| BEHAVIORAL | × 1.0 | × 1.0 |
| ATMOSPHERIC | × 0.7 | × 0.0 (reset) |
| CONTEXTUAL | × 0.9 | × 0.5 (extra penalty) |
| CHARACTER | × 1.0 | × 1.0 |
| UNDEFINED | × 1.0 | × 1.0 |

Narrative breaks (scene changes, time jumps) trigger additional penalties: ATMOSPHERIC evidence resets completely (a new scene has its own atmosphere), while CONTEXTUAL evidence receives an extra 50% penalty (situational inferences weaken across scene boundaries). EXPLICIT facts ("the father is dead") and CHARACTER traits ("Aladdin is impulsive") persist indefinitely.

**[Fig 2: Evidence Type Hierarchy]**
```
                    ┌─ EXPLICIT (1.0, no decay) ─── "I was afraid"
                    ├─ BEHAVIORAL (0.85, no decay) ── "he clenched his fist"
Evidence ───────────├─ CHARACTER (0.90, no decay) ── personality prior
                    ├─ CONTEXTUAL (0.50, decay 0.9) ─ situational inference
                    ├─ ATMOSPHERIC (0.30, decay 0.7) ─ environment → N.tension only
                    └─ UNDEFINED (0.00) ──────────── no evidence
```

**[Fig 3: WSM Update Cycle]**
```
Delta arrives → Apply updates → Clamp ceilings → Decay by type
    → If narrative_break: ATMOSPHERIC→0, CONTEXTUAL×0.5, N.tension→0
    → State ready for rendering + context summary
```

### 5.5 Render Intensity Mapping

Confidence maps to rendering strength through a piecewise linear function:

```python
def render_intensity(self) -> float:
    if self.confidence > 0.8:   return 1.0
    elif self.confidence > 0.5: return 0.3 + (confidence - 0.5) * 1.0
    elif self.confidence > 0.3: return 0.1 + (confidence - 0.3) * 1.0
    return 0.0
```

UNDEFINED evidence (confidence ≤ 0.3) produces zero rendering effect. §12 discusses replacing this with a smooth sigmoid composition to enable gradient-based optimization.

## 6. Implementation

### 6.1 Schema

The world state schema is implemented in Python using Pydantic v2 for runtime validation (269 lines). Key design choices: `Field(ge=, le=)` constraints for physical parameters, Enum types for categorical fields, Optional fields in deltas (None = no change), and tuple types for spatial data.

### 6.2 Parser Prompt

The Parser prompt encodes the evidence determination algorithm as natural language rules:

1. **Evidence classification rules**: Definitions, examples, and confidence guidelines for all six types.
2. **Zero-Introspection enforcement**: Explicit prohibition of ATMOSPHERIC evidence updating entity emotion.
3. **Environment extraction rules**: Mandatory scanning for light sources, spatial features, acoustic cues, and tactile information—counteracting the LLM's natural attention bias toward character and dialogue (§9.2).
4. **Output format**: WorldStateDelta JSON with source_span annotations.
5. **Context injection**: Current world state summary from WSM, with narrative break flags.

### 6.3 Stability Test Framework

Phase 0.5 validation measures schema compliance (target 100%), evidence consistency (target >80%), and emotion label consistency (target >90%) across 12 segments × 20 runs. Supports dry-run mode and per-segment PASS/FAIL reporting.

## 7. Experimental Design

### 7.1 Corpus

**[Table 2: Corpus Inventory]**

| Segment ID | Source | Author | Style | Words | Scene Type |
|-----------|--------|--------|-------|-------|------------|
| aladdin_cave_sparse | Aladdin (Gutenberg) | Human | Fairy tale | 47 | outdoor_path |
| aladdin_lamp_sparse | Aladdin (Gutenberg) | Human | Fairy tale | 66 | cave_interior |
| usher_approach_rich | Poe: House of Usher | Human | Gothic | 81 | outdoor_approach |
| masque_rooms_rich | Poe: Masque of Red Death | Human | Gothic | 123 | interior_palace |
| cask_unreliable | Poe: Cask of Amontillado | Human | Gothic | 71 | outdoor_carnival |
| cthulhu_philosophical | Lovecraft: Call of Cthulhu | Human | Cosmic horror | 108 | abstract |
| ackroyd_neutral | Christie: Roger Ackroyd | Human | Detective | 36 | interior_domestic |
| sakakibara_rich | Sakakibara Kaito (AI) | AI | Light novel | 54 | interior_classroom |
| sakakibara_sparse | Sakakibara Kaito (AI) | AI | Light novel | 43 | interior_classroom |
| karl_sensory | Karl (AI) | AI | 2nd person | 73 | interior_classroom |
| karl_social | Karl (AI) | AI | 2nd person | 56 | interior_hallway |
| karl_panic | Karl (AI) | AI | 2nd person | 57 | interior_classroom |

12 segments, 6 styles, 7 human + 5 AI. The Sakakibara full/starter pair (word ratio 5.7:1) provides a naturally aligned sparse/rich comparison.

### 7.2 Experimental Phases

**Phase 0.5** — Prompt stability (240 API calls, gate for Phase 1)
**Phase 1** — Parser fidelity: 5 conditions × all segments (RQ1-4)
**Phase 2** — Rendering: Three.js visual + Tone.js audio, CLIP + normalized fidelity (RQ2)
**Phase 3** — Human evaluation + cognitive correlation (RQ1, RQ5)

**[Fig 4: Experimental Design]**
```
Corpus (12 segments × 6 styles × AI/human)
    → 5 conditions (A: free, B: JSON, C: binary, D: coarse, Full)
    → Phase 1 metrics (fill rate, IEI leak, evidence κ, env recall)
    → Phase 2 rendering (CLIP, normalized fidelity)
    → Phase 3 human eval + cognitive correlation (r with N.tension)
```

### 7.3 Metrics

**Normalized fidelity** (primary): correctly rendered info units / total renderable info units.
**CLIP alignment** (secondary, automated): OpenCLIP ViT-L/14 cosine similarity. Known bias toward photorealistic content.
**IEI leak rate**: emotion assigned on neutral passages.
**Environment recall**: |expected ∩ extracted| / |expected| environmental features.

## 8. Results

### 8.1 Prompt Stability (Phase 0.5)

Stability testing was conducted on GLM-4.5-air with 5 runs per segment across 12 corpus segments. After two rounds of prompt iteration (v1 → v2, adding emotion vocabulary constraints, strategic-intent rules, and enum enforcement):

- Schema compliance: average 95% (target: ≥95%)
- Evidence consistency: average 93% (target: >80%, **PASS**)
- Emotion consistency: average 80% (target: >80%, **borderline**)
- 4/12 segments fully pass all three criteria

Emotion consistency remains the primary bottleneck. Segments with abstract/philosophical content (Lovecraft) and unreliable narrators (Poe's Cask) show the highest variance, reflecting genuine ambiguity in the source text rather than parser instability. *Full multi-round analysis with additional models pending.*

### 8.2 Parser Fidelity (Phase 1, Round 1)

**[Table 4: Phase 1 Condition Comparison (GLM-4.5-air, 12 segments)]**

| Condition | Description | Schema Valid | Avg Fill Rate | Avg Env Fill | IEI Leaks |
|-----------|------------|-------------|---------------|-------------|-----------|
| A | Free text (no schema) | 0/12 | N/A | N/A | N/A |
| B | JSON schema, no evidence | 12/12 | * | * | 0 |
| C | Binary evidence ablation | 0/12 ** | * | 0% | 0 |
| D | Coarse material ablation | 10/12 | 57% | 36% | 0 |
| F | LLEE Full (6-type evidence) | **12/12** | **52%** | **24%** | **0** |

\* B and C use non-LLEE JSON structures; fill rates not directly comparable.
\*\* C outputs binary evidence labels not in the 6-type enum, causing schema validation failure by design.

Key findings:
- **IEI is zero across all structured conditions (B, C, D, F).** The Zero-Introspection Principle suppresses emotional hallucination regardless of evidence granularity.
- **Condition D (coarse) achieves higher fill rate than F (full)** (57% vs 52%), because coarse enums (e.g., "interior") are easier to fill than fine-grained ones (e.g., "cave_interior"). This suggests a precision-recall tradeoff: coarse granularity increases recall at the cost of semantic precision.
- **Environment fill rate is systematically low** (24% for LLEE Full), confirming the LLM attention blindspot hypothesis (§9.2). Environmental details are under-extracted relative to character and emotion information.
- **LLEE Full achieves 100% schema compliance** (12/12), the highest among structured conditions.

*Phase 1 Round 1 preliminary results. Multi-model comparison and multi-round consistency analysis pending.*

**[Fig 5: PLACEHOLDER — Parser fidelity across 5 conditions by corpus style]**
**[Table 5: PLACEHOLDER — Environment recall rate by corpus style]**
**[Fig 6: PLACEHOLDER — Evidence consistency: AI-generated vs human-authored text]**
**[Fig 7: PLACEHOLDER — WSM tension vs human-rated atmosphere (Pearson r)]**

## 9. Discussion

### 9.1 Evidence Grading as Hand-Crafted Attention

LLEE's six evidence types function as six hand-designed attention heads, each with a characteristic decay curve. The confidence computation `confidence = base × source_weight × decay^n` is structurally isomorphic to Transformer attention weight computation. The key difference: Transformer heads are learned; LLEE's types are designed from narrative theory. Phase 4's bilevel optimization proposes to close this gap.

### 9.2 LLM Attention Blindspot

LLMs exhibit systematic attention bias: high attention to character/dialogue/emotion, low attention to environmental physics. For rendering, this bias is inverted—environmental details constitute the majority of parameters. LLEE addresses this through explicit extraction rules and the `scene_features` field. Phase 1 quantifies the "false UNDEFINED" rate.

### 9.3 Bilevel Optimization

LLEE's parameters require two optimization algorithms: evolutionary search for discrete structure (evidence types, enum sets) and gradient descent for continuous parameters (decay rates, ceilings, render curves). The outer loop searches topology; the inner loop optimizes parameters per topology. Analogous to Neural Architecture Search.

### 9.4 Dialogue Subtext and the Evidence Stack

A common objection to Zero-Introspection is dialogue subtext: when a character says "I'm fine" but the reader knows they are not, should the renderer show a neutral face?

LLEE's answer depends on the evidence available. If the text contains only the dialogue line, the renderer correctly shows a neutral face—the author chose not to provide behavioral cues, and LLEE respects that choice. But if prior paragraphs established behavioral evidence (e.g., "she had been crying, her eyes red and swollen"), the WSM retains that evidence with type-specific decay. When the current paragraph says "I'm fine" (EXPLICIT, confidence 0.85), the prior "crying" evidence (BEHAVIORAL, confidence 0.8, no decay) coexists in the state history.

This reveals a limitation of the current single-value emotion model: `apply_delta` overwrites the previous emotion with the new one, erasing the prior evidence. A richer model would maintain an *evidence stack*—multiple concurrent evidence records for the same attribute, potentially contradictory. The renderer could then resolve contradictions modality-specifically: the facial renderer takes the EXPLICIT "fine" (smile), while the vocal renderer takes the BEHAVIORAL "sadness" (slight tremor). The result—smiling face, trembling voice—is subtext, achieved not through inference but through evidence coexistence.

This is precisely where the six-type evidence system provides value over binary (has/no) evidence: binary systems cannot represent "two contradictory pieces of evidence at different confidence levels." The evidence stack is proposed as future work (§12).

### 9.5 Conservative Fidelity

LLEE's fidelity is asymmetric by design: it prioritizes avoiding false positives (injecting information absent from text) over avoiding false negatives (omitting information present in text). The 24% environment fill rate reflects this asymmetry—LLEE would rather leave a scene sparse than hallucinate details. This is analogous to high-specificity diagnostic design in medicine, where the cost of a false positive (misdiagnosis) exceeds the cost of a false negative (missed case). In narrative rendering, a falsely injected emotion distorts the author's intent in ways that are difficult for users to detect, while a missing environmental detail is immediately visible and can be addressed by the renderer's default asset pipeline.

## 10. Threats to Validity

**Internal**: LLM non-determinism mitigated by 20-run stability test. Hand-set ceilings mitigated by ablation (Baseline C). Prompt iteration history recorded. Decay rate sensitivity analysis (±20% perturbation) planned for Phase 1 Round 2.

**External**: Corpus limited to English literary fiction (5 human + 2 AI authors). Renderer limited to Three.js. May not generalize to technical writing, poetry, or non-English text.

**Construct**: CLIP biased toward photorealistic content—mitigated by normalized fidelity as primary metric. IEI operationalized as emotion on neutral passages—may miss subtle injection.

**Reliability**: All code/prompts/corpus open-source and version-controlled. Inter-annotator agreement (Krippendorff's α > 0.67) required for ground truth.

## 11. Limitations

1. **Semantic grouping, not mathematical decoupling**: The seven-group state model (E,V,S,O,H,T,N) is a semantic partition, not a mathematically orthogonal decomposition. Within each group, fields remain coupled (e.g., `visual.lights` contains both spatial position and source type in the same object). True decoupling—separating spatial occupancy from visual attributes as orthogonal feature vectors—is a future direction requiring latent-space methods.
2. **Control signal, not physical quantity**: `render_intensity` is a unitless control signal (analogous to a BlendShape weight or audio bus send level), not a physically-grounded rendering parameter. It does not participate in energy conservation or radiometric equations. Mapping confidence to physically meaningful parameters (color temperature shifts, reverb wet/dry ratios, roughness perturbations) requires deep integration with specific renderer physics models—an engineering task, not a theoretical one.
3. **Strong human priors, unverified emergent potential**: The six evidence types, decay rates, and confidence ceilings are hand-designed from narrative theory. Whether these structures can emerge from evolutionary search starting from a minimal basis (e.g., only ENTITY + UNDEFINED) is an open empirical question addressed in Future Work.
4. **Single-world architecture**: No nested narratives, character beliefs, or multi-perspective states.
5. **Narrator reliability assumed**: All statements treated as trustworthy (implicit reliability = 1.0). Extensible via narrator identity + reliability weight binding.
6. **Attention bias in extraction**: Parser inherits LLM attention distribution. Explicit rules partially compensate; environment fill rate remains systematically low (24%).
7. **Uncalibrated decay**: Rates derived from narrative theory, not empirical cognitive data. Phase 3 cognitive correlation experiment provides initial calibration.
8. **No cross-modal validation**: Visual and audio rendering consistency not verified automatically.
9. **Single-value emotion model**: Current WSM overwrites emotion on each delta, erasing prior evidence. Dialogue subtext (contradictory evidence from different turns) cannot be represented. An evidence stack model is proposed in Future Work.

## 12. Future Work

- **WorldStack (multi-world ontology)**: Multi-layer world state for nested narratives, character visions, flashbacks, and dreams. Each layer inherits from its parent (CONTEXT level) and can feed evidence back (PREDICTED level, confidence ≤ 0.4). This connects to Ryan's possible worlds semantics, where each narrative defines a Textual Actual World and multiple alternative possible worlds.
- **Evolution from minimal priors**: Controlled comparison of evolution starting from hand-crafted Schema (6 types) vs. minimal Schema (ENTITY + UNDEFINED only) vs. random initialization, to determine whether human-designed evidence types are discoverable natural structures or necessary cognitive scaffolding.
- **Bayesian confidence**: Replace clamp with prior × likelihood → posterior, learning prior distributions from human evaluation data.
- **Differentiable render_intensity**: Sigmoid composition for gradient flow from human scores to rendering parameters.
- **Emotion competition**: Within-group softmax for mutually exclusive states (fear vs. joy competing for probability mass).
- **Context predictor**: Lightweight MLP for next-state prediction (PREDICTED evidence, confidence ≤ 0.4).
- **Spatial skeleton**: @REGION topology for coherent 3D layout construction, separating spatial occupancy from visual attributes.
- **Evidence stack**: Replace single-value emotion with a stack of concurrent evidence records, enabling subtext rendering through cross-modal contradiction resolution (e.g., EXPLICIT "fine" → facial smile; BEHAVIORAL "crying" → vocal tremor).

## 13. Conclusion

LLEE establishes a trust boundary between LLM narrative interpretation and deterministic rendering. Its six-type evidence system, grounded in the foreground/background affect distinction, suppresses emotional hallucination while preserving atmospheric and behavioral evidence. The Zero-Introspection Principle prioritizes auditable fidelity over speculative richness. The text-centric ontology ensures equal treatment of fictional and real worlds.

[PLACEHOLDER: Key experimental findings.]

LLEE's discrete symbolic structure and continuous parameters are jointly optimizable through bilevel optimization. The evidence types themselves are candidates for evolutionary search, raising the possibility that the optimal language for describing narrative worlds may differ from human design. If LLEE's symbols eventually evolve beyond human interpretability, that would be its ultimate validation: a language machines designed for machines, grounded in the only truth that matters for rendering—what the text actually says.

## References

[PLACEHOLDER: Full reference list. Key citations:]

- Russell, J. A. (2003). Core affect and the psychological construction of emotion. *Psychological Review*.
- Scherer, K. R. (2005). What are emotions? *Social Science Information*.
- Ryan, M.-L. (1991). *Possible Worlds, Artificial Intelligence, and Narrative Theory*. Indiana University Press.
- LeCun, Y. (2022). A path towards autonomous machine intelligence. *OpenReview*.
- Pixar (2016). Universal Scene Description. https://openusd.org
- NVIDIA (2025). ChatUSD. GTC 2025.
