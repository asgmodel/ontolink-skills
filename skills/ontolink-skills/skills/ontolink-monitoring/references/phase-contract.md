# Monitoring phase contract

- Phase: `monitor`.
- Mandatory artifact kind: `monitoring`.
- Expected result: A monitoring snapshot tied to the current revision and concrete follow-up tasks, without claiming an always-on service.
- Optional engineering adapter: autotaska when end-to-end coordination is needed.

Resolve original skills by exact name and read their instructions only when required by the task. This module supplies a phase procedure; actual builds, tests, browser checks, provider access and external writes require real host capabilities.

Use the OntoLink graph as the shared contract. Link the outcome to its requirements and consumed artifacts, retain proof paths and hashes, and record warnings or blockers at the node they affect. The mediator's local validation is provenance and workflow checking, not a substitute for reviewing engineering correctness.

Avoid new approval steps for routine work already authorized by the user. Honor actual host requirements for new security permissions, authentication, external communications and consequential actions. Resume independent authorized work when part of the phase is blocked.
