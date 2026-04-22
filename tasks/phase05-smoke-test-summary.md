# Phase 0.5 Smoke Test Summary — 2026-04-22

## Single-Run Results (12 segments each)

| Model | Provider | Pass | Fail | Pass Rate | Failed Segments |
|-------|----------|------|------|-----------|-----------------|
| glm-4.5-air | ZhipuAI | 10 | 2 | 83% | aladdin_cave_sparse, cthulhu_philosophical |
| deepseek-chat | DeepSeek | 10 | 2 | 83% | masque_rooms_rich, sakakibara_classroom_rich |
| claude-opus-4-6 | Anthropic relay | 10 | 2 | 83% | usher_approach_rich, karl_classroom_sensory |
| deepseek-reasoner | DeepSeek | 5 | 7 | 42% | Reasoning model often doesn't output final JSON |
| claude-sonnet-4-6 | Anthropic relay | 2 | 10 | 17% | Reverb enum issues (pre-normalizer) |

## Key Findings

1. All three non-reasoning models (GLM, DeepSeek Chat, Claude Opus) achieve 83% compliance after normalization
2. Failed segments differ across models — no single segment fails on all models
3. Remaining failures are edge cases in the normalizer, not fundamental model limitations
4. DeepSeek Reasoner is unsuitable for structured output (puts JSON inside reasoning chain)
5. Claude Sonnet via relay has connection stability issues

## Normalizer Fixes Applied
- position: dict/list → tuple
- state: dict → string
- action: string → dict with verb
- sonic.reverb: map non-enum values to closest valid enum
- sonic.ambient_sounds: string → dict, add missing id/sound_type
- visual.atmosphere: string/list → dict
- visual.scene_type_evidence: string → Evidence dict
- visual.lights: string → dict, add missing id
- narrative.stage: map non-enum values to closest valid stage

## Recommendation
- Primary Parser: GLM-4.5-air (fastest, cheapest, 83% compliance)
- Validation Parser: Claude Opus 4.6 (highest quality output when it works)
- Next step: 5-run consistency test on GLM to measure evidence/emotion stability
