---
name: ontolink-delivery
description: Execute the deliver phase of an OntoLink project using the ontology-mediated state and compact context. Use for OntoLink delivery, the ontolink-delivery workflow, or when the OntoLink mediator routes a task to this phase.
---

# OntoLink Delivery

Resolve the bundled `ontolink-skills` coordinator at `../..` relative to this phase folder; read its [SKILL.md](../../SKILL.md). Read its execution contract and run its mediator against the real project state. Do not rely on platform-generated folder IDs or copy a second ontology into this skill.

Before phase work, apply the coordinator's mandatory project bootstrap: create or reuse `knowledge.owl` at the actual project root without requiring a separate user request. Preserve any explicitly configured canonical state path.

1. Read the current context packet for the selected task. Confirm its phase is `deliver` and its prerequisites are satisfied before execution. For monitoring during an earlier phase, inspect read-only state and report the actual active phase; do not bypass phase closure guards.
2. Prepare and complete the authorized delivery. Check current evidence and unresolved blockers; perform only the external writes, deployment or publishing already within user scope.
3. Read [phase-contract.md](references/phase-contract.md). Apply the relevant original engineering skill instructions and actual project capabilities; never claim that reading their names executes them.
4. Record factual knowledge, artifacts and proof through the mediator with the observed revision. Keep communications, warnings, blockers, confidence and likelihood distinct. Load uncertainty guidance before making an assessment.
5. Preserve the required outcome kind `handoff`. Mark DONE only after current evidence and the actual phase outcomes are established. A blocker, missing tool or unknown external prerequisite remains explicit.
6. Generate a fresh compact packet for the next eligible phase. Do not load all phase skills, duplicate the user's project, fabricate test results or transmit messages solely because the graph recommends them.
