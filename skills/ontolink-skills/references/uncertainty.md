# Uncertainty, recommendations and signals

| Concept | Meaning | Required basis |
| --- | --- | --- |
| ConfidenceAssessment | Strength of support for a specific claim | Target, method, rationale and calibration flag |
| LikelihoodAssessment | Probability or qualified estimate for a defined event | Target, event scope, time horizon, method, rationale and calibration flag |
| Progress | Observed completed task weight | Current accepted outcomes and evidence |
| Recommendation | Suggested next action | Affected node, explicit basis and proposed/accepted/rejected state |
| Warning | Risk or caution | Affected nodes, summary, severity and OPEN/CLOSED state |
| Blocker | A condition preventing eligible work | Affected nodes, summary and OPEN/CLOSED state |
| Message | A communication record | Source, target, summary, state and real external receipt when sent |

Use values in [0,1] only when there is a justified assessment. Omit `value` when unknown; absence is neither zero probability nor zero confidence. Set `calibrated` to false for a subjective estimate, and describe whose estimate it is and why. Set it to true only with a named calibration procedure, suitable data and inspectable evidence; the software checks the flag and range but cannot establish calibration.

Do not interpret confidence=0.8 as an 80% event probability, multiply unrelated estimates into a fabricated score, or average assessments without a justified aggregation model. Conflicting assessments remain separate nodes with their provenance. A likelihood record needs a concrete event such as "API provider fails during the next test run" and an explicit horizon.

Critical warnings are blocking. Explicit blocking warnings and OPEN blockers prevent closure of affected tasks, including project-wide and artifact-linked tasks. A confidence score never overrides a blocker or substitutes for a verification gate. Record signal resolution with its rationale and verify the actual prerequisite changed.

The mediator presents relevant stored recommendations and the next eligible phase; it does not predict outcomes or automatically execute recommendations or send communications.

Task-local optional `confidence` and `likelihood` sections follow the [task JSON contract](record-contract.md). They are separate arrays, never a fabricated combined score, and never justify marking a task DONE on their own.
