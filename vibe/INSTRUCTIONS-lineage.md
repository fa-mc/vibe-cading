# Instruction Lineage

Provenance for rules in [vibe/INSTRUCTIONS.md](INSTRUCTIONS.md): the triggering
incidents, directives, and superseded history that explain *why* a rule exists
and what it has survived. Nothing loads this file at cold start — the live rule
keeps at most one line of *why* and points here.

**Conventions.** One `##` heading per rule, matching the rule's bold name; the
authoring rule is *Instruction-Graph Changes* → *Provenance placement for new
rules* in `vibe/INSTRUCTIONS.md`.

---

## Instruction-Graph Changes — Lightweight Path, Mandatory Fresh-Context Review

*Added 2026-09-02.* Adopted from a maintainer-side workflow review: instruction
edits were routing either through the full design flow (whose requirements and
design gates degenerate on a user directive) or, more often, through no review
at all — the Admin drafting and self-applying a new rule. The first fresh-context
review run under this rule caught three cold-start contradictions in its own
introducing diff across three BLOCK rounds before an APPROVE, which is the
evidence the independence property is load-bearing.

## Orchestrator-Brain Routing — Delegate by Default, Size Every Seat Explicitly

*Added 2026-09-02.* Adopted from a maintainer-side workflow review of spawn
policy. The measured failure it closes: a spawn with no tier named inherits the
orchestrator's model, so routine scans and drafts silently ran on the most
expensive tier with no quality gain and no visible signal, because the spawn
succeeds either way. The review-seat carve-out (never escalate a review with a
pointer to the prior attempt) is the same independence property *Fresh-context
isolation for review subagents* protects.

## Conserve Context Window

*Changed 2026-09-02 — provenance split, Earns-its-keep narrowed.* The carve-out
originally kept full triggering-incident narratives inline; several rules in
the always-loaded file carry them. The
maintainer chose to narrow the carve-out to a one-line citation for **new**
rules only and route narratives here, bounding the cold-start file's growth
without touching any working rule. Retro-extraction was explicitly rejected:
each move needs a clause-survival check, and the existing narratives are what
stop repeats of specific, expensive geometry failures.
