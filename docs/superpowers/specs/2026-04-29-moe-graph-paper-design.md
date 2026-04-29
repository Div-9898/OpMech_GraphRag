# MoE-Graph Paper — Design Spec

**Date:** 2026-04-29
**Author:** Divyansh Singh (with brainstorming via Claude Code)
**Status:** Draft for user review
**Companion docs:** `docs/Claude Chat 1.docx`, `docs/OpMech_GraphRAG_Experimental_Spec.docx`

---

## 0. Executive summary

This spec defines the engineering and methodological work to produce empirically defensible numbers for the **MoE-Graph paper** — the paper claiming that hard-routed expert specialisation by edge type produces measurably higher-quality knowledge graphs from SEC filings than a single-prompt LLM baseline. The paper is being separated from a sibling paper on commutator-based analysis; that sibling paper depends on the graph this paper produces but is not in scope here.

**Outcome we are committing to:** a self-contained new repository (`OpMech_MoE_Graph/`) with a `dvc repro`-able pipeline that produces every number in spec Tables 2, 3, 4 plus calibration figures and Tier-3 robustness checks, against a 4-stage human + LLM gold standard. Submission target is a fresh paper submission optimised for empirical solidity, not for a specific deadline.

**Locked-in decisions** (from brainstorming):

| Decision | Choice |
|---|---|
| Repo strategy | Two clean repos. Repo A (this paper) first; Repo B (commutator paper) later. Local now, GitHub later. |
| Repo init approach | Greenfield + DVC pipeline (Approach Gamma). |
| LLM (system under test) | `Qwen/Qwen3-14B` dense, served via vLLM in FP8 or AWQ on RTX 5090 24GB. |
| LLM (judge, Stage 4) | `claude-sonnet-4-6` via Anthropic API (`claude-opus-4-7` as config-flag override). |
| Annotation protocol | 4-stage: A + B human → tiebreaker C → LLM audit. |
| Tier scope | Full Tier 1 + Tier 2 + Tier 3. |
| Filing scope | 12 Apple SEC filings (10-Ks + recent 10-Qs); MSFT FY2024 as Tier 3.3 spot-check. |
| Prompt-tuning rule | Prompts iterated on a held-out dev split (15%) only; locked before test annotation begins. |
| Annotators | 3 humans confirmed available + LLM as 4th audit. |
| Realistic timeline | ~4–5 weeks comfortable; ~3 weeks compressed if Tier 3 is dropped. |

**Naming hazard noted up-front (must surface in paper §1):** the "MoE" in this paper refers to mixture-of-experts at the **graph-construction layer** (six hard-routed experts, one per edge type). The Qwen3-14B backbone is dense; we deliberately did not pick a token-level MoE LLM (Qwen3.5-35B-A3B was considered and rejected) to keep this distinction clean.

---

## 1. Repository layout

New repository: **`OpMech_MoE_Graph/`** (sibling to the existing `OpMech_GraphRag/`; both local, both eventually on GitHub).

```
OpMech_MoE_Graph/
├── README.md                         # paper-facing reproducibility instructions
├── pyproject.toml                    # uv-managed; pinned versions
├── dvc.yaml                          # pipeline stages (Section 2)
├── dvc.lock                          # data hashes, committed
├── .dvc/                             # DVC config (S3 remote optional later)
├── params.yaml                       # all experiment hyperparameters in one file
├── docker-compose.yml                # neo4j + vllm services
│
├── src/moe_graph/                    # importable Python package
│   ├── __init__.py
│   ├── config.py                     # pydantic-settings; reads params.yaml
│   ├── models.py                     # Node, Edge, EdgeType (Pydantic)
│   ├── llm_client.py                 # SystemLLMClient (Qwen3-14B) + JudgeLLMClient (Claude)
│   ├── ingestion/                    # sec_fetcher, html_parser, xbrl_processor
│   ├── embedding/                    # FinBERT engine
│   ├── experts/                      # 6 experts + base.py contract
│   ├── graph/                        # neo4j_client, builder, connectivity
│   ├── pipeline.py                   # thin orchestrator
│   └── evaluation/
│       ├── sampling.py               # stratified sampler (§5.1 protocol)
│       ├── negatives.py              # non-trivial negatives (§5.3)
│       ├── annotation.py             # GoldEdge/GoldStandard schemas + load/save
│       ├── kappa.py                  # Cohen's κ + 3-way agreement
│       ├── llm_judge.py              # Stage 4 LLM audit (Claude)
│       ├── metrics.py                # P/R/F1/ECE; reliability diagrams
│       ├── baseline.py               # Tier 2.1 single-model baseline
│       ├── calibration.py            # Tier 2.2 reliability diagrams
│       ├── overlap.py                # Tier 3.1
│       └── per_expert/               # eval_<expert>.py × 6
│
├── scripts/                          # thin CLI wrappers
│   ├── fetch_filings.py
│   ├── build_graph.py
│   ├── sample_for_annotation.py
│   ├── annotate_ui.py                # Streamlit annotation UI
│   ├── compute_kappa.py
│   ├── run_llm_audit.py
│   ├── run_eval.py
│   ├── run_baseline.py
│   ├── run_calibration.py
│   └── reproduce.sh                  # end-to-end re-run
│
├── data/                             # DVC-tracked, NOT in git
│   ├── raw/<filing>/                 # downloaded HTML + XBRL
│   ├── parsed/<filing>/nodes.jsonl
│   ├── embeddings/<filing>/embeddings.npz
│   ├── graph/                        # edges.jsonl + Neo4j dump
│   └── baseline/edges.jsonl          # baseline pipeline output
│
├── annotations/                      # IN git (small, paper-critical)
│   ├── candidates/<expert>/*.jsonl   # sampled pairs, no labels yet
│   ├── dev/<expert>/*.jsonl          # held-out dev set for prompt tuning
│   └── test/<expert>/                # locked gold standard
│       ├── template.jsonl            # locked candidate set
│       ├── template_a.jsonl          # annotator A's labels
│       ├── template_b.jsonl          # annotator B's labels
│       ├── tiebreaker.jsonl          # annotator C resolutions
│       ├── llm_audit.jsonl           # Stage 4 LLM judgments
│       ├── consensus.jsonl           # final gold (post-tiebreak)
│       └── kappa_report.json
│
├── results/                          # IN git; matches spec §8 exactly
│   ├── per_expert_metrics.json       # Tier 1.1
│   ├── llm_ablation.json             # Tier 1.2
│   ├── graph_statistics.json         # Tier 1.3
│   ├── single_llm_baseline.json      # Tier 2.1
│   ├── calibration.json              # Tier 2.2 (data)
│   ├── calibration_diagrams.png      # Tier 2.2 (figure, 6-panel)
│   ├── overlap_analysis.json         # Tier 3.1
│   ├── alt_llm_robustness.json       # Tier 3.2
│   ├── microsoft_spotcheck.json      # Tier 3.3
│   ├── moe_compute.json              # NEW — token/wallclock for cost-vs-quality framing
│   ├── all_tables.csv                # combined for paper Tables 2–4
│   └── notes.md                      # narrative summary of surprises
│
├── docs/
│   ├── design.md                     # this design spec (copied in)
│   ├── annotation_guidelines.md      # for annotators (paper appendix material)
│   └── reproducibility.md            # how to re-run from scratch
│
└── tests/
    ├── test_imports.py               # zero-dependency-leak check
    ├── test_experts/                 # one test per expert
    ├── test_evaluation/              # κ, ECE, sampling stratification
    ├── test_pipeline/                # end-to-end on a 1-filing fixture
    └── fixtures/                     # synthetic gold standards for harness tests
```

