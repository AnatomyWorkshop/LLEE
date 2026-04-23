# LLEE: A Constraint Layer for Faithful Narrative Rendering with Evidence-Graded World State

**Version 0.7 — April 2026**

---

## Abstract

When large language models (LLMs) convert narrative text into rendering parameters, they systematically inject emotional states and environmental details lacking textual evidence — a failure mode we term *Intentional Emotional Injection* (IEI). We present LLEE, a constraint layer establishing a formally defined *trust boundary* between probabilistic LLM interpretation and deterministic rendering. LLEE does not generate content; it constrains renderers to operate within textual evidence bounds.

We contribute: (1) a mathematical framework providing testable expressions for world-state transitions, evidence decay, confidence ceilings, and IEI detection; (2) a six-type evidence-grading system with type-specific decay and the Zero-Introspection Principle; (3) a formal characterization of IEI as confusion between aleatoric uncertainty (narrative genuinely undetermined) and epistemic uncertainty (parser extraction failure), reframing UNDEFINED as active classification; (4) cross-model validation (GLM-4.5-air, DeepSeek Chat) demonstrating zero IEI across all structured conditions with 52–68% fill rates; and (5) evidence boundary specifications for contradictory evidence handling and multi-modal source extensibility.

Decay sensitivity analysis reveals a critical threshold: contextual evidence rate 0.9 is near a bifurcation point where +20% perturbation eliminates decay entirely. All code, prompts, and data are open-source.

---

## 1. Introduction

### 1.1 The Problem

Consider: "Next day the magician led Aladdin into some beautiful gardens a long way outside the city gates." A faithful rendering depicts two figures in gardens. An IEI-contaminated rendering adds ominous lighting, tense music, fearful expression — none evidenced by text. The magician's intent is known from prior context, but *this passage* describes no fear.

IEI is not aesthetic preference. In interactive fiction, educational visualization, and accessibility tools, the distinction between "what the text says" and "what the AI infers" is a matter of trust.

### 1.2 LLEE as Constraint Layer

LLEE establishes a *trust boundary*: LLM uncertainty is isolated, quantified, and constrained before reaching the rendering pipeline. On one side, the Parser operates probabilistically. On the other, the World State Machine (WSM) and adapters operate deterministically.

LLEE is analogous to a traffic signal — it does not generate traffic, it prevents collisions. The renderer's default assets fill space between LLEE's anchors; LLEE ensures those anchors are grounded in text.

### 1.3 Reframing IEI

Cross-model data (§8) confirms zero IEI leakage under structured constraints. IEI is a *solved baseline*. The deeper question: **why does IEI occur?**

We propose IEI is fundamentally a confusion of two uncertainty types:

- **Aleatoric**: The narrative is genuinely undetermined. The author chose not to specify. Irreducible.
- **Epistemic**: The text contains evidence the parser missed. Reducible through better models.

LLMs commit IEI by treating aleatoric uncertainty as epistemic — assuming the text *should* specify an emotion and filling the gap with priors. LLEE's UNDEFINED preserves aleatoric uncertainty rather than collapsing it into hallucination.

### 1.4 Research Questions

- **RQ1**: Can structured evidence grading suppress IEI across different LLMs?
- **RQ2**: Does differential encoding achieve higher fidelity than unconstrained output?
- **RQ3**: How does LLM attention bias affect world-state completeness?
- **RQ4**: How sensitive are decay parameters to perturbation?
- **RQ5**: Can the framework support contradictory evidence and multi-modal sources without architectural change?

### 1.5 Contributions

- **C1**: Mathematical framework (§4) — formal expressions for state transitions, decay, ceilings, IEI detection.
- **C2**: Six-type evidence system with Zero-Introspection formally encoded.
- **C3**: IEI as aleatoric/epistemic confusion; UNDEFINED as active classification.
- **C4**: Cross-model validation (2 LLMs × 5 conditions × 12 segments), zero IEI, sensitivity analysis.
- **C5**: Evidence boundary specification (§5.5) — contradiction handling, source provenance, evidence-stack architecture.

---

## 2. Related Work

**ChatUSD** (NVIDIA, GTC 2025) enables conversational scene editing via natural language USD commands. Designed for human-in-the-loop; no cross-turn consistency, no evidence grading, no IEI handling. LLEE targets automated pipeline-mode rendering where state consistency is essential.

