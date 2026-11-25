# Planning phase contract

- Phase: `plan`.
- Mandatory artifact kind: `plan`.
- Expected result: An implementation plan whose prerequisites, task ownership and verification obligations are explicit.
- Optional engineering adapter: autotaska or chatgpt-task-creator only when actual coordination is needed.

Resolve original skills by exact name and read their instructions only when required by the task. This module supplies a phase procedure; actual builds, tests, browser checks, provider access and external writes require real host capabilities.

Use the OntoLink graph as the shared contract. Link the outcome to its requirements and consumed artifacts, retain proof paths and hashes, and record warnings or blockers at the node they affect. The mediator's local validation is provenance and workflow checking, not a substitute for reviewing engineering correctness.

Avoid new approval steps for routine work already authorized by the user. Honor actual host requirements for new security permissions, authentication, external communications and consequential actions. Resume independent authorized work when part of the phase is blocked.