**Key decisions:**

- `src/moe_graph/` is the importable package; replaces the existing repo's `src/`.
- `annotations/` is in git (small, paper-critical, version-controlled with diffs); `data/` is in DVC (large, reproducible from the SEC + `dvc.lock`).
- Per-expert evaluator modules in `evaluation/per_expert/` keep each ≤200 lines and independently testable.
- `scripts/` are thin wrappers; logic lives in `src/moe_graph/` so it is importable and testable.

**Explicitly NOT carried over from the existing repo:**

- `src/opmech/*` (28 files — the commutator paper)
- `src/core/unified_*.py`, `src/core/integrated_system.py`, `src/core/ground_truth_injector.py` (commutator/MoE entanglement)
- `src/processing/*` (answer synthesis — Paper B)
- `src/api/*`, `dashboard/`, `frontend/` (runtime serving)
- `run_analysis_queries.py`, `start_demo.sh`, `query_results.json`, `strategic_analysis_results.json` (demo artefacts)
- The four giant `.docx` planning docs in `docs/` (kept in Repo Original; not in Repo A)

---

## 2. DVC pipeline stages

The pipeline has **20 DVC stages** plus **two manual gates** where humans must commit annotations before downstream stages run.

### Stage DAG

```
                                params.yaml
                                     |
                                     v
[fetch] -> [parse] -> [embed] -> [graph_build] -> [graph_stats]   (Tier 1.3)
                |        |             |
                |        |             +--> [sample_candidates]
                |        |                       |
                |        |                       +--> [sample_negatives]
                |        |                                |
                |        |                                +--> [dev_split]
                |        |                                        |
                |        |                            -------- (MANUAL GATE) -----------
                |        |                            |   human annotation: A, B, C   |
                |        |                            ----------------+----------------
                |        |                                            |
                |        |                                            v
                |        |                                       [kappa] -> [consensus]
                |        |                                                       |
                |        |                                                       +--> [llm_audit]
                |        |                                                       |
                |        |                                                       v
                |        |                                              +-- [eval_per_expert]   (Tier 1.1)
                |        |                                              +-- [eval_ablation]     (Tier 1.2)
                |        |                                              +-- [calibration]       (Tier 2.2)
                |        |                                              +-- [overlap]           (Tier 3.1)
                |        +--> [baseline_run] -> [eval_baseline]                                 (Tier 2.1)
                +-----> [alt_llm_run]   -> [eval_alt_llm]                                       (Tier 3.2)
                +-----> [msft_run]      -> [eval_msft]                                          (Tier 3.3)
                                                          \
                                                           v
                                                     [aggregate_tables]
```

### Stages in detail

| # | Stage | Depends on | Produces | Tier |
|---|---|---|---|---|
| 1 | `fetch` | `params.yaml:filings` | `data/raw/<filing>/` | — |
| 2 | `parse` | `data/raw/` | `data/parsed/<filing>/nodes.jsonl` | — |
| 3 | `embed` | `data/parsed/` | `data/embeddings/<filing>/embeddings.npz` | — |
| 4 | `graph_build` | parsed + embed + `params.yaml:experts` | `data/graph/edges.jsonl`, Neo4j dump | — |
| 5 | `graph_stats` | `data/graph/` | `results/graph_statistics.json` | **1.3** |
| 6 | `sample_candidates` | parsed + graph | `annotations/candidates/<expert>/*.jsonl` | — |
| 7 | `sample_negatives` | parsed + graph + candidates | merged into candidate files | — |
| 8 | `dev_split` | candidates | `annotations/dev/<expert>/template.jsonl` (15%) + `annotations/test/<expert>/template.jsonl` | — |
| ⊗ | **MANUAL GATE 1** | dev split | annotators iterate on prompts using dev only | — |
| ⊗ | **MANUAL GATE 2** | test template | `template_a.jsonl`, `template_b.jsonl`, `tiebreaker.jsonl` filled in | — |
| 9 | `kappa` | A + B templates | `kappa_report.json` | (paper appendix) |
| 10 | `consensus` | A + B + tiebreaker | `consensus.jsonl` | — |
| 11 | `llm_audit` | consensus + parsed text | `llm_audit.jsonl` | (paper appendix) |
| 12 | `eval_per_expert` | consensus + graph | `results/per_expert_metrics.json` | **1.1** |
| 13 | `eval_ablation` | consensus + parsed + 2 expert configs | `results/llm_ablation.json` | **1.2** |
| 14 | `baseline_run` | parsed + `params.yaml:baseline_prompt` | `data/baseline/edges.jsonl` | — |
| 15 | `eval_baseline` | baseline + consensus | `results/single_llm_baseline.json` | **2.1** |
| 16 | `calibration` | per-expert predictions + consensus | `results/calibration_diagrams.png` + ECE | **2.2** |
| 17 | `overlap` | graph | `results/overlap_analysis.json` | **3.1** |
| 18 | `alt_llm_run` + `eval_alt_llm` | parsed (subset) + alt model | `results/alt_llm_robustness.json` | **3.2** |
| 19 | `msft_run` + `eval_msft` | new MSFT FY2024 raw | `results/microsoft_spotcheck.json` | **3.3** |
| 20 | `aggregate_tables` | all `results/*.json` | `results/all_tables.csv` | — |