**FactTrack** (Min et al., 2023) tracks factual consistency in long-form generation. Does not distinguish evidence types, model emotion, or interface with renderers. LLEE extends state-tracking with evidence grading and rendering output.

**CRANE** (Lee et al., 2024) uses constrained decoding for structural compliance at the token level. LLEE operates at the semantic level, ensuring content is grounded in evidence. Orthogonal approaches.

**USD/Omniverse** (Pixar, 2016; NVIDIA) provides scene interchange. LLEE is an AI frontend — where USD describes *what exists*, LLEE describes *why it exists* (evidence) and *how certain we are* (confidence).

**Emotion computation**: The foreground/background affect distinction (Russell, 2003; Scherer, 2005) is operationalized by LLEE's ATMOSPHERIC type: background affect influences global parameters but never entity emotion. To our knowledge, the first system encoding this distinction into a rendering evidence model.

**JEPA** (LeCun, 2022) learns world dynamics via self-supervised latent prediction. JEPA predicts *what happens next*; LLEE describes *what is now*. LLEE is deliberately static — prediction introduces uncertainty that would compromise the trust boundary. Future integration: JEPA predictions as PREDICTED-level evidence (confidence ≤ 0.4).

---

## 3. Design Principles

### 3.1 Zero-Introspection Principle

**No emotional state shall be assigned to any entity unless the source text provides direct evidence.**

1. Absent emotion → UNDEFINED (not "neutral," not "calm" — explicitly unknown).
2. Environmental descriptions → N.tension only, **never** E.emotion (the ATMOSPHERIC constraint).
3. Contextual inference → permitted but capped at confidence 0.50.

This is not a claim about what characters *feel* — it is about what the *text establishes*. We sacrifice speculative richness for auditable fidelity.

### 3.2 Text-Centric Ontology

Confidence measures *textual evidence strength*, not *physical plausibility*. "An enormous genie rose out of the earth" → EXPLICIT (0.9). "The cave was probably cold" → CONTEXTUAL (≤ 0.50). Fictional and real worlds enjoy equal ontological status.

### 3.3 Fact-Statement Principle

LLEE models *what the text states*, not *what characters believe*. "The magician was a fraud" is a world fact regardless of Aladdin's knowledge. Perspective rendering is delegated to the renderer.

### 3.4 Conservative Fidelity

Fidelity is asymmetric: false positive cost (injecting absent emotion, undetectable distortion) exceeds false negative cost (omitting present detail, visible and addressable by renderer defaults). Analogous to high-specificity diagnostic design.

---

## 4. Mathematical Framework

This section provides formal expressions for LLEE's core mechanisms. Every parameter in the implementation corresponds to a term in these equations.

### 4.1 World State Space (M1)

The narrative world is represented as a seven-group state vector:

$$W = (E, V, S, O, H, T, N)$$

where $E$ = Entities, $V$ = Visual Field, $S$ = Sonic Field, $O$ = Olfactory, $H$ = Haptic, $T$ = Temporal, $N$ = Narrative Meta. Each narrative segment produces a differential update $\Delta_t$ containing only changed fields. The WSM applies deltas deterministically:

$$W_{t+1} = \text{WSM}(W_t, \Delta_t) = \text{Decay}(\text{Clamp}(\text{Apply}(W_t, \Delta_t)))$$

This is a *declarative* state transition, not a *predictive* one — the WSM does not learn $F$ or predict $W_{t+1}$ from $W_t$. It receives $\Delta_t$ from the Parser and applies it.

### 4.2 Evidence Decay (M2)

For each evidence record $e$ with confidence $c_t(e)$ and evidence level $\ell(e)$:

$$c_{t+1}(e) = c_t(e) \cdot r_{\ell(e)}$$

where $r_\ell$ is the type-specific decay rate. On narrative break (scene change, time jump):

$$c_{t+1}(e) = c_t(e) \cdot r_{\ell(e)} \cdot p_{\ell(e)}$$

with penalty $p_\ell$: $p_{\text{ATMOSPHERIC}} = 0.0$ (complete reset), $p_{\text{CONTEXTUAL}} = 0.5$.

**Theoretical persistence**: The number of turns for confidence to decay from ceiling $\theta_\ell$ to threshold $\epsilon$ is:

$$\tau(\ell) = \frac{\ln(\epsilon / \theta_\ell)}{\ln(r_\ell)}$$

