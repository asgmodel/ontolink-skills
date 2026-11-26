# Task JSON contract — v4

**One task = one `.ontolink/tasks/<id>.json` file.** The fixed reference
template is [`../assets/task-template.json`](../assets/task-template.json).
The runtime derives this structure from the authoritative `knowledge.owl`,
writes `formatVersion: 4`, and omits optional empty arrays/objects for economy.
Do not copy the template into every task. Existing v2/v3 tasks are readable;
an accepted task update writes v4 and refreshes its hash.

**Required core**: `formatVersion`, `id`, `type`, `uri`, `revision`,
`updatedAt`, `properties` and `relationships`. `properties` contains
`title`, `owner`, `status`, `phase` and `requiredKind`. Resource
references `belongsTo`, `dependsOn`, `usesArtifact` and `derivedFrom`
occur **only** in `relationships`. Each array is deduplicated; singleton
scalar properties are not wrapped in arrays. No `resourceFields` or
`events`; `weight=1` need not be stored because it is implicit.

**Optional sections**: `actors`, `artifacts`, `assessments`, `blockers`,
`communication`, `contracts`, `decisions`, `evidence`, `files`,
`proofs`, `recommendations`, `requirements`, `risks`, `testResults`,
`warnings`, `inputs`, `outputs`, `steps`, `reports`, `confidence`,
`likelihood`, `timestamps` and `lastUpdate`. `timestamps` permits ISO-8601
`startedAt`, `dueAt`, `completedAt`; `updatedAt` is generated once at the
top level. `lastUpdate` stores the *latest* work note; do not accumulate a
history under `updates` or `events`.

**Confidence** and **likelihood** are separate, evidence-aware arrays:
```json
{
  "confidence": [{"id":"assessment-quality","target":"tests support the new API",
                  "method":"reviewed tests","rationale":"3 passing assertions",
                  "calibrated":false,"value":0.7}],
  "likelihood": [{"id":"assessment-outage","eventScope":"API downtime",
                  "timeHorizon":"next 24 hours","method":"incident review",
                  "rationale":"historical monitoring","calibrated":false}]
}
```
The `value` field is **optional**; if supplied it must be a finite numeric
value in `[0,1]`. An unknown value is absent, not zero. A confidence score
measures support for a specified claim and is **not** an event probability.
Likelihood requires a named event and time horizon. `calibrated=true` must
not be asserted without independent calibration evidence. IDs may not be
repeated across `confidence`, `likelihood`, and `assessments` (or across
signal categories `reports`, `warnings`, `blockers`, `risks`).

Task-owned assessment notes are **not** substitutes for validated ontology
`ConfidenceAssessment` and `LikelihoodAssessment` records or proof checks.
External artifacts and proof logs remain at their original project paths;
evidence references remain inside this one JSON, with no
`.ontolink/evidence/` directory.

**Updates and validation**: use `record --json '...' --expected-revision N`.
The adapter regenerates the task JSON from RDF, validates metadata, writes
atomically and updates `taskRecordHash`. Do not edit the task JSON directly.
A task is DONE only after dependency, blocker, actual artifact and current
proof checks. No new Event nodes are created; `--save-record` is an opt-in
minimal receipt outside task data.