### How manual gates work in DVC

Annotation files (`template_a.jsonl` etc.) live in **git, not DVC**. When humans commit completed annotations, `dvc repro` sees that downstream stages now have all their inputs and runs them. Before that, those stages block with a "missing inputs" message — which is the correct behaviour.

### Param-file unification

`params.yaml` is the single source of truth for: model IDs, prompt versions, expert thresholds, sampling sizes, random seed, filing list, baseline prompt. Every script reads from it via `pydantic-settings`. Changing a hyperparameter and reproducing is one git diff plus `dvc repro`.

---

## 3. Core components (build side)

### `src/moe_graph/config.py`

Pydantic-settings model loading `params.yaml` + env vars. Replaces existing `src/config.py` and `src/company_config.py` (most of the latter is OpMech-specific company config and is not carried over). Single import: `from moe_graph.config import settings`.

### `src/moe_graph/models.py`

`Node`, `Edge`, `EdgeType`, `NodeType`, `FilingMetadata` — Pydantic. Copied from existing `src/models.py`. Every `Edge` carries `confidence: float ∈ [0, 1]` and `evidence_quote: str | None` — required for ECE and reviewer trust.

### `src/moe_graph/llm_client.py` — two classes, two concerns

**`SystemLLMClient`** — Qwen3-14B via vLLM. Used by experts.

- Constructor: `vllm_endpoint`, `model_id="Qwen/Qwen3-14B"`, default sampling params.
- Methods: `generate(prompt, max_tokens, temperature)`, plus typed helpers (`extract_temporal_links()`, `extract_semantic_relationships()`, `extract_causal_chain()`, `extract_table_text_link()`, `extract_cross_reference()`).
- Uses `transformers.AutoTokenizer.apply_chat_template()` for Qwen3-14B's chat format.

**`JudgeLLMClient`** — Anthropic Claude via API. Used only by Stage 4 audit.

- Constructor: `api_key`, `model_id="claude-sonnet-4-6"`, `temperature=0.0`.
- Method: `audit_label(pair, human_label) -> AuditResult`.

**Import-graph isolation** (enforced by `tests/test_imports.py`): `evaluation/llm_judge.py` may only import `JudgeLLMClient`; `experts/*` may only import `SystemLLMClient`. The judge model and the system-under-test model are different families by design.

### `src/moe_graph/ingestion/`

`sec_fetcher.py`, `html_parser.py`, `xbrl_processor.py` — copied from existing repo. No commutator entanglement.

### `src/moe_graph/embedding/`

`embedding_engine.py` — FinBERT on each node's text → 768-dim vectors. Copied from existing.

### `src/moe_graph/experts/`

**`base.py` — the Expert contract:**

```python
class Expert(ABC):
    name: str                                 # e.g., "CausalChainBuilder"
    edge_types: list[EdgeType]                # one or more
    supports_llm: bool                        # True for 5 of 6
    use_llm: bool                             # mode toggle for Tier 1.2 ablation

    @abstractmethod
    def discover_edges(
        self,
        nodes: list[Node],
        embeddings: dict[str, np.ndarray],
    ) -> list[Edge]:
        # MUST set Edge.confidence ∈ [0, 1]
        ...
```

This contract is load-bearing for Tier 1.2: switching `use_llm` at construction time produces directly comparable edge sets on identical inputs.

**Six experts** (copied from existing, audited for clean imports + working `use_llm` toggle + meaningful confidence distributions):

| Expert | Edge type(s) | LLM-capable? |
|---|---|---|
| `EntityExtractor` | `MENTIONS_ENTITY`, `ENTITY_RELATED_TO` | No |
| `CrossReferenceHunter` | `REFERS_TO` | Yes |
| `CausalChainBuilder` | `CAUSED_BY`, `LEADS_TO` | Yes |
| `TemporalLinker` | `TEMPORAL_NEXT` | Yes |
| `TableTextConnector` | `EXPLAINS_LINE_ITEM`, `DISCUSSES` | Yes |
| `SemanticBridge` | `SEMANTICALLY_SIMILAR` | Yes |

EntityExtractor still receives a Tier 1.1 gold standard (P/R/F1/ECE) — it just does not appear in the Tier 1.2 LLM ablation table.

### `src/moe_graph/graph/`

- `neo4j_client.py` — async Neo4j driver wrapper. Copied.
- `builder.py` — runs all experts, deduplicates overlapping edges (max-confidence), batch-loads to Neo4j. Light edits to remove any commutator-aware paths.
- `connectivity.py` — bridge-edge detection + connected-component analysis. Copied.

### `src/moe_graph/pipeline.py` (NEW)

Thin orchestrator (~120 lines) replacing the entangled `src/core/unified_pipeline.py`:

```python
def run_pipeline(filings: list[FilingSpec], use_llm: bool = True) -> GraphRunResult:
    raw    = fetch_all(filings)
    parsed = parse_all(raw)
    emb    = embed_all(parsed)
    edges  = run_experts(parsed, emb, use_llm=use_llm)
    load_to_neo4j(edges)
    return GraphRunResult(...)
```

The top-level `use_llm` flag drives both ablation modes for Tier 1.2 — same inputs, two runs, two comparable graphs.

---

## 4. Evaluation harness

### `evaluation/sampling.py` — stratified candidate sampling (§5.1)

Stratifies on three dimensions simultaneously: **edge type × confidence bucket × filing source**. Confidence buckets: `high>0.80`, `medium 0.60–0.80`, `low<0.60`. At least 3 distinct filings per stratum (fail-fast otherwise).

For EntityExtractor: strata are `(edge_type ∈ {MENTIONS_ENTITY, ENTITY_RELATED_TO}) × confidence_bucket × filing` — same shape, different edge types.

### `evaluation/negatives.py` — non-trivial negatives (§5.3)

Two negative classes per spec, equal counts, labelled by class:

- **Class A — Co-located but unconnected**: pairs `(u, v)` not connected by this expert, but sharing the same filing AND (same section OR same named entity).
- **Class B — Type-confused**: pairs `(u, v)` connected by a *different* expert with a *different* edge type. Tests type discrimination.