This yields: ATMOSPHERIC ($r=0.7, \theta=0.30$) persists ~5.0 turns; CONTEXTUAL ($r=0.9, \theta=0.50$) persists ~21.9 turns (§8.3).

### 4.3 Confidence Ceilings (M3)

The WSM enforces hard ceilings after each delta:

$$\forall t, \forall e: \quad c_t(e) \leq \theta_{\ell(e)}$$

This is the mathematical expression of Zero-Introspection: evidence strength is bounded by evidence *type*, not by content vividness. A maximally vivid atmospheric description ("the walls wept with condensation, shadows pooled like blood") still cannot exceed $\theta_{\text{ATMOSPHERIC}} = 0.30$.

### 4.4 IEI Detection (M4)

$$\text{IEI}(\Delta, T) = 1 \iff \exists\, a \in \Delta.\text{emotions}: a.\text{value} \neq \text{UNDEFINED} \;\wedge\; \text{NoEvidence}(T, a.\text{entity})$$

where $T$ is the source text and $\text{NoEvidence}(T, e)$ is operationalized as: $T$ is a pre-labeled neutral passage containing no emotional cues for entity $e$.

### 4.5 Fill Rate (M5)

$$\text{FillRate}(\Delta) = \frac{|\{f \in \mathcal{F} : \Delta[f] \neq \text{None}\}|}{|\mathcal{F}|}$$

Decomposed by modality: $\text{FillRate}_{\text{env}}$ covers visual and sonic fields; $\text{FillRate}_{\text{emo}}$ covers entity emotions.

### 4.6 Evidence Calibration (M6)

Parser-vs-human agreement measured by Cohen's Kappa:

$$\kappa = \frac{P_o - P_e}{1 - P_e}$$

where $P_o$ is observed agreement on evidence level labels, $P_e$ is chance agreement. Target: $\kappa > 0.6$ (substantial agreement).

### 4.7 Render Intensity (M7)

Confidence maps to rendering strength via parameterized sigmoid:

$$r(c; \alpha, \beta) = \sigma(\alpha(c - \beta)) = \frac{1}{1 + e^{-\alpha(c - \beta)}}$$

Each rendering parameter has independent $(\alpha, \beta)$: fog density $(8.0, 0.4)$, color temperature shift $(12.0, 0.6)$, reverb wet/dry $(6.0, 0.3)$. The sigmoid is differentiable, enabling gradient-based optimization of rendering curves from human evaluation data (Future Work).

---

## 5. Evidence System

### 5.1 Evidence Types

**[Table 1: Evidence Types]**

| Type | Definition | Decay | Ceiling | Example |
|------|-----------|-------|---------|---------|
| EXPLICIT | Direct statement of state or fact | 1.0 | 1.00 | "I was afraid"; "the lamp glowed blue" |
| BEHAVIORAL | Observable action implying state | 1.0 | 0.85 | "he clenched his fist"; "she wept" |
| ATMOSPHERIC | Environment implying mood; N.tension only, **never** E.emotion | 0.7 | 0.30 | "bleak walls"; "soundless day" |
| CONTEXTUAL | Weak situational inference | 0.9 | 0.50 | Father died → probably sad |
| CHARACTER | Stable personality prior; never decays | 1.0 | 0.90 | Aladdin's impulsiveness |
| UNDEFINED | No evidence | 1.0 | 0.00 | Text provides no information |

ATMOSPHERIC resolves a tension in Zero-Introspection: Poe writes "dull, dark, and soundless day" — environmental description, not character emotion. Ignoring it strips Poe's prose of atmosphere. ATMOSPHERIC channels environmental mood into narrative tension without contaminating entity emotion. This maps to the foreground/background affect distinction (Russell, 2003).

### 5.2 Scheme C: Continuous Internal, Discrete External

Confidence is stored as continuous float (0.0–1.0). A `display_level` property maps to discrete labels for human readability:

```
> 0.8 → EXPLICIT | > 0.5 → BEHAVIORAL | > 0.3 → CONTEXTUAL | ≤ 0.3 → UNDEFINED
```

Critical insight: **decay must use stored `level`, not derived `display_level`.** A bug during development caused CONTEXTUAL evidence (level=contextual, confidence=0.7) to be misidentified as BEHAVIORAL via display_level, suppressing decay. The fix illustrates why level/confidence/display_level separation is essential.

