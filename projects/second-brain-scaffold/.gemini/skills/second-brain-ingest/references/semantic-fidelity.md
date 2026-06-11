# Semantic Fidelity Contract

Use this reference during every ingest before wiki writes and again after wiki writes. It defines semantic coverage for source-to-note transformation.

## Coverage Definition

Semantic coverage is sufficient only when:

- every P0/P1 semantic unit has an explicit destination or disposition; and
- every key claim added to the final note is traceable to source material or explicitly marked as agent inference.

Fluent summaries, topical similarity, or a clean page structure are not enough.

## Gate Model

Semantic fidelity has three gates:

1. Prewrite gate: before domain routing, extract source semantic units into a visible ledger. This blocks domain routing, page proposals, and writes until complete.
2. Confirmation gate: the preflight manifest exposes the Semantic Coverage Plan and the user confirms it before any wiki/raw/index write.
3. Postwrite gate: after writing, compare the final pages against the confirmed ledger and report coverage status, failures, and residual-risk.

The postwrite gate verifies the prewrite ledger; it cannot replace it. A retrospective audit after pages already exist is a corrective recovery path, not a valid normal ingest.

## Semantic Unit Types

Use the smallest unit needed to preserve meaning and reasoning:

- `claim`: conclusion or assertion.
- `premise/reason`: support for a claim.
- `inference`: reasoning step between premise and claim.
- `evidence/example`: case, quote, measurement, raw asset, or example.
- `counterexample`: objection, exception, negative case, or competing example.
- `constraint`: condition, limitation, assumption, scope, or caveat.
- `decision`: chosen option, rejected option, or trade-off.
- `open question`: unresolved issue or follow-up.
- `meta-correction`: self-correction, superseding statement, uncertainty about prior wording, or later reversal.

Knowledge atoms remain useful for domain routing. Do not treat atomization as semantic coverage; one atom may contain multiple semantic units.

## Importance

- `P0`: Meaning would be materially wrong or misleading if omitted.
- `P1`: Meaning would be materially thinner, less actionable, or less defensible if omitted.
- `P2`: Useful detail, context, or illustration that can be deferred or summarized.

All ingest levels must identify P0/P1 units. Light mode may summarize P1 handling, but it may not skip P1 disposition.

## Loss Risk

- `HIGH`: omission, merge, or rewrite could change the conclusion, erase a caveat, hide a conflict, or turn exploration into fact.
- `MED`: omission or rewrite would reduce important context but not invert the conclusion.
- `LOW`: detail can be summarized without changing the meaning.

## Transform Actions

- `preserve`: keep the unit substantially intact.
- `rewrite`: rephrase without changing meaning.
- `merge`: combine with another unit.
- `defer`: leave out of the current wiki page while recording the reason.
- `discard`: intentionally omit as noise, duplicate, unsupported, or out of scope.
- `supersede`: mark as replaced by a later correction or stronger statement.

## Coverage Status

After writing, each P0/P1 unit must have one status:

- `preserved`
- `rewritten`
- `merged`
- `deferred`
- `discarded`
- `superseded`

For `merged`, record what it was merged with. For `deferred` or `discarded`, record the reason. For `superseded`, record the later unit that replaced it.

## Failure Types

Use these labels in coverage audit findings:

- `omission`: source unit has no destination or disposition.
- `unsupported-addition`: final note adds a key claim without source support or explicit inference marker.
- `over-compression`: rewrite removed necessary nuance.
- `false-merge`: distinct ideas were collapsed as if they were the same.
- `chain-break`: reasoning path lost a premise, inference, or conclusion.
- `provenance-loss`: source/evidence relationship became unclear.
- `unresolved-conflict`: conflicting units were not resolved, marked, or escalated.

## Confirmation Gate

Pause for user confirmation, or report residual-risk if confirmation cannot happen, when any of these occur:

- P0 `defer` or `discard`.
- P0/P1 `merge` with `HIGH` loss risk or unresolved false-merge risk.
- meta-correction is ambiguous or may reverse the final conclusion.
- source support is insufficient for a final-note key claim.
- exploratory thought may be written as a settled conclusion.
- a conflict remains unresolved after coverage audit.

## Semantic Fidelity Levels

- `Light`: short material or one simple concept. Identify P0/P1 units; list P0 units explicitly and summarize P1 disposition when P1 exists. Audit P0 and confirm P1 summary has no residual-risk.
- `Standard`: default. List P0/P1 units and audit P0/P1 coverage.
- `Full`: long text, multi-turn discussion, user asks for maximum completeness, or material contains decisions, counterexamples, constraints, self-corrections, or many P0/P1 units. Segment the source, list P0/P1/P2 units, and perform full coverage audit.

Upgrade to a stronger level when the source has multiple topics, explicit caveats, counterexamples, decisions, self-correction, or many P0/P1 units.

## Prewrite Semantic Unit Plan

Before domain-routing preflight, create a working semantic unit plan. The plan must be inspectable in the preflight manifest before the user confirms the write. Do not collapse it to counts or a prose summary.

```text
semantic fidelity level: Light | Standard | Full
semantic units:
- id: SU-001
  type: claim | premise/reason | inference | evidence/example | counterexample | constraint | decision | open question | meta-correction
  importance: P0 | P1 | P2
  source_ref: <source segment, raw file, URL, image asset, or discussion turn>
  loss_risk: HIGH | MED | LOW
  proposed_target: wiki/domain/page.md#section | manifest-only | deferred
  proposed_action: preserve | rewrite | merge | defer | discard | supersede
  confirmation: none | required
```

For `proposed_target`, use the best candidate available before domain routing (`candidate:<domain-or-page>`, `TBD-after-routing`, `manifest-only`, or `deferred`) when the final page is not yet known. The id, type, importance, source_ref, loss_risk, proposed_action, and confirmation fields cannot be left as TBD for P0/P1 units.

Minimum explicit rows:

- `Light`: every P0 unit. P1 may be summarized only if every P1 has a disposition and no residual-risk remains.
- `Standard`: every P0 and P1 unit.
- `Full`: every P0, P1, and P2 unit selected by source segmentation.

## Postwrite Coverage Audit

After writing wiki pages and before final ingest manifest:

1. Verify every P0/P1 unit has a coverage status.
2. Verify every final-note key claim has source support or is explicitly marked as agent inference.
3. Report any failure using the failure taxonomy.
4. Trigger the confirmation gate for unresolved high-risk items.

Keep the full trace in the ingest manifest, not in wiki content pages. Write only durable knowledge, limitations, counterexamples, decisions, and open questions into wiki pages.

If the prewrite ledger was missing, this audit is non-compliant as a standalone substitute. Follow corrective recovery instead of claiming completion.

## Corrective Recovery

Use this only after a gate-order violation:

1. Stop further writes and journal handoff.
2. Reopen the original source material; do not derive the missing plan from the already-written notes.
3. Build the missing Semantic Coverage Plan with the minimum explicit rows for the correct fidelity level.
4. Ask the user to confirm the corrective plan.
5. Audit and repair the written pages against the confirmed plan.
6. Mark the final manifest as corrected after semantic non-compliance and report any residual-risk.