### `evaluation/annotation.py` — schemas, dev/test split

```python
class CandidatePair(BaseModel):
    pair_id: str                 # stable hash(source_id, target_id, edge_type)
    source_id: str
    target_id: str
    edge_type: EdgeType
    proposed_confidence: float
    proposed_evidence: str | None
    source_text: str             # truncated to 500 chars
    target_text: str
    negative_class: Literal["positive", "co_located", "type_confused"] | None
    stratum: dict

class Annotation(BaseModel):
    pair_id: str
    label: bool
    annotator: str               # "A", "B", "C", or "llm_judge"
    confidence: float | None     # 1–5 self-reported (optional)
    notes: str | None
    timestamp: datetime
```

Templates are `*.jsonl`, one Annotation per line. The deterministic `pair_id` is the join key across all annotation files.

**Dev/test split**: 15% per expert as dev. Dev annotated by you only; used for prompt iteration. **Once test annotation begins, prompts are frozen** (`params.yaml:prompt_version`). Re-tuning prompts after that requires regenerating dev/test split with a new seed.

### `evaluation/kappa.py` — agreement statistics

- **Cohen's κ** between A and B per expert.
- **Three-way Fleiss' κ** (A, B, tiebreaker) for the appendix.
- Threshold: κ < 0.7 emits a yellow warning; κ < 0.6 emits a red error and recommends re-annotation.

### `evaluation/llm_judge.py` — Stage 4 audit (Anthropic API)

Calls `JudgeLLMClient` (Claude Sonnet 4.6) over `consensus.jsonl`. For each pair, shows source/target text, edge type, human label, asks: "Do you agree? Output JSON with `agree`, `confidence`, `reasoning`."

The LLM does **not** override consensus. Its agreement rate (per expert) is reported in the appendix as a robustness check. If LLM-human agreement is <80% on any expert, that's a signal the binary question for that edge type may be ambiguous and needs a §discussion paragraph.

### `evaluation/metrics.py` — deterministic metric core

```python
def compute_metrics(predicted_edges, gold) -> ExpertMetrics:
    # Join by pair_id. Returns:
    # precision, recall, f1, ece, tp, fp, fn, tn, sample_n, n_strata
    # plus per-stratum breakdowns
```

- ECE uses 10 confidence bins per spec §5.4.
- All metrics also computed per stratum so the paper can report "low-confidence-bucket precision" separately.

### `evaluation/per_expert/eval_<expert>.py` — six modules

Each module:

1. Loads `annotations/test/<expert>/consensus.jsonl`.
2. Loads predicted edges from `data/graph/edges.jsonl` filtered to this expert's edge types.
3. For LLM-capable experts: also loads from a second graph build with `use_llm=False`.
4. Calls `compute_metrics()` and writes one record into `results/per_expert_metrics.json`.

EntityExtractor: one mode, one row, no `llm_ablation.json` entry. The 5 LLM-capable experts: two rows in `per_expert_metrics.json` (one per mode) plus one row in `llm_ablation.json` carrying ΔP/ΔR/ΔF1/Δedges.

### `evaluation/baseline.py` — Tier 2.1 single-model baseline

See Section 6 below.

### `evaluation/calibration.py` — Tier 2.2 reliability diagrams

Per expert (LLM-on mode), bin predicted-positive edges by confidence (10 bins), compute observed precision per bin, plot expected-vs-observed on a 6-panel matplotlib figure → `results/calibration_diagrams.png` at 300 DPI.

### `evaluation/overlap.py` — Tier 3.1

For each unordered node pair, count how many distinct experts produced an edge. Histogram + complementary-vs-redundant analysis. Goes into `results/overlap_analysis.json`.

### Module dependency graph

```
sampling.py    -> annotation.py
negatives.py   -> sampling.py + annotation.py
kappa.py       -> annotation.py
llm_judge.py   -> annotation.py + ../llm_client.py(JudgeLLMClient)
metrics.py     -> annotation.py + ../models.py
calibration.py -> metrics.py
baseline.py    -> ../llm_client.py(SystemLLMClient) + metrics.py
overlap.py     -> ../graph/builder.py output (edges.jsonl)
per_expert/eval_*.py -> metrics.py + annotation.py
```

No `evaluation/` module imports from `experts/` directly. Evaluation works on edge artefacts (`edges.jsonl`), not on running expert objects.

---

## 5. Annotation workflow

### Phase 0 — Build, sample, dev split

`dvc repro graph_build sample_candidates sample_negatives dev_split`. Produces `annotations/candidates/<expert>/all_pairs.jsonl`, `annotations/dev/<expert>/template.jsonl`, `annotations/test/<expert>/template.jsonl`.

### Phase 1 — Prompt iteration on dev set (you only)

You annotate the dev set. Iterate prompts on the 5 LLM-capable experts; track each version in `params.yaml:prompts.<expert>.version` and `prompt_version: N` (global). Dev metrics tracked in `results/dev_metrics_history.json`.

### Phase 2 — Lock prompts and freeze test template

```
git tag prompts-frozen-v1
git commit -am "Freeze prompts at version N before test annotation"
```

After this commit, changing any prompt invalidates the test set. Enforced socially and technically: `scripts/run_eval.py` aborts if `params.yaml:prompt_version` mismatches `data/graph/edges.jsonl` metadata.

### Phase 3 — Annotation tooling

**Streamlit UI** (`scripts/annotate_ui.py`): one pair at a time, source + target text + edge-type-specific question, Y/N/?/skip keyboard shortcuts, auto-save on each keypress, progress bar, mandatory 5-min break every 100 judgments. ~150 LOC. Built before annotation begins.

JSONL-only fallback supported but UI is the default.

### Phase 4 — Annotation guidelines per edge type

`docs/annotation_guidelines.md` (paper appendix material). One page per expert with:

- The binary question, phrased identically for each annotator. Examples:
  - **CrossReferenceHunter**: "Does the SOURCE text explicitly reference the TARGET note (e.g., 'See Note 3', 'refer to Note X')?"
  - **CausalChainBuilder**: "Does the SOURCE text describe a cause whose effect is described in the TARGET text, supported by linguistic evidence (e.g., 'because', 'due to', 'resulted in')?"
  - **TemporalLinker**: "Do the SOURCE and TARGET texts describe the same financial item, event, or trend across consecutive reporting periods?"
  - **TableTextConnector**: "Does the SOURCE text discuss, explain, or directly reference the specific data point or row in the TARGET table?"
  - **SemanticBridge**: "Are the SOURCE and TARGET texts about the same topic at a level of similarity that would make co-retrieval useful for answering a question about either?"
  - **EntityExtractor**: "Is the entity (TARGET) correctly identified in the SOURCE text — i.e., does the source mention this exact entity (not a near-match or partial substring)?"
