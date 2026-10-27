# Track B v1 — primary-source related work and novelty audit

CONVERSATION: Independent Track B literature and methodology review.
MODEL: GPT-6.1 Sol reasoning role, inherited task settings; no scientific model invocation.
EXECUTION TARGET: accepted source `effda0c053bf03723b8089bc331e6b152ef9ab31`, isolated Track B worktree; public papers/repositories through the web research tool.
JETSTREAM ACTION: NONE. No local browser, authenticated session, provider, SSH, infrastructure operation, or new scientific collection.

Research cutoff: October 26, 2026 local / October 27 UTC. Paper versions are explicit below. Public repository pages were read as mutable pages on that date; no exact repository checkout, dependency installation, experiment reproduction, or independent verification of their reported results was performed. This is a targeted nearest-neighbor literature audit, not an exhaustive systematic review. Search results and secondary summaries were discovery aids only. Mechanism claims below use primary full text/source; numerical results remain the authors' reports.

## Assessment

A broad contribution of “memory poisoning,” “retrieved is not authoritative,” signed provenance, origin-bound authority, cross-agent laundering, invalid-memory filtering, descendant revocation, or selective recovery would overlap established work. Cross-provider scope alone also overlaps existing empirical studies. These words do not establish novelty.

MEMO's defensible present contribution is an unusually explicit separation of native lifecycle observations, normalized authority/provenance, selected-context exposure, model proposals, authorization classification and actual execution, with attempt-scoped custody. Whether that separation discovers an additional failure mechanism or improves enforcement is still a hypothesis. The concrete partial-lineage and provider-metadata correlation counterexamples are measurement defects in MEMO, not evidence that a native provider or model is vulnerable.

## Primary-source comparisons

Each entry separates the paper's mechanism from a possible MEMO distinction. The latter is a research question, not a priority claim.

### 1. AgentPoison