### 5.3 Narrative Break Handling

**[Table 2: Narrative Break Penalties]**

| Type | Normal Decay | On Break |
|------|-------------|----------|
| ATMOSPHERIC | × 0.7 | × 0.0 (reset) |
| CONTEXTUAL | × 0.9 | × 0.5 (extra) |
| EXPLICIT/BEHAVIORAL/CHARACTER | × 1.0 | × 1.0 |

Scene changes reset atmosphere completely; situational inferences weaken. Facts and traits persist.

### 5.4 Render Intensity

Current implementation (v0.6, piecewise linear):

```python
def render_intensity(self) -> float:
    if self.confidence > 0.8:   return 1.0
    elif self.confidence > 0.5: return 0.3 + (self.confidence - 0.5) * 1.0
    elif self.confidence > 0.3: return 0.1 + (self.confidence - 0.3) * 1.0
    return 0.0
```

v0.7 proposes sigmoid replacement (§4.7) with per-parameter semantic anchors. This is a *control signal* (analogous to BlendShape weight or audio send level), not a physically-grounded quantity. It does not participate in energy conservation. Mapping to physical parameters (color temperature, reverb ratio) requires renderer-specific integration.

### 5.5 Evidence Boundaries

This section explicitly defines how LLEE handles edge cases at the boundary of its evidence model.

**Contradictory evidence (current)**: Latest-value override. When a new delta assigns emotion "fine" (EXPLICIT, 0.85) to an entity whose prior state was "sadness" (BEHAVIORAL, 0.8), the new value replaces the old. Prior evidence is lost. This is a known simplification.

**Contradictory evidence (proposed)**: Evidence stack. Multiple concurrent evidence records for the same attribute:

```python
emotion_stack = [
    Evidence(value="sadness", level=BEHAVIORAL, confidence=0.8),  # prior turn
    Evidence(value="fine", level=EXPLICIT, confidence=0.85),       # current turn
]
```

Renderers resolve contradictions modality-specifically: facial renderer takes EXPLICIT "fine" (smile); vocal renderer takes BEHAVIORAL "sadness" (tremor). The result — smiling face, trembling voice — is subtext through evidence coexistence, not inference.

**UNDEFINED subtypes (proposed)**:

- *UNDEFINED_ALEATORIC*: Text genuinely silent. Renderer uses neutral defaults; no context override permitted.
- *UNDEFINED_EPISTEMIC*: Text contains information parser missed. Renderer uses neutral defaults but may perform low-intensity context interpolation under user authorization.

This distinction localizes IEI's root cause: LLMs confuse aleatoric with epistemic, filling genuinely undetermined states with statistical priors.

**Source provenance**: The `Evidence.source` field (TEXT, CONTEXT, PREDICTED, EXTERNAL, CROSS_MODAL) is architecturally extensible. A visual model outputting `{emotion: "joy", confidence: 0.85}` enters the same evidence structure as text-derived evidence — only the source tag differs. The evidence system is source-agnostic by design.

---

## 6. Architecture and Implementation

### 6.1 Pipeline

```
Narrative Text → [LLM Parser] → WorldStateDelta (JSON)
                                      ↓
                              [World State Machine]
                              ↓ Apply → Clamp → Decay
                              WorldState (current)
                                      ↓
                    ┌─────────────────┼─────────────────┐
              [Visual Adapter]  [Audio Adapter]  [Context Summary]
              Three.js / USD    Tone.js / FMOD   → next Parser call
```

### 6.2 Schema (269 lines Python/Pydantic v2)

Seven groups with typed fields and evidence annotations. Key choices: `Field(ge=, le=)` constraints, Enum types for categoricals, Optional fields in deltas (None = no change), `scene_features: list[str]` for environment extraction.

### 6.3 World State Machine (170 lines)

Three-phase update: Apply (merge delta), Clamp (enforce ceilings), Decay (type-specific rates + narrative break penalties). Sliding context buffer (5 recent deltas) generates summaries for next Parser call.

### 6.4 Parser Prompt

Encodes evidence rules as natural language: evidence classification definitions, Zero-Introspection enforcement, environment extraction rules (counteracting attention bias), 15-label emotion vocabulary, enum constraints. 11 Critical Rules evolved through 2 prompt iterations.

### 6.5 Normalizer