- Three worked examples per edge type (one clear `True`, one clear `False`, one borderline).
- Borderline rule: when uncertain, mark `False` and add `notes`. Tiebreaker has explicit responsibility for borderlines.

### Phase 5 — Three-stage human annotation

**Stage 1 — A and B in parallel, no communication**:
```
scripts/annotate_ui.py --annotator A --expert <name>
scripts/annotate_ui.py --annotator B --expert <name>
```

**Stage 2 — Cohen's κ check**: `dvc repro kappa`. Halt if any κ<0.6.

**Stage 3 — Tiebreaker (annotator C)** resolves disagreed pairs only:
```
scripts/annotate_ui.py --annotator C --tiebreaker --expert <name>
```

**Consensus build**: `dvc repro consensus` → `annotations/test/<expert>/consensus.jsonl`. **This is the gold standard.**

### Phase 6 — Stage 4 LLM audit

`dvc repro llm_audit` runs `JudgeLLMClient` (Claude Sonnet 4.6) over `consensus.jsonl`. Outputs `llm_audit.jsonl`. Reported in appendix as a robustness check; does not override human consensus.

### Phase 7 — Frozen artefacts

After Phase 6, all of `annotations/test/<expert>/{template,template_a,template_b,tiebreaker,consensus,llm_audit,kappa_report}.{jsonl,json}` are committed to git and never modified without a documented re-annotation event.

### Time estimate per annotator

- ~150 pairs × 6 experts = ~900 pairs each for A and B at ~30 sec/pair → **~7.5 hours per annotator**.
- Tiebreaker: ~30% disagreement at κ ≈ 0.7 → ~270 pairs × 60 sec → **~4.5 hours**.

---

## 6. Single-model LLM baseline (Tier 2.1)

The comparison the paper rises or falls on. Designed to be scrupulously fair so a positive MoE result is credible.

### Fairness rules (non-negotiable)

The MoE pipeline and the baseline differ on **exactly one variable: extraction strategy**. Everything else is held identical:

| Held identical | Both pipelines |
|---|---|
| Model | Qwen3-14B (vLLM, FP8) — same instance, same checkpoint |
| Sampling params | `temperature=0.1, top_p=0.95, max_tokens=1024` |
| Input chunking | FinBERT chunker → `nodes.jsonl` |
| Filings | 12 Apple SEC filings |
| Gold standard | `consensus.jsonl` per expert |
| Hardware | RTX 5090, same GPU run |
| **Differs**: extraction prompt | 6 specialised prompts vs. 1 unified prompt |

Enforced via DVC: `baseline_run` and `graph_build` depend on the same `params.yaml:model_id` field.

### Implementation choices

1. **Chunk granularity**: same chunks as MoE pipeline. No "whole-document" advantage. Shared `evaluation/baseline.py:build_chunks()`.
2. **Entity resolution**: baseline emits `(source_text, target_text, relation_type)` tuples; we resolve to existing Node IDs via fuzzy text matching (Jaccard on token sets, threshold 0.7). Mild advantage for the baseline (no entity-resolution work required) — flagged explicitly in the paper.
3. **Tolerant JSON parsing**: handles bare arrays, markdown-fenced JSON, single-quoted JSON, partial trailing arrays. Parse failures logged in `results/baseline_parse_failures.jsonl`. No retries — same one-shot budget as each expert.
4. **Confidence scores**: prompt asks for `confidence ∈ [0, 1]` per edge. Used directly for ECE on the baseline.

### The unified prompt (frozen, paper-appendix-ready)

```
You are extracting a typed knowledge graph from a SEC filing chunk.
Identify all directly-stated relationships between entities and concepts
present in the chunk. Output a JSON array of objects with fields:
  source, target, relation_type, evidence_quote, confidence (0–1).
Allowed relation types:
  REFERS_TO, CAUSED_BY, LEADS_TO, TEMPORAL_NEXT, EXPLAINS_LINE_ITEM,
  DISCUSSES, SEMANTICALLY_SIMILAR, MENTIONS_ENTITY, ENTITY_RELATED_TO.
Return [] if no relationships are clearly stated.

CHUNK:
{chunk}
```

Versioned via `params.yaml:baseline_prompt_version`. Frozen at the same checkpoint as the expert prompts.

### Scoring

Same `consensus.jsonl` per expert, split by edge type. Output `results/single_llm_baseline.json` with overall + per-edge-type breakdown + compute block (calls, tokens, wall time, parse failures).

### Risk planning (per Claude Chat 1 §"One honest note")

If baseline F1 ≈ MoE F1, the paper framing pivots — pre-planned:

- **Primary contribution if MoE wins clearly (≥5pt F1)**: edge-type specialisation produces measurably higher-quality knowledge graphs.
- **Backup contribution if MoE wins narrowly (<5pt) or loses**: per-edge-type confidence calibration + modular debugging + per-expert ablation transparency. Paper becomes an interpretability + engineering contribution.

The empirical work answers the question either way.

### Computational note

- MoE run: ~6 experts × ~12,000 chunks ≈ 72,000 LLM calls → ~6–10 hours with vLLM batching.
- Baseline run: ~12,000 chunks × 1 call → ~1–2 hours.
- Both fit in a single overnight run.

---

## 7. Output schemas and paper-table mapping

Every `results/*` file shape is locked here and tested in `tests/test_evaluation/test_output_schemas.py`.

### `results/per_expert_metrics.json` (Tier 1.1, Table 2)