**Zhaorun Chen, Zhen Xiang, Chaowei Xiao, Dawn Song, Bo Li (2024). _AgentPoison: Red-teaming LLM Agents via Poisoning Memory or Knowledge Bases_.** arXiv **2407.12784v1**, July 17, 2024; the [official repository](https://github.com/AI-secure/AgentPoison) identifies NeurIPS 2024. [Versioned paper](https://arxiv.org/html/2407.12784v1), especially §§3.2–3.3.

The attacker adds demonstrations to memory/KB and optimizes a query trigger so poisoned examples are retrieved and induce a chosen action. The objective separates retrieval, target generation and coherence; a white-box embedder is assumed for optimization, with transfer evaluated. This is stronger than merely inserting an arbitrary stale record, but it does not make revocation/reconstruction the treatment. MEMO should cite it for persistent retrieved-state influence. A lifecycle-authority comparison would need the same content and retrieval exposure while independently changing valid authority, rather than claiming a new poisoning attack from stale-text exposure.

### 2. MINJA

**Shen Dong, Shaochen Xu, Pengfei He, Yige Li, Jiliang Tang, Tianming Liu, Hui Liu, Zhen Xiang (2025; revised 2026). _Memory Injection Attacks on LLM Agents via Query-Only Interaction_.** arXiv **2503.03704v5**, February 12, 2026; first submission March 5, 2025 used the title _A Practical Memory Injection Attack against LLM Agents_. [Metadata](https://arxiv.org/abs/2503.03704), [versioned full text](https://arxiv.org/html/2503.03704v5), §§3–4.

MINJA removes direct attacker access to the memory bank. Ordinary interaction induces stored malicious reasoning, using bridging steps and progressively shortening indication prompts until a victim-like query retrieves it. The important distinction is attacker write authority versus an agent performing the eventual write. A signature from the writer is therefore insufficient proof of the originating claim's authority. MEMO has not run MINJA by exposing historical defender-authored policy, and should not compare ASRs across these different threat models.

### 3. CaMeL

**Edoardo Debenedetti, Ilia Shumailov, Tianqi Fan, Jamie Hayes, Nicholas Carlini, Daniel Fabian, Christoph Kern, Chongyang Shi, Andreas Terzis, Florian Tramèr (2025). _Defeating Prompt Injections by Design_.** arXiv **2503.18813v2**, June 24, 2025; first submitted March 24. [Paper](https://arxiv.org/html/2503.18813v2), §§3, 5; [official source](https://github.com/google-research/camel-prompt-injection).

A privileged planner generates a program from the trusted request; a quarantined model processes untrusted data. A custom interpreter propagates dependencies/capabilities and checks policies at tool calls. This is executable mediation, not a prompt instruction or retrospective ACL scorer. Its data-flow modes and error handling matter; the paper says side-effect sequences lack atomicity/rollback. The source warns that the research interpreter may contain security bugs. MEMO must compare an actual enforced boundary with this mechanism, including alternate paths and state reuse; a pure proposal classifier is a different outcome.

### 4. MemLineage

**Ciyan Ouyang, Rui Hou (2026). _MemLineage: Lineage-Guided Enforcement for LLM Agent Memory_.** arXiv **2605.14421v1**, May 14. [Paper](https://arxiv.org/html/2605.14421v1), §§3, 5–6, 8.

Signed entries and a Merkle log protect integrity; a weighted derivation DAG carries ancestor trust to a sensitive-action gate. The persistence guarantee requires sufficiently strong recorded attribution edges. Its deterministic isolation harness and model-backed evaluations are explicitly different. It reports all-zero undefended cells in one strong-model setting and uses a separately disclosed vulnerable profile to stress the enforcement mechanism. Recovery/authority-repair examples are also discussed. MEMO cannot claim that lineage propagation, derived-entry coverage, or separating model refusal from gate efficacy is new. A distinct result might concern native lineage availability and loss across a real provider interface, rather than assuming the attribution DAG exists.

### 5. Non-malleable origin-bound authority / TMA-NM

**Yedidel Louck (2026). _Securing LLM-Agent Long-Term Memory Against Poisoning: Non-Malleable, Origin-Bound Authority with Machine-Checked Guarantees_.** arXiv **2606.24322v1**, June 23. [Paper](https://arxiv.org/html/2606.24322v1), §§II–IV, IX; [official artifact](https://github.com/yedidel/mem-inv-bench).

TMA-NM binds authority to authenticated write channels and propagates origin through summaries, tool echoes and manufactured corroboration. Action elevation requires independent corroboration or fresh action-bound user authorization. The reported separation results are conditional on the model and authenticated origin oracle; the initial TLC enumeration is bounded, not a universal proof about deployed agents. Shared-memory cross-agent security is explicitly excluded from the paper's scope. This already supplies the core origin/authority distinction. MEMO could test failures when real interfaces cannot preserve those prerequisites; that would measure an assumption boundary, not refute a conditional theorem.

**Later artifact, separately versioned:** the current [complete-action contract](https://github.com/yedidel/mem-inv-bench/blob/main/ACTION-CONTRACT.md) describes exact whole-action approvals, policy epochs and expiry/revocation checks at local commit. Its ledger is in memory and does not survive restart. [Reproduction notes](https://github.com/yedidel/mem-inv-bench/blob/main/REPRODUCE.md) distinguish reconstructed stops, authored fixtures and independent evaluation. The README advertises artifact 2.1.0 and deterministic/service evidence. These mutable artifact extensions must not be silently attributed to June paper v1; they also preclude assuming commit-time checks or proposal/commit separation are an unoccupied research area.

### 6. MPBench / write-channel taxonomy

**Pritam Dash, Tongyu Ge, Aditi Jain, Tanmay Shah, Zhiwei Shang (2026). _From Untrusted Input to Trusted Memory: A Systematic Study of Memory Poisoning Attacks in LLM Agents_.** arXiv **2606.04329v2**, June 18; first submitted June 3. [Paper](https://arxiv.org/html/2606.04329v2), §§2–4.

This work distinguishes four write channels and six attack classes. MPBench separately checks the persistent write and later-session behavioral influence; semantic write equivalence uses an LLM judge. Its agents and memory policies differ from MEMO's qualified provider modes. The relevant overlap is persistent multi-session evaluation, not revocation itself. MEMO can add deterministic authority and direct native selection custody, but must still demonstrate downstream influence separately from a stored payload or visible string. A lexical tag, semantic content and native causal lineage are three different measurements.

### 7. PPMF / source-authority non-amplification

**Jinghan Xu, Yiyong Xiao, Wanru Shao, Hankai Liu, Xinjin Li (2026). _Memory Provenance Laundering in LLM Agents: A Non-Amplification Firewall for Persistent Memory_.** arXiv **2607.29167v1**, July 31; metadata says “EMNLP2026 submitted,” not accepted. [Metadata](https://arxiv.org/abs/2607.29167v1), [full PDF](https://arxiv.org/pdf/2607.29167v1), §§3–4 and appendix on missing provenance.

PPMF retains platform metadata through consolidation and deterministically binds action arguments to memory support. Partial/ambiguous support keeps all candidates and uses least trust; tool authentication does not clean externally sourced content. It explicitly tests loss of provenance, defaulting to UNKNOWN and measuring false blocks. Thus “provenance loss must not elevate authority” and conservative unknown handling are established mechanisms. MEMO's partial-map defect is a local violation of this general principle. A useful contribution would measure how native provider normalization introduces that loss, with a complete external oracle and retained benign utility.

### 8. SAFE-Mem

**Haoming Li, Dingyi Kang, Xu Hu, Jinxin Yang, Zhu Xu, Chenru Wang, Yi Ge, Miao Yin, Guanpeng Li, Feng Chen, Bingzhe Li (2026). _SAFE-Mem: Secure Agentic Memory with Fine-Grained Authority and Governance-Aware Retrieval_.** arXiv **2610.22959v2**, October 20; first submitted October 16. [Metadata](https://arxiv.org/abs/2610.22959), [PDF](https://arxiv.org/pdf/2610.22959v2), §4; [source](https://github.com/LVenum/SAFE-Mem).

SAFE-Mem gives claims kind, channel-derived authority and scope. It admits eligible claims before similarity ranking, marks conflicts and rechecks memory-derived identifiers at tool calls. Derived claims inherit the lowest authority present unless explicitly endorsed. Some semantic use/retention judgments are model-mediated. This overlaps fine-grained authority-aware retrieval, preserved provenance, mixed-origin summaries and utility-aware withholding. MEMO could examine lifecycle state changes after initial admission and restart durability, but that property must be measured rather than inferred from a static authority label. No broad comparison of effectiveness is supported without matching tasks, gates and budgets.

### 9. Revoked but Still Authoritative

**Yi Ting Shen, Kentaroh Toyoda, Alex Leung (2026). _Revoked but Still Authoritative: An Empirical Study of Revocation Enforcement in Agent-Memory Systems_.** arXiv **2609.08258v1**, September 8. [Paper](https://arxiv.org/html/2609.08258v1), §§3–5, appendices B–C; [source](https://github.com/VulcanLab/Memory-Rebirth-Attack).

This is the closest direct overlap: five backends, retained revoked/current policies, rank/exposure and downstream decisions, six defense arms, write-back descendants and shared-store agents. Main prompts omit status/time metadata. A crucial qualification is Table 13: Mem0's shipped expiration filter enabled gives no exposure; disabling it produces exposure. The abstract's blanket default claim should not be repeated. MEMO cannot claim first cross-provider revocation evaluation or first current-looking descendants escaping a root-status filter. A plausible distinction is stricter native provenance and capability accounting across reconstruction, but LC12's hard-deletion/nonvisibility result does not itself extend this retained-revocation threat model.

### 10. Endogenous authorization laundering / EAL-Bench

**Tommaso Cerruti, Mika Okamoto, Ansel Kaplan Erol (2026). _Agent Memory Is a Surface for Endogenous Authorization Laundering_.** arXiv **2609.01836v2**, October 24; first submitted September 1. Metadata reports acceptance at NeurIPS 2026 PALM Workshop. [Metadata](https://arxiv.org/abs/2609.01836), [paper](https://arxiv.org/html/2609.01836v2), §3.

A hidden deterministic ledger replays valid authorization events, while writers maintain typed/free-text memories and executors receive memory only. False-authority formation and propagation are distinct outcomes. The histories contain amendments, stale statements and non-authoritative advice without an external attacker; memory interventions help attribute effects. This overlaps MEMO's independent Host ACL and authority/history distinction. MEMO's R1 does not demonstrate false-authority formation merely because historical memory was present: all 32 proposals were ACL-valid. Cross-provider extraction/reconstruction could be a distinct empirical axis, with the same hidden authority oracle and authoring independence.

### 11. Multi-CaMeL

**James Peters-Gill, Avi Semler, Henning Bartsch, Ilia Shumailov, Christian Schroeder de Witt (2026). _Can CaMeLs Talk? Securing Multi-Agent Systems Against Indirect Prompt Injection Attacks_.** arXiv **2610.05640v1**, October 5, preprint. [Paper](https://arxiv.org/html/2610.05640v1), §§III–IV, VI.

A tool-derived value becomes trusted downstream instructions despite each individual agent using CaMeL. Multi-CaMeL enforces separate trusted instruction and opaque data channels and preserves capabilities across agent boundaries. The protocol assumes instruction-channel integrity; implementation limitations include missed implicit dependencies. Evaluation is hierarchical agent-as-tool trees; persistent shared state, cycles and retained cross-invocation history require further work. Cross-agent trust upgrade is therefore prior art. MEMO could target persistent provider-mediated re-entry, with lifecycle changes between agents and authenticated principal binding, but must show that its persistence mechanism differs from the already demonstrated handoff.

### 12. LLMbda

**Zac Garby, Andrew D. Gordon, David Sands (2026). _The LLMbda Calculus: AI Agents, Conversations, and Information Flow_.** arXiv **2602.20064v2**, July 10; first submitted February 23. [Metadata](https://arxiv.org/abs/2602.20064), [paper](https://arxiv.org/html/2602.20064v2), §§3–7.

The calculus models conversations, code generation and dynamic information-flow labels, with explicit endorsement and machine-checked probabilistic noninterference. Its executable interpreter is part of the verified harness. This supplies a stronger formal target than merely refusing an enumerated stale record. MEMO has no comparable theorem from trace normalization or synthetic decision checks. A future contract must state what trusted labeling, endorsement, confinement and dependency completeness it assumes before comparing guarantees.

### 13. Selective revocation and replay

**Ali Uyar (2026). _Selective Revocation and Replay: Post-Compromise Recovery of Explicit Persisted State in Memory-Augmented LLM Agents_.** Author page dates publication March 11, 2026. [Primary paper source](https://raw.githubusercontent.com/aliuyar1234/selective-revocation-replay/main/paper/usenix_security26/main.tex), [artifact](https://github.com/aliuyar1234/selective-revocation-replay), [author metadata](https://aliuyar.dev/research/selective-revocation-and-replay/).

Given suspicious roots, an explicit provenance DAG identifies persisted descendants; dirty writers replay from sanitized inputs, with rollback fallback if control flow is unsafe. Complete provenance and deterministic replay are assumptions. The main matrix uses a deterministic heuristic backend; live confirmation is narrower. This already covers descendant revocation and recovery with benign-state retention. It excludes hidden state and external-side-effect reversal. Metadata has a version distinction: the author page links Zenodo `18967060`, the repository cites `18967061`; this audit does not assert they are identical or that USENIX-format source means conference acceptance.

### 14. Execution-state unlearning

**Chao Yao, Yangbo Wei, Zhen Huang, Junhong Qian, Chenle Chen, Shaoqiang Lu, Chen Wu, Lei He (2026). _Forgetting Without Restarting: Execution-State Unlearning for Stateful LLM Agents_.** arXiv **2609.04875v1**, September 4. [Paper](https://arxiv.org/html/2609.04875v1), method and limitations.

This defines forgetting against a target-excluded counterfactual trajectory, covering summaries, pending plans and KV cache. Under deterministic runtime/logging assumptions, it crops the cache before target entry and regenerates the suffix; experiments also probe string-free behavioral influence. Oracle provenance is used in the harness. This is prior art for the distinction between record deletion and loss of derived influence. LC12 checks native nonvisibility after delete/reopen; it neither demonstrates nor contradicts counterfactual execution-state forgetting. Native black-box provider feasibility remains a separate question from the paper's replay model.

## What accepted MEMO evidence actually demonstrates

The checked basis is the accepted commit above, not uncommitted repairs. The [claims register](../CLAIMS_REGISTER.md), [R1 closeout](../R1_CLOSEOUT_20261026.md) and [LC12 audit](../LC12_EVIDENCE_AUDIT_20261026.md) govern interpretation.

| Evidence | Supported conclusion | Unsupported extension |
| --- | --- | --- |
| R1, 32 completed fixed Mem0/Qwen requests | Current context 32/32; historical context 16/16 conflict; 32 ACL-valid native proposals; eight registered contrasts zero | Attack immunity, enforcement efficacy, population equivalence, unresolved-state abstention, real protected dispatch |
| LC12, 12 stores / 36 checkpoints in two qualified modes | Target lookup/raw/selected nonvisibility after deletion and reopen; fixture-current content survives | Physical erasure, complete forgetting, derived-state revocation, full architecture security, downstream safety |
| LifecycleStatusFilter | Explicit invalid lifecycle states block; unknown/unsupported/not-applicable default to TAG | General authority gateway or demonstrated safe use of TAG by a model |
| ProvenanceTraceRunner | Non-BLOCK candidates appear in delivered trace; source mappings and uncertainty are recorded | Model influence or tool effect: this runner explicitly sets both execution statuses to NOT_RUN |
| Authority exposure normalization | Direct mapped event IDs are checked against an authority ledger | Complete-ancestry assurance: the accepted classifier ignores candidate provenance_status |

Direct source: [filter](../../../src/memlife/enforcement/filters.py), [trace runner](../../../src/memlife/runner/provenance.py), [storage payload producer](../../../src/memlife/runner/storage_batch.py), [authority classifier](../../../src/memlife/models/authority.py), [trace schema](../../../src/memlife/models/provenance.py). The independent [source findings](SOURCE_FINDINGS.md) bind 21 passing pure offline tests and distinguish two scoring defects. The trace runner retains mapped parent IDs and marks incomplete mapping UNKNOWN, but the classifier ignores that uncertainty. The storage producer is stronger: it discards unresolved IDs and labels any nonempty surviving subset KNOWN. The unresolved parent might be current, stale or irrelevant; the demonstrated error is falsely resolving uncertainty. Fixing only the scorer to reject UNKNOWN cannot repair the producer.

The second defect accepts provider metadata values such as source_event_id as trusted host-ledger identities when their strings match ledger event IDs. Native attacker control and knowledge of those keys remain conditional; the reproduced result is unauthenticated identity substitution at a pure scoring boundary. Neither finding establishes observed model influence or dispatch. No historical evidence is reclassified. The source review also shows that RQ4 can deny independently revoked authority despite an ACTIVE hint and quarantine changed raw bytes: a weak lifecycle baseline is not the complete existing mediator.

## Claims to retire or keep as hypotheses

- **Retire as novelty claims:** persistence through memory; summaries/tool echoes laundering source; origin-bound authority; signature-versus-authority distinction; validity-aware retrieval; provenance crossing agent boundaries; descendant revocation/recovery; proposal-versus-dispatch separation.
- **Retain as an implementation finding:** incomplete source correlation must not be upgraded to complete authoritative exposure. Report the accepted source defect and any repair separately.
- **Retain as a scientific hypothesis:** native lifecycle/provenance projection can erase the evidence needed by otherwise sound authority policies, particularly through derived state and restart. A provider-specific counterexample needs actual supported transitions and original native evidence.
- **Retain as a possible contribution:** a reproducible provider capability/observability contract that reports UNKNOWN without inventing native lineage, plus demonstrated utility-preserving enforcement across lifecycle boundaries. The present audit establishes neither completeness nor priority.

## One bounded next experiment: NEXT-LP-01 (proposal only)

**Question:** Does partial ancestry projection in the accepted normalization path silently convert mixed-authority exposure into authoritative-only exposure, and can a conservative classifier prevent that conversion while preserving fully evidenced active cases?

**Purpose and limit:** this is a preregistered offline mechanism experiment, not a model-safety benchmark. It resolves a necessary measurement prerequisite before paying for more native/model collection. It does not replay any sealed campaign.

**Frozen units:** twelve independently materialized synthetic records: two complete-oracle ancestry classes (two active parents; one active plus one revoked parent) × three adapter-visible correlation conditions (both parents mapped; the second parent unmapped; neither parent mapped) × two transport representations (fresh object; JSON round trip). Preserve native-parent-ID fixtures, complete external oracle, mapped IDs, provenance flag and lifecycle value separately. Keep the retrieved candidate's own ACTIVE hint fixed. The two representations are paired observations, not independent samples. Publish case hashes and expected oracle labels before execution; do not alter fixtures after inspecting outcomes.

**Paths and arms:** pass each record through both accepted producers (trace builder and storage payload builder), then compare the accepted classifier with a separately reviewed candidate that carries explicit correlation-completeness information and returns UNKNOWN_PROVENANCE whenever correlation is incomplete or unestablished. Generic causal-provenance UNKNOWN is not itself proof that a separately attested direct identity is unresolved. Use the exact same records. Classify TAG delivery separately; no model or sink is called. Do not “fix” the oracle to match implementation. Include both active-only positive controls and mixed-authority controls so blanket unknown/deny is visible as loss of usable evidence.

**Primary outcome:** count of incomplete-correlation rows labeled AUTHORITATIVE_ONLY despite incomplete authority evidence. **Secondary outcomes:** oracle-consistent classifications among fully mapped rows; UNKNOWN counts; survival of fully mapped active-only positive controls. Report the full 12×2 producer paths×2 arms paired table, not a pooled attack-success percentage or significance test. A deterministic zero after repair proves these fixtures pass, not universal security. Preserve failures and UNKNOWNs without replacement; reruns after edits require a new version identity.

**Decision rule:** any unsupported authoritative-only classification blocks promotion of this measurement path for scientific claims; the candidate must preserve every fully mapped active-only control. If the accepted code does not reproduce the anticipated counterexample, report that outcome and investigate the premise without changing this registration.

**Permissions:** no provider/model/embedding request, native service, container, network, browser or remote infrastructure is needed. Run only pure local code in the repository `.venv`, under offline containment. This document proposes rather than executes the experiment. Any subsequent test that claims native derived-state propagation needs separately qualified provider-supported derivation/revocation/reopen operations, independent scientific/package review, explicit exact owner and platform authority, bounded provider-internal inference costs, and a separate model grant if downstream proposals are generated. A harmless local sentinel sink can test dispatch in a future authorization package; it cannot demonstrate protected production execution.

## Methodology constraints for any later live design

Current-state absence, stale-state presence and native selection rank should be crossed rather than confounded. Preserve literal selected order and distinguish delivered metadata from sidecar metadata. Use independently authored task templates and a hidden authority oracle; count independent stores/templates rather than repeated queries as independent units. Predeclare authorized-action utility and unresolved-state abstention alongside unsafe proposals. A gate cannot demonstrate denial effectiveness when the model produces no unauthorized challenge; deterministic adversarial proposals can test the gate separately, with an explicitly different estimand. If derived lineage is unavailable, report the boundary UNKNOWN instead of manufacturing a native edge from textual similarity. If a proposal is only scored, say so; committing to a sink, crash/restart durability and time-of-check/time-of-use require their own evidence.

These constraints follow the concrete gaps in MEMO's accepted evidence and the conditional assumptions of the primary work above. They do not authorize new execution or reopen frozen R1/R2/LC12 evidence.