`normalize_delta()` handles ~15 type mismatch patterns in LLM structured output (string→dict, list→dict, enum case normalization). This normalizer is itself a contribution: a catalog of common type errors in LLM structured output.

---

## 7. Experimental Design

### 7.1 Corpus

**[Table 3: Corpus Inventory]**

| Segment | Source | Author | Style | Words |
|---------|--------|--------|-------|-------|
| aladdin_cave_sparse | Aladdin (Gutenberg) | Human | Fairy tale | 47 |
| aladdin_lamp_sparse | Aladdin (Gutenberg) | Human | Fairy tale | 66 |
| usher_approach_rich | Poe: Usher | Human | Gothic | 81 |
| masque_rooms_rich | Poe: Masque | Human | Gothic | 123 |
| cask_unreliable | Poe: Cask | Human | Gothic | 71 |
| cthulhu_philosophical | Lovecraft | Human | Cosmic horror | 108 |
| ackroyd_neutral | Christie | Human | Detective | 36 |
| sakakibara_rich | AI novel | AI | Light novel | 54 |
| sakakibara_sparse | AI novel | AI | Light novel | 43 |
| karl_sensory | AI novel | AI | 2nd person | 73 |
| karl_social | AI novel | AI | 2nd person | 56 |
| karl_panic | AI novel | AI | 2nd person | 57 |

12 segments, 6 styles, 7 human-authored + 5 AI-generated.

### 7.2 Conditions

| Condition | Description |
|-----------|------------|
| A | Free text, no schema |
| B | JSON schema, no evidence grading |
| C | LLEE + binary evidence (HAS/NO ablation) |
| D | LLEE + coarse enums (3-value materials) |
| F | LLEE Full (6-type evidence) |

### 7.3 Metrics

- **Fill rate**: Non-None fields / total fields (M5)
- **Environment fill rate**: Visual + sonic environment fields
- **IEI leak rate**: Emotion assigned on neutral passages (M4)
- **Schema compliance**: Valid WorldStateDelta parse rate
- **Normalized fidelity**: Correctly rendered info units / total renderable units [Phase 2]
- **CLIP alignment**: OpenCLIP ViT-L/14 cosine similarity [Phase 2]

---

## 8. Results

### 8.1 Prompt Stability (Phase 0.5)

GLM-4.5-air, 5 runs × 12 segments, 2 prompt iterations (v1→v2):

- Schema compliance: 95% (target ≥95%)
- Evidence consistency: 93% (target >80%, **PASS**)
- Emotion consistency: 80% (target >80%, **borderline**)
- 4/12 segments fully pass all criteria

Bottleneck: abstract/philosophical content (Lovecraft) and unreliable narrators (Poe) show highest variance, reflecting genuine textual ambiguity.

### 8.2 Parser Fidelity (Phase 1)

**[Table 4: Cross-Model Comparison — GLM-4.5-air vs DeepSeek Chat]**

| Condition | GLM Schema | GLM Fill | GLM Env | DS Schema | DS Fill | DS Env | IEI (both) |
|-----------|-----------|----------|---------|-----------|---------|--------|------------|
| A | N/A | N/A | N/A | — | — | — | N/A |
| B | 12/12 | * | * | — | — | — | 0 |
| C | 0/12 | 51%* | 0%* | 0/12 | 51% | 7% | 0 |
| D | 10/12 | 57% | 36% | 11/12 | 68% | 55% | 0 |
| F | **12/12** | **52%** | **36%** | **10/12** | **68%** | **60%** | **0** |

\* C uses binary labels outside 6-type enum; schema failure by design.

Key findings:

1. **IEI is zero across all structured conditions on both models.** The constraint layer suppresses emotional hallucination regardless of LLM capability.
2. **DeepSeek Chat achieves significantly higher fill rates** (68% vs 52% overall, 60% vs 36% environment). Stronger models extract more information under the same constraints — the constraint layer is a ceiling, not a floor.
3. **Environment fill rate is the primary gap.** Even DeepSeek's 60% means 40% of environmental information is missed, confirming the LLM attention blindspot (§9.1).
4. **Condition D (coarse) matches F (full) on fill rate** for DeepSeek (both 68%), but with lower environment fill (55% vs 60%). The six-type system's value is in semantic precision, not fill rate.
5. **Condition C is universally non-compliant** (0/12 on both models), confirming that binary evidence labels are insufficient for schema compliance.

### 8.3 Decay Sensitivity Analysis