```json
{
  "metadata": {
    "evaluation_date": "...",
    "model_id": "Qwen/Qwen3-14B",
    "prompt_version": 3,
    "seed": 42,
    "graph_run_id": "sha256:..."
  },
  "experts": {
    "EntityExtractor": {
      "mode": "rule_only",
      "edge_types": ["MENTIONS_ENTITY", "ENTITY_RELATED_TO"],
      "precision": 0.0, "recall": 0.0, "f1": 0.0, "ece": 0.0,
      "sample_n": 150, "tp": 0, "fp": 0, "fn": 0, "tn": 0,
      "by_stratum": { "high_conf": {...}, "med_conf": {...}, "low_conf": {...} },
      "kappa": 0.0, "llm_audit_agreement": 0.0,
      "gold_standard_path": "annotations/test/EntityExtractor/consensus.jsonl",
      "notes": ""
    },
    "CrossReferenceHunter_with_llm":   {...},
    "CrossReferenceHunter_without_llm":{...},
    "CausalChainBuilder_with_llm":     {...},
    "CausalChainBuilder_without_llm":  {...},
    "TemporalLinker_with_llm":         {...},
    "TemporalLinker_without_llm":      {...},
    "TableTextConnector_with_llm":     {...},
    "TableTextConnector_without_llm":  {...},
    "SemanticBridge_with_llm":         {...},
    "SemanticBridge_without_llm":      {...}
  }
}
```

→ 11 rows: 1 Entity + 5 LLM-capable × 2 modes. Maps to **Table 2**.

### `results/llm_ablation.json` (Tier 1.2, Table 3)

```json
{
  "metadata": {...},
  "ablations": {
    "CrossReferenceHunter": {
      "rule_only":     {"precision": ..., "recall": ..., "f1": ..., "n_edges_total": ...},
      "with_llm":      {"precision": ..., "recall": ..., "f1": ..., "n_edges_total": ...},
      "delta": {"delta_precision": 0.0, "delta_recall": 0.0, "delta_f1": 0.0, "delta_edges": 0}
    },
    "CausalChainBuilder": {...},
    "TemporalLinker":     {...},
    "TableTextConnector": {...},
    "SemanticBridge":     {...}
  }
}
```

→ 5 experts × 2 modes + 5 deltas. Maps to **Table 3**. The "10× CausalChainBuilder" claim, if real, surfaces as `delta_edges` on Causal.

### `results/graph_statistics.json` (Tier 1.3)

```json
{
  "metadata": {...},
  "global": {
    "total_nodes": 0,
    "total_edges": 0,
    "edges_by_type": {"REFERS_TO": 0, ...},
    "edges_by_expert": {"EntityExtractor": 0, ...},
    "connected_components": 0,
    "largest_component_size": 0,
    "bridge_edges": 0,
    "avg_degree": 0.0,
    "max_degree": 0,
    "median_degree": 0.0,
    "confidence_distribution": {"bins": [...], "counts": [...]}
  },
  "per_filing": {"AAPL-10-K-FY2024": {...}, "...": "..."}
}
```

### `results/single_llm_baseline.json` (Tier 2.1, Table 4)

```json
{
  "overall": {"precision": 0.0, "recall": 0.0, "f1": 0.0, "ece": 0.0, "n_edges": 0},
  "per_edge_type": {
    "REFERS_TO":            {"precision": ..., "recall": ..., "f1": ..., "n_edges": ...},
    "CAUSED_BY":            {...},
    "TEMPORAL_NEXT":        {...},
    "DISCUSSES":            {...},
    "SEMANTICALLY_SIMILAR": {...},
    "MENTIONS_ENTITY":      {...},
    "ENTITY_RELATED_TO":    {...}
  },
  "compute": {
    "n_llm_calls": 0,
    "total_input_tokens": 0,
    "total_output_tokens": 0,
    "wall_time_seconds": 0.0,
    "parse_failures": 0
  },
  "model_id": "Qwen/Qwen3-14B",
  "prompt_version": 1,
  "evaluation_date": "..."
}
```

### `results/calibration.json` + `results/calibration_diagrams.png` (Tier 2.2)

```json
{
  "metadata": {...},
  "experts": {
    "CrossReferenceHunter": {
      "ece": 0.0,
      "bins": [
        {"conf_min": 0.0, "conf_max": 0.1, "predicted_conf": 0.05, "observed_precision": 0.0, "n": 0},
        ... (10 bins)
      ]
    },
    "...": "..."
  }
}
```

PNG: 6-panel matplotlib figure, x = predicted confidence, y = observed precision, identity diagonal. Per-expert ECE annotated.

### `results/overlap_analysis.json` (Tier 3.1)

```json
{
  "summary": {
    "n_node_pairs_with_edges": 0,
    "pct_pairs_with_one_expert": 0.0,
    "pct_pairs_with_two_plus_experts": 0.0
  },
  "expert_pair_overlap": {
    "CausalChainBuilder__SemanticBridge": {"n_shared_pairs": 0, "jaccard": 0.0},
    "...": "..."
  },
  "interpretation": "..."
}
```

### `results/alt_llm_robustness.json` (Tier 3.2)

```json
{
  "subset_size": 50,
  "results": {
    "Qwen3-14B (primary)": {"f1": 0.0, "n_edges": 0},
    "Llama-3.1-8B-Instruct": {"f1": 0.0, "n_edges": 0}
  },
  "f1_correlation": 0.0,
  "interpretation": "..."
}
```

### `results/microsoft_spotcheck.json` (Tier 3.3)

```json
{
  "filing": "MSFT-10-K-FY2024",
  "structural_results": {"n_nodes": 0, "n_edges": 0, "edges_by_type": {...}, "components": 0, "bridges": 0},
  "comparison_to_apple": {"comment": "...", "metrics": {...}},
  "completed_without_errors": true,
  "interpretation": "anecdotal generalisation evidence"
}
```

### `results/moe_compute.json` (NEW)

```json
{
  "moe_pipeline": {
    "n_llm_calls": 0,
    "total_input_tokens": 0,
    "total_output_tokens": 0,
    "wall_time_seconds": 0.0,
    "by_expert": {"CausalChainBuilder": {"n_calls": 0, "tokens_in": 0, "tokens_out": 0, "wall_s": 0.0}, "...": "..."}
  }
}
```

### `results/all_tables.csv`

```csv
table,row_label,metric,value
table_2,EntityExtractor,precision,0.85
table_2,EntityExtractor,recall,0.78
...
table_3,CausalChainBuilder,delta_f1,0.12
...
table_4,baseline_overall,f1,0.42
table_4,moe_overall,f1,0.61
```

### Paper-table → results-file mapping

