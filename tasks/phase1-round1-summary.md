# Phase 1 Round 1 Results — GLM-4.5-air

## 2026-04-22

### Conditions Run
| Condition | Description | Segments | Status |
|-----------|------------|----------|--------|
| A | Free text, no schema | 12/12 | Done |
| B | JSON schema, no evidence grading | 12/12 | Done |
| C | Binary evidence (HAS/NO) | 12/12 | Done |
| D | Coarse materials (3 values) | 12/12 | Done |
| F | LLEE Full (6-type evidence) | 12/12 | Done |

### Summary Table
| Metric | A | B | C | D | F |
|--------|---|---|---|---|---|
| Schema valid | 0/12 | 12/12 | 0/12 | 10/12 | **12/12** |
| Avg fill rate | N/A | 0%* | 100%* | 57% | 52% |
| Avg env fill | N/A | 0%* | 0% | 36% | 24% |
| IEI leaks | N/A | 0 | 0 | 0 | **0** |

*B/C fill rates not directly comparable due to different JSON structures.

### Key Findings

1. **IEI zero leaks across all structured conditions** — Zero-Introspection works
2. **D > F on fill rate** (57% vs 52%) — coarse enums are easier to fill but less precise
3. **D > F on env fill** (36% vs 24%) — same pattern for environment
4. **F achieves 100% schema compliance** — LLEE Full prompt produces valid output
5. **C schema invalid** — binary evidence labels not in 6-type enum (expected)

### Interpretation
The D vs F comparison is the ablation study's first data point:
- Coarse granularity → higher fill rate (easier to fill "interior" than "cave_interior")
- Fine granularity → lower fill rate but higher semantic precision
- Both achieve zero IEI — evidence grading doesn't affect IEI suppression

### Next Steps
- Run F with DeepSeek Chat and Claude Opus for cross-model comparison
- Compute evidence calibration (Cohen's κ) once ground truth is annotated
- Run multiple rounds of F for consistency measurement