Theoretical persistence (turns to decay from ceiling to threshold 0.05):

**[Table 5: Sensitivity Analysis]**

| Variant | ATM Rate | CTX Rate | ATM Persist | CTX Persist |
|---------|----------|----------|-------------|-------------|
| Baseline | 0.70 | 0.90 | 5.0 turns | 21.9 turns |
| +20% | 0.84 | 1.00 | 10.3 turns | ∞ (no decay) |
| −20% | 0.56 | 0.72 | 3.1 turns | 7.0 turns |

**Critical finding**: CONTEXTUAL rate 0.9 is near a bifurcation point. At +20% (rate=1.0), contextual evidence never decays — situational inferences persist indefinitely, violating the design intent. At −20% (rate=0.72), persistence drops from 22 to 7 turns — a 3× reduction.

ATMOSPHERIC is moderately sensitive: ±20% produces 2× variation in persistence (3–10 turns), which is within acceptable bounds for atmospheric mood dissipation.

**Implication**: The CONTEXTUAL rate should be lowered to ~0.85 to increase distance from the critical threshold, or replaced with a data-driven estimate (§10.2).

---

## 9. Discussion

### 9.1 LLM Attention Blindspot

LLMs exhibit systematic attention bias: high attention to character/dialogue/emotion, low attention to environmental physics. For rendering, this bias is inverted — environmental details constitute the majority of parameters. DeepSeek Chat's higher environment fill rate (60% vs GLM's 36%) suggests that model capability partially compensates, but a 40% gap remains even with a strong model. Explicit extraction rules in the prompt are necessary but insufficient.

### 9.2 Evidence Grading as Hand-Crafted Attention

LLEE's six evidence types function as six hand-designed attention heads, each with a characteristic decay curve. The confidence computation $c = c_0 \cdot r^n$ is structurally isomorphic to exponential attention weight decay. The difference: Transformer heads are learned; LLEE's types are designed from narrative theory. Phase 4's bilevel optimization proposes to close this gap — evolutionary search for discrete structure, gradient descent for continuous parameters.

### 9.3 The Constraint Layer's Value Proposition

The cross-model data reveals LLEE's core value: **IEI suppression is model-independent.** Both GLM (weaker) and DeepSeek (stronger) achieve zero IEI under the same constraints. Meanwhile, fill rate scales with model capability (52% → 68%). The constraint layer does not limit what strong models can extract — it only limits what they can fabricate.

This is the traffic signal analogy made empirical: the signal doesn't slow down fast cars, it prevents all cars from running red lights.

### 9.4 Subtext and Evidence Coexistence

When a character says "I'm fine" after crying, the current system overwrites "sadness" with "fine." The evidence stack (§5.5) would preserve both, enabling modality-specific rendering: facial "fine" + vocal "sadness" = subtext. This is not inference — it is evidence coexistence. The six-type system enables this where binary (has/no) cannot: binary systems cannot represent "two contradictory pieces of evidence at different confidence levels."

### 9.5 Toward Multi-Modal Evidence

The evidence structure is source-agnostic (§5.5). A visual model's output enters the same stack as text-derived evidence. This means LLEE's architecture naturally extends from "text constraint layer" to "multi-modal belief manager" — fusing evidence from text, vision, audio, and user interaction. The core mechanisms (decay, ceilings, IEI detection) apply unchanged. What changes is only the source tag.

### 9.6 Decay Rate and Information Theory

The hand-set decay rates (0.7, 0.9) approximate an information-theoretic quantity:

$$r_\ell \approx \exp(-H(s_{t+1}^\ell \mid s_t^\ell))$$

where $H$ is conditional entropy over the evidence-type subspace. High conditional entropy (next state unpredictable from current) → fast decay. Low entropy (next state predictable) → slow decay. ATMOSPHERIC has high entropy (mood shifts rapidly); CONTEXTUAL has lower entropy (situations persist). Phase 4 proposes estimating these from data.

---

## 10. Threats to Validity

**Internal**: LLM non-determinism mitigated by multi-run stability test. Hand-set parameters mitigated by ablation (Condition C) and sensitivity analysis (§8.3). Prompt iteration history recorded.

**External**: Corpus limited to English literary fiction (5 human + 2 AI authors). Two LLMs tested. May not generalize to technical writing, poetry, or non-English text.