| Paper section | Paper artefact | Source file | Field |
|---|---|---|---|
| §4 Method | Table 1 (architecture) | hand-written | — |
| §5 Results — quality | **Table 2** | `per_expert_metrics.json` | each expert's metrics |
| §5 Results — ablation | **Table 3** | `llm_ablation.json` | each expert's deltas |
| §5 Results — graph | section text | `graph_statistics.json` | global stats |
| §6 Comparison | **Table 4** | `single_llm_baseline.json` | per-edge-type + overall |
| §7 Calibration | **Figure 1** | `calibration_diagrams.png` | + per-expert ECE |
| §8 Discussion — overlap | text + small table | `overlap_analysis.json` | summary |
| §8 Discussion — robustness | text | `alt_llm_robustness.json` | f1_correlation |
| §8 Discussion — generalisation | text | `microsoft_spotcheck.json` | structural comparison |
| Appendix A — gold standard | table + κ | `kappa_report.json` per expert | κ values, LLM audit % |
| Appendix B — compute | table | `moe_compute.json` + baseline compute | tokens, wall time |
| Appendix C — reproducibility | text + listings | `dvc.lock`, `params.yaml` | hashes, settings |

---

## 8. Risk register and mitigations

### Tier 0 — Existential

| # | Risk | Likelihood | Impact | Mitigation | Trigger |
|---|---|---|---|---|---|
| R1 | Inter-annotator κ < 0.6 on one or more experts | Medium | High | Annotation guidelines with three worked examples per edge type; pilot 20 pairs per expert before full annotation; halt on κ<0.6 and revise | `kappa_report.json` shows κ<0.6 |
| R2 | Baseline (Tier 2.1) beats or matches MoE on overall F1 | Medium | High | Pre-planned framing pivot (§6): contribution becomes interpretability + calibration + modular debug, not raw F1 | `single_llm_baseline.json:overall.f1 ≥ moe overall f1 − 5pt` |
| R3 | Confidence scores are uniform | Low | High | Test (`tests/test_experts/test_confidence_distribution.py`): assert std(confidence) > 0.1 per expert | Test fails OR ECE undefined |

### Tier 1 — Schedule-killers

| # | Risk | Likelihood | Impact | Mitigation | Trigger |
|---|---|---|---|---|---|
| R4 | Cold-start data pipeline fails | High | Medium | Day-1 smoke test on 1 filing before scaling to 12; pinned versions; cached model downloads | Single-filing smoke test fails |
| R5 | Qwen3-14B prompt drift (existing prompts tuned for Qwen2.5-7B) | High | Medium | Phase 1 prompt iteration on dev set is already a phase; budget 2–3 days; track versions in `params.yaml` | Dev F1 < 0.4 on any expert after 1 day |
| R6 | Annotator dropout | Medium | High | A and B parallel; one named backup per role; LLM judge can serve as second annotator with appendix caveat if necessary | Annotator misses 2 consecutive checkpoints |
| R7 | vLLM OOM on 24GB | Medium | Medium | FinBERT on CPU during embedding; vLLM exclusive GPU during expert runs; fall back to AWQ-INT4 | Startup fails or latency >2× expected |

### Tier 2 — Quality issues

| # | Risk | Likelihood | Impact | Mitigation | Trigger |
|---|---|---|---|---|---|
| R8 | Bridge-edge count diverges from prior "2 bridges over 22,387 edges" claim | Medium | Medium | Don't pre-commit headline number; report measured number with run hash | `bridge_edges` differs by >2× from prior |
| R9 | LLM-judge disagrees with humans on >20% | Low | Low–Medium | Reported transparently; concentrate-on-one-expert flag → §discussion paragraph | <80% agreement for any expert |
| R10 | Calibration is poor (high ECE) | High (typical) | Medium | Frame as measured property; if ECE>0.15, recommend temperature scaling as future work | `ece > 0.15` for any expert |
| R11 | Microsoft spot-check fails | Medium | Low | Tier 3.3 explicitly anecdotal; drop with one-line limitations note | `completed_without_errors == false` |
| R12 | Overlap is high (>40% pairs covered by 2+ experts) | Low | Medium | Report honestly; argue high-confidence overlap is consensus, low-confidence is ablation | `pct_pairs_with_two_plus_experts > 0.4` |

### Tier 3 — Process risks

| # | Risk | Likelihood | Impact | Mitigation | Trigger |
|---|---|---|---|---|---|
| R13 | Prompt-frozen rule violation | Low | High | Technical enforcement: `params.yaml:prompt_version` written into `edges.jsonl` metadata; eval aborts on mismatch | Eval aborts with "prompt version mismatch" |
| R14 | DVC lock-file conflicts | Low | Low | Single-developer assumption; collaborator pulls `dvc.lock` first | Git merge conflict on `dvc.lock` |
| R15 | API rate limits / billing on Anthropic API | Low | Low | Exponential backoff; cost cap (`$50`) hardcoded in `run_llm_audit.py`; `ANTHROPIC_API_KEY` in `.env` | API 429 or projection > cap |
| R16 | Token budget exhausted on baseline | Medium | Low–Medium | `build_chunks()` splits chunks where `len(tokenize) > 4096`; parse-failure log surfaces in `single_llm_baseline.json` | `parse_failures > 5%` |

### Acknowledged limitations (paper §discussion)

- Generalisation beyond SEC filings: only Apple 10-Ks/10-Qs; MSFT spot-check is anecdotal.
- Single-language English-only.
- No GraphRAG / Microsoft-Azure baseline (deferred per spec §6.2).
- No fine-tuned NER+RE baseline (deferred per spec §6.2).
- Annotation pool size: 3 annotators per protocol; expanding to 5+ would tighten κ confidence intervals.

---

## 9. Phasing and execution sequence

Three parallel tracks: pipeline, annotation, engineering. Critical path runs through pipeline + annotation; engineering parallelises on top.

### Phase A — Repo bootstrap (Days 1–2)

- Initialise `OpMech_MoE_Graph/` per Section 1 layout.
- `pyproject.toml` (uv-managed, pinned), `pre-commit` (ruff, black, mypy).
- `docker-compose.yml` (Neo4j + vLLM with `Qwen/Qwen3-14B`).
- DVC initialised; empty `dvc.yaml` with stage stubs.
- `.env.example` with all required env vars.
- `params.yaml` populated.
- Migrate experts, ingestion, embedding, graph builder, models, config — imports adjusted to `moe_graph.*`.
- **Gate A**: `pytest -x` green on imports + toy expert test.

