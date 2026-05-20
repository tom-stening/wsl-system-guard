<!-- runtime-guard-wsl-seed:start -->
## Cross-Repo WSL Crash Resolution Workflow

Use `/home/thomas_stening/runtime-guard` as a reference for WSL crash mitigation patterns.

Rules:
1. Do not copy/paste code from `runtime-guard`.
2. Reimplement ideas natively for this repository and its constraints.
3. Produce concrete output every time this workflow is invoked:
   - One local implementation attempt in this repo
   - One validation result (test/repro/benchmark evidence)
   - One improvement suggestion to feed back into `runtime-guard`

Definition of done:
- Adaptation attempted in this repo
- Evidence captured
- Feedback note prepared for runtime-guard
<!-- runtime-guard-wsl-seed:end -->

---

## AI Output Verification and Hallucination Mitigation

This repository (wsl-system-guard) is a host-level WSL memory and swap pressure monitor propagating pressure events to all WSL instances. It maintains strict quality gates for
AI-assisted code and documentation to prevent hallucinations, fabricated API claims,
and incorrect domain assertions from reaching production.

### When writing code or documentation:

1. **Reasoning traces**: before generating code or documentation, state the problem
   being solved, cite the authoritative source for any domain-specific constant,
   formula, or API, and reason through edge cases and error conditions.
2. **Library contracts**: do not fabricate API signatures, protocol field names, or
   domain-specific coefficients. Verify against the cited documentation.
3. **Type safety**: all generated Python/shell code must pass static type checking with no
   implicit untyped values.
4. **Test coverage**: all generated code must have unit tests. AI-generated modules with low coverage require documented justification.
5. **Code review**: generated code requires explicit review confirming (a) domain
   claims are cited, (b) edge cases are tested, (c) high-risk paths have dual-path
   verification where applicable.

### High-risk code categories requiring extra verification:

- **OS memory interface reads** (`/proc/meminfo`, WSL host metrics): field names, units, and availability must be verified against the current WSL and kernel documentation. Kernel or WSL updates can silently change field semantics.
- **Pressure event propagation**: generated code that writes to WSL control interfaces must be tested for idempotency and correct ordering. Incorrect event sequencing can trigger cascading process termination.
- **Threshold and hysteresis logic**: any change to memory pressure tier boundaries requires benchmark evidence from a representative WSL workload. Fabricated thresholds cause spurious OOM events.

### Quarterly audit:

Every quarter, maintainers run an AI output verification audit
(see `docs/ROUTINE_MAINTENANCE.md` §Q2) checking recent agent-generated code for
hallucinations, domain claim accuracy, and test coverage gaps.