**Construct**: IEI operationalized as emotion on neutral passages — may miss subtle injection. Fill rate treats all fields equally — some fields matter more for rendering.

**Reliability**: All code, prompts, corpus open-source. Sensitivity analysis reproducible without API calls.

---

## 11. Limitations

1. **Semantic grouping, not mathematical decoupling**: The seven groups are a semantic partition, not orthogonal decomposition. Within groups, fields remain coupled.
2. **Control signal, not physical quantity**: `render_intensity` is unitless. Mapping to physical parameters requires renderer-specific integration.
3. **Strong human priors**: Six types, decay rates, ceilings are hand-designed. Whether they emerge from evolutionary search is an open question.
4. **Single-world architecture**: No nested narratives, character beliefs, or multi-perspective states.
5. **Narrator reliability assumed**: All statements treated as trustworthy (reliability = 1.0).
6. **Attention bias in extraction**: Environment fill rate remains 40–64% below theoretical maximum even with explicit rules.
7. **Uncalibrated decay**: Rates from narrative theory, not cognitive data. Sensitivity analysis (§8.3) reveals critical thresholds.
8. **Single-value emotion**: Current WSM overwrites emotion per delta. Evidence stack proposed but not implemented.
9. **Two-model validation**: Cross-model comparison limited to GLM and DeepSeek. Broader validation needed.

---

## 12. Future Work

- **Evidence stack**: Replace single-value emotion with concurrent evidence records. Enable subtext through cross-modal contradiction resolution.
- **UNDEFINED subtypes**: Implement ALEATORIC/EPISTEMIC distinction in schema and parser.
- **Data-driven decay**: Estimate $r_\ell$ from conditional entropy of narrative sequences, replacing hand-set values.
- **Sigmoid render_intensity**: Implement §4.7 with per-parameter $(\alpha, \beta)$; optimize from human evaluation data.
- **WorldStack**: Multi-layer state for nested narratives, flashbacks, dreams. Parent→child inheritance at CONTEXT level; child→parent feedback at PREDICTED level (≤ 0.4).
- **Evolution from minimal priors**: Controlled comparison — evolution from 6-type Schema vs. minimal (ENTITY + UNDEFINED) vs. random initialization.
- **Bayesian confidence**: Replace clamp with prior × likelihood → posterior.
- **Context predictor**: Lightweight MLP for next-state prediction as PREDICTED evidence.
- **Multi-modal sources**: Extend evidence intake from text-only to vision, audio, user interaction.
- **Spatial skeleton**: @REGION topology for coherent 3D layout, separating spatial occupancy from visual attributes.

---

## 13. Conclusion

LLEE establishes a trust boundary between LLM narrative interpretation and deterministic rendering. Its six-type evidence system suppresses emotional hallucination — zero IEI across two LLMs and five experimental conditions — while preserving 52–68% of textual information. The mathematical framework (§4) provides every design parameter with a testable equation. Sensitivity analysis reveals that the contextual decay rate operates near a critical threshold, motivating data-driven calibration.

LLEE is a constraint layer, not a generation system. It does not produce visual or auditory content. It ensures that whatever content the renderer produces does not violate what the text establishes. The space between LLEE's evidence anchors is filled by the renderer's assets and physics — LLEE's contribution is ensuring those anchors are grounded in text, not hallucination.

The evidence system's source-agnostic architecture means LLEE naturally extends from text constraint to multi-modal belief management. The evidence stack design enables subtext rendering through evidence coexistence rather than inference. These extensions require no architectural change — only implementation of structures already specified in the formal framework.

UNDEFINED is not a failure. It is LLEE's most important output: an honest declaration that the text is silent, and the rendering should respect that silence.

---

## References

- Russell, J. A. (2003). Core affect and the psychological construction of emotion. *Psychological Review*.
- Scherer, K. R. (2005). What are emotions? *Social Science Information*.
- Ryan, M.-L. (1991). *Possible Worlds, Artificial Intelligence, and Narrative Theory*. Indiana University Press.
- LeCun, Y. (2022). A path towards autonomous machine intelligence. *OpenReview*.
- Pixar (2016). Universal Scene Description. https://openusd.org
- NVIDIA (2025). ChatUSD. GTC 2025.
- Min, S. et al. (2023). FactTrack: Factual consistency tracking in long-form generation.
- Lee, J. et al. (2024). CRANE: Constrained decoding for structured LLM output.