### Phase B — Cold-start data build (Days 3–6)

- Day 3: smoke test on 1 filing end-to-end.
- Day 4: scale to 12 filings (`dvc repro fetch parse embed`).
- Day 5: vLLM up; first `graph_build` with all 6 experts in LLM-on mode; `graph_stats`.
- Day 6: second `graph_build` with `use_llm=False`.
- **Gate B**: `graph_statistics.json` reasonable; no zero-edge experts; non-trivial confidence distributions.

### Phase C — Sampling and split (Day 7)

- `sample_candidates`, `sample_negatives`, `dev_split` for all 6 experts.
- Verify stratification: every expert's candidate file has all strata populated.
- Streamlit UI scaffolding committed.
- **Gate C**: candidate files exist with ≥100 pairs each; dev/test 15/85 split verified.

### Phase D — Prompt iteration on dev set (Days 8–11)

- You annotate `annotations/dev/<expert>/template.jsonl` for all 6 experts (~250 pairs total).
- Iterate prompts on the 5 LLM-capable experts. Track in `results/dev_metrics_history.json`.
- **Gate D**: dev F1 ≥ 0.5 on each LLM-capable expert; commit + tag `prompts-frozen-v1`.
- ⚠️ Lock-in: no prompt changes after this without re-sampling test set.

### Phase E — Test annotation by 3 humans + LLM audit (Days 12–22)

Long pole. Calendar-parallel with Phase F.

- Days 12–18: A and B work independently (~8 hours each, paced).
- Day 18: `dvc repro kappa` — first κ readout. **Gate E1**: κ ≥ 0.6 per expert.
- Days 19–20: Tiebreaker (C) resolves disagreed pairs (~250–300).
- Day 21: `dvc repro consensus llm_audit`.
- **Gate E2**: 6 × `consensus.jsonl` + 6 × `kappa_report.json` exist; LLM audit % captured.

### Phase F — Engineering parallel to annotation (Days 12–22)

While annotators work:

- `evaluation/per_expert/eval_*.py` × 6 — tested on synthetic fixtures.
- `evaluation/baseline.py` — tested on dev set first.
- `evaluation/calibration.py` — tested on synthetic predictions.
- `evaluation/overlap.py`.
- Refine `evaluation/llm_judge.py` for batch efficiency.
- Run `scripts/run_baseline.py` against all 12 filings (background, ~1–2 hours).
- Run alt-LLM (Tier 3.2) and MSFT (Tier 3.3) — schedulable any time after Phase B.
- **Gate F**: all `eval_*.py` modules pass synthetic-fixture tests; baseline + alt-LLM + MSFT runs complete.

### Phase G — Full evaluation run (Days 23–25)

- `dvc repro` from clean state — entire pipeline from `fetch` to `aggregate_tables`.
- All `results/*.json` populated.
- `results/calibration_diagrams.png` regenerated at 300 DPI.
- `results/all_tables.csv` aggregated.
- **Gate G**: every file from §7 exists; spot-check 3 expert-metric values match the per-expert run.

### Phase H — Results write-up + reproducibility check (Days 26–28)

- `results/notes.md` populated.
- `docs/reproducibility.md` written.
- `bash reproduce.sh` end-to-end test from a fresh clone.
- README updated.
- **Gate H**: clean-clone reproduction lands within ±1% on every metric in `per_expert_metrics.json`.

### Phase I — Buffer (Days 29+)

- Re-runs in response to paper-drafting feedback.
- Supplementary analyses.
- GitHub-readiness polish.

### Decision gates summary

| Gate | When | Pass criterion | Fail action |
|---|---|---|---|
| A | End of Day 2 | imports clean, smoke test green | fix imports/dependencies |
| B | End of Day 6 | graph stats reasonable, no zero-edge experts | inspect failing expert, re-run |
| C | End of Day 7 | candidate files populated with all strata | adjust sampling |
| D | End of Day 11 | dev F1 ≥ 0.5 + prompt freeze tagged | extend prompt iteration |
| E1 | Day 18 | κ ≥ 0.6 per expert | revise guidelines, re-annotate |
| E2 | Day 21 | gold standards + audits complete | recruit replacement annotator |
| F | Day 22 | all harness modules + baseline + alt-LLM + MSFT done | scope-cut Tier 3 |
| G | Day 25 | all results files populated | debug failing eval stage |
| H | Day 28 | clean-clone reproduction matches | fix non-determinism |

### Critical-path summary

Critical path: A → B → C → D → E1 → E2 → G → H. Annotation (Phase E) is the longest single phase. Engineering (Phase F) and the baseline run calendar-parallelise onto E without extending the critical path.

If we hit ~Day 22 with annotation still in progress, scope cuts in priority order: drop Tier 3.3 (MSFT) → drop Tier 3.2 (alt-LLM) → drop Tier 3.1 (overlap). Tier 1 + Tier 2 + calibration is the publishable floor.

---

## 10. Open questions deferred to implementation plan

These were raised during brainstorming and will be resolved in the writing-plans phase, not here:

1. **Per-expert sub-stages in DVC** (so `dvc repro -s eval_per_expert@causal` re-runs just one expert) — proposed in Section 2 review; user confirmed "looks good"; final shape decided when writing `dvc.yaml`.
2. **Streamlit UI feature set** — keyboard shortcuts, progress bar, break reminder all proposed; final UX decided when implementing.
3. **Alt-LLM choice for Tier 3.2** — `Llama-3.1-8B-Instruct` is the placeholder default; alternatives include `gemma-2-9b-it`, `mistral-nemo-12B`. Final pick based on what serves cleanly on the same vLLM instance.
4. **MSFT FY2024 fetch handling** — SEC EDGAR rate-limits and HTML-template differences may require parser tweaks; resolved during Phase B if encountered.
5. **Repo migration mechanics** — whether to use `git filter-repo` to extract history or start with a fresh `git init` for the new repo; defer to implementation. Likely fresh `git init` since the existing repo's history mixes both papers.

---

## 11. Sign-off

This design is committed to the existing `OpMech_GraphRag/` repo at `docs/superpowers/specs/2026-04-29-moe-graph-paper-design.md` as the source-of-truth for the implementation work. The new repo `OpMech_MoE_Graph/` will receive a copy at `docs/design.md` once it is initialised in Phase A.

— End of design spec —
