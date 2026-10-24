# OntoLink  Skills & Knowledge Orchestration

**Ontology-mediated project execution, from discovery to monitoring.**

OntoLink ships one self-contained coordinator package with seven embedded phase
skills, connected through a shared OWL model and a persistent
project knowledge graph. It retrieves the current task, relevant dependencies,
contracts and evidence so an agent can continue work across sessions without
reloading every skill or the entire project history.

The coordinator manages the workflow. Phase skills provide the procedures for
each stage. Available engineering tools and optional specialist skills perform
the actual implementation, testing and delivery.

## Project ontology and selective context

![Project inputs, ontology relationships, selective context and agent workflows](docs/assets/project-ontology.jpg)

A conceptual view of project knowledge and selective context. The record contract
defines the exact runtime fields and validation rules; token savings and error
reduction depend on the workload and are not guaranteed by the diagram.

## Ontology update cycle

![OntoLink execution cycle: shared ontology and project state feed compact context, which routes phase work through evidence and guarded records](docs/assets/ontolink-overview.svg)

The execution cycle has three responsibilities:

1. **Model and state.** The shared `ontolink.owl` defines classes, relationships,
   phase order, required outcomes and skill routing. Each project's `knowledge.owl`
   stores its own facts and execution state. They are separate files with separate roles.
2. **Context and execution.** The coordinator queries the Python mediator. The
   resulting packet identifies the eligible task, its phase skill, dependencies,
   linked artifacts and completion gates. The agent reads that phase's contract
   and the relevant source, then performs the work using available tools.
3. **Evidence and persistence.** The agent records factual changes and current
   artifact/proof hashes. The mediator checks revisions, structure, provenance
   and workflow gates before accepting an update. It commits accepted changes
   atomically and logs an audit event. Fresh context guides the next task.

The ontology is semantic data. The mediator applies the operational guards; the
file format does not execute code or enforce a workflow on its own. The runtime
supports a constrained named-node RDF/XML representation, not general OWL reasoning.

## The eight skills

| Order | Skill | Required outcome |
| --- | --- | --- |
| Coordinator | [ontolink-skills](https://github.com/asgmodel/ontolink-skills/blob/main/skills/ontolink-skills/SKILL.md) | Canonical knowledge, routing and handoffs |
| 1 | [ontolink-discovery](https://github.com/asgmodel/ontolink-skills/blob/main/skills/ontolink-skills/skills/ontolink-discovery/SKILL.md) | Requirements and acceptance criteria |
| 2 | [ontolink-architecture](https://github.com/asgmodel/ontolink-skills/blob/main/skills/ontolink-skills/skills/ontolink-architecture/SKILL.md) | Reviewed architecture and contracts |
| 3 | [ontolink-planning](https://github.com/asgmodel/ontolink-skills/blob/main/skills/ontolink-skills/skills/ontolink-planning/SKILL.md) | Execution plan and dependencies |
| 4 | [ontolink-implementation](https://github.com/asgmodel/ontolink-skills/blob/main/skills/ontolink-skills/skills/ontolink-implementation/SKILL.md) | Working implementation |
| 5 | [ontolink-verification](https://github.com/asgmodel/ontolink-skills/blob/main/skills/ontolink-skills/skills/ontolink-verification/SKILL.md) | Current verification evidence |
| 6 | [ontolink-delivery](https://github.com/asgmodel/ontolink-skills/blob/main/skills/ontolink-skills/skills/ontolink-delivery/SKILL.md) | Authorized delivery and handoff |
| 7 | [ontolink-monitoring](https://github.com/asgmodel/ontolink-skills/blob/main/skills/ontolink-skills/skills/ontolink-monitoring/SKILL.md) | Observed health and follow-up work |

Phase order is enforced when work is accepted. A later phase cannot become ready
or complete while its required earlier phases remain incomplete. Specialist
engineering skills remain optional adapters; OntoLink does not replace their
implementation capabilities or require a particular application stack.

## Project knowledge and completion

The graph represents requirements, contracts, tasks, dependencies, decisions,
artifacts, evidence, blockers, warnings, recommendations, actors and communications.
Relationships such as `dependsOn`, `usesArtifact` and `derivedFrom` connect work
to its inputs and let recorded upstream changes reopen affected tasks or mark
artifacts stale.

A task becomes `DONE` only when its required outcome has current `PASS` evidence,
predecessor phases are complete and blocking signals are resolved. Evidence
references a local proof file and exact SHA-256 hashes for both the proof and its
target artifact. Agents must still inspect whether the proof demonstrates the
claimed outcome; matching hashes alone do not establish correctness.

Progress measures accepted task weight. Confidence describes evidence strength;
likelihood concerns a named event and time horizon. Neither closes tasks nor
overrides blockers. Recording a message does not send it; sent-message records
require a real external receipt and an authorized communication action.

## Package layout

Install or copy `skills/ontolink-skills/` as one complete directory. Its internal
`skills/` contains all seven phase folders; `.rule/`, `scripts/`, `references/`,
`assets/` and `agents/` travel with it. Each phase retains its own `SKILL.md`,
metadata and references. The coordinator reads the selected bundled phase from
its catalog; no separate phase installation is required.

| Path within `skills/ontolink-skills/` | Contents |
| --- | --- |
| `SKILL.md` | Main entry point |
| `skills/` | Discovery, architecture, planning, implementation, verification, delivery and monitoring |
| `.rule/` | Shared policy and project adapter |
| `scripts/` | Runtime, complete project installer and regression checks |
| `references/` | All operational contracts and guides |
| `assets/` | Ontology, shapes, catalog, provenance and examples |
| `agents/` | Coordinator UI metadata |

## Install with npx

With Node.js 22.20+ and npm available, select the single coordinator package:

```sh
npx skills add asgmodel/ontolink-skills --skill ontolink-skills
```

The package includes all seven nested phases, scripts, rules and references.
Choose the agents in the installer. Python 3.10+ is required for the mediator.
Copying or installing a skill does not execute project setup; run the bundled
installer below to add project integration and create or reuse canonical state.

### Complete project setup

For the external `.rule` integration, managed `AGENTS.md` and `GEMINI.md` blocks,
backups, compatibility checks and initial context, use a separate distribution
checkout. Set the actual skill directory supported by your host:

```sh
git clone https://github.com/asgmodel/ontolink-skills.git /path/to/ontolink-distribution
python /path/to/ontolink-distribution/skills/ontolink-skills/scripts/project_setup.py \
  --project /path/to/my-project --skills-dir .agents/skills
```

Setup copies the single package with all nested phases and rules, preserves
unrelated skills and project files, and backs up replaced files under
`.ontolink/backups/`. It manages copied
packages itself; do not assume those copies are registered in the npx installer's
lock data. Use the update method corresponding to the installation you actually have.

The same installer is included in the installed/downloaded package:

```sh
python /actual/path/ontolink-skills/scripts/project_setup.py \
  --project /path/to/my-project --skills-dir .agents/skills
```

Existing managed sibling phase copies are backed up before migration into the
single package. Their local customizations remain in the reported backup for
review; unrelated skills, canonical graph bytes and project files are preserved.

## First use and everyday operation

At first project use, OntoLink creates or validates and reuses the project's
`knowledge.owl`. Bootstrap derives the initial project identity from the directory
and creates seven incomplete phase obligations. Existing graph bytes and progress
are preserved. An explicitly configured canonical state remains authoritative;
never initialize a second graph to clear an error.

From the application root after setup:

```sh
python .agents/skills/ontolink-skills/.rule/ontolink.py start --root . --skill-root .agents/skills/ontolink-skills
python .agents/skills/ontolink-skills/.rule/ontolink.py context --root . --skill-root .agents/skills/ontolink-skills
```

Read the returned `workflow_skill` and relevant source before acting. The graph
helps navigate the project; it does not replace source-code inspection. If no
task is eligible, address the reported dependency or blocker.

Keep OntoLink-generated JSON and text under the fixed `.ontolink/` directory:
record payloads in `records/`, proof logs in `proofs/` and generated project
artifacts in `artifacts/`. Application source stays in its native location.

Create each payload using the coordinator's record contract, then record it with
the revision observed in current context:

```sh
python .agents/skills/ontolink-skills/.rule/ontolink.py record --root . --skill-root .agents/skills/ontolink-skills \
  --input .ontolink/records/scope-001.json --expected-revision 0
```

The example requires an actual payload and the current revision; later writes
must not blindly reuse revision zero. A successful record validates state and
refreshes context automatically. On a revision conflict, reread and reconcile.
If recording committed but refresh failed, rerun `context` rather than resubmitting
that record. Preserve invalid state and active locks; do not reset or bypass them.

For an existing explicit state path, pass `--state path/to/existing.owl` on every
setup and wrapper command. Generated `.ontolink` files remain beside that state
file, preserving the mediator's relative-path contract.

## Core mediator: commands and options

`skills/ontolink-skills/scripts/mediator.py` is the core engine for project state,
routing, evidence checks and guarded writes. The `.rule/ontolink.py` adapter calls
this engine and adds fixed generated-file placement, receipts and automatic
context refresh. Direct mediator calls remain available for explicit control.

In the examples below, resolve the installed coordinator and replace the paths:

```sh
ONTO_MEDIATOR="/actual/path/to/ontolink-skills/scripts/mediator.py"
ONTO_STATE="/absolute/path/to/project/knowledge.owl"
```

| Command | Responsibility | Required options |
| --- | --- | --- |
| `bootstrap` | Create or validate and reuse root `knowledge.owl`; return context. | None; set `--root` explicitly for the target project. |
| `init` | Deliberately create a new, named state; refuse to overwrite an existing file. | `--project`, `--title`, `--output` |
| `context` | Validate state and return the selected task, phase skill, dependencies, evidence and gates. | `--state` |
| `record` | Upsert one JSON record, apply dependency impact and commit with a revision guard. | `--state`, `--input`, `--expected-revision` |
| `validate` | Check state structure, local provenance and workflow rules without modifying state. | `--state` |

For basic state monitoring, use `context` and `validate`. There is no continuous
`watch` or `monitor` command in this CLI.

### `bootstrap`: start or resume

```sh
python "$ONTO_MEDIATOR" bootstrap --root /absolute/path/to/project
```

- `--root PATH`: existing target directory; defaults to the current directory.
- `--project ID`: optional initial project ID; otherwise inferred from the directory.
- `--title TEXT`: optional initial title; otherwise the directory name.

The optional identity/title apply only to new state. Existing state is validated
and reused without resetting progress. Output includes `state`, `created` and
`context`. Bootstrap always uses `<root>/knowledge.owl`; for an already-configured
custom state path, query that state directly instead of bootstrapping another graph.

### `init`: create an explicitly named new state

```sh
python "$ONTO_MEDIATOR" init --project research-project \
  --title "Research Project" --output /absolute/path/to/new-project/knowledge.owl
```

All three options are required. `--project` accepts a lowercase letter or digit
followed by lowercase letters, digits or hyphens, up to 64 characters in total.
`--output` is the new state path. Use `init` as a deliberate alternative to
bootstrap, not as an extra step for an existing project. It returns initial context.

### `context`: inspect current work

```sh
python "$ONTO_MEDIATOR" context --state "$ONTO_STATE"
python "$ONTO_MEDIATOR" context --state "$ONTO_STATE" \
  --task task-discover --budget 4000
```

- `--state PATH`: required canonical state file.
- `--task ID`: optional focused task, including a blocked task. Without it, the
  mediator selects the currently eligible task.
- `--budget NUMBER`: positive integer; default `4000`. This is a byte-based token
  estimate for the packet, not a provider token count. Mandatory facts are retained
  and overflow is reported rather than silently removing evidence or blockers.

The JSON packet includes the revision, progress, `active_task`, `workflow_skill`,
relevant context and signals. Use its observed revision for the next record.
A context query validates current files; it does not silently reconcile changed
artifact bytes or rewrite canonical state.

### `record`: persist a factual change

```sh
python "$ONTO_MEDIATOR" record --state "$ONTO_STATE" \
  --input /absolute/path/to/project/.ontolink/records/scope-001.json \
  --expected-revision 0
```

- `--state PATH`: required canonical state file.
- `--input PATH`: required JSON file containing one record, using the coordinator's
  record contract. Keep generated payloads under `.ontolink/records/`.
- `--expected-revision NUMBER`: required integer matching the current graph revision.
  Zero is an example for newly initialized state, not a value to reuse blindly.

A successful write increments the revision, adds an audit event and returns
`revision`, `recorded` and `invalidated`. Dependency changes can reopen tasks and
stale dependent artifacts. Invalid records, unmet gates, revision conflicts or
active writer locks are not bypassed. On conflict, reread current context and
reconcile before retrying.

Direct `record` does not return or save a fresh context packet. After a successful
write, validate and query again, or use `.rule/ontolink.py record` for automatic
validation, receipts and context refresh:

```sh
python "$ONTO_MEDIATOR" validate --state "$ONTO_STATE"
python "$ONTO_MEDIATOR" context --state "$ONTO_STATE"
```

### `validate`: check the canonical graph

```sh
python "$ONTO_MEDIATOR" validate --state "$ONTO_STATE"
```

`--state PATH` is required. Checks include supported graph structure, project
membership, dependency references/cycles, phase/status rules, artifact/proof
hashes, blockers and evidence gates. Success returns `status: VALID`, task count,
revision and the validation scope. This checks local provenance and workflow;
it does not prove that a test log demonstrates correctness or authenticate an
external receipt. The command does not reset, repair or migrate state.

### Shared options and command help

`--ontology PATH` is optional and defaults to the coordinator's bundled
`assets/ontolink.owl`. It is a global option and must appear **before** the command:

```sh
python "$ONTO_MEDIATOR" --ontology /path/to/ontolink.owl \
  context --state "$ONTO_STATE"
python "$ONTO_MEDIATOR" --help
python "$ONTO_MEDIATOR" record --help
```

Use `COMMAND --help` for the options of any of the five commands. Supply a custom
ontology only when it is intentionally compatible with the existing project's
vocabulary and workflow; it is not a way to bypass completion gates.

## Update skills while keeping project data

A prompt is optional: it asks an agent to execute commands. For packages already
installed and registered through the Skills CLI, run the update directly from
the project directory:

```sh
npx skills update ontolink-skills --project
```

This targets the complete OntoLink package in the project scope. It updates
the bundled phases and rules. Run project setup to refresh project-local
integration. For packages installed as copies by `project_setup.py`, use the distribution-and-setup update commands below instead.

An existing project can receive new skill instructions, scripts and commands
without rebuilding its knowledge graph. Stop active agent work, then run these
two commands against the original distribution checkout:

```sh
git -C /path/to/ontolink-distribution pull --ff-only origin main
python /path/to/ontolink-distribution/skills/ontolink-skills/scripts/project_setup.py \
  --project /path/to/my-project --skills-dir .agents/skills
```

Setup validates the existing graph with the incoming mediator before replacing
the package, backs up replaced files, refreshes context, and checks that the existing
graph bytes have not changed. It preserves recorded knowledge, proof files,
generated artifacts and application source. Newly added package commands become
available after installation and any host-required reload.

Copy or refresh failure restores the replaced package, rule and host files.
Backups retain local customizations for deliberate merging. Invalid state or an
incompatible future data format stops the update; this is not an automatic schema
migration. Resolve local Git changes before pulling instead of discarding them.

For an older installation consisting only of copied skill folders, clone the
distribution and run setup with their actual parent directory as `--skills-dir`.
It backs up the previous copies, replaces managed sibling phases with the nested
package, and reuses existing project knowledge. Never copy
a bundled example graph over the application's canonical state.

## Prompts for coding agents

These prompts require an agent with Git access, Python execution and permission
to write the target project. Replace the example paths.

### Install

```text
Install OntoLink Skills from https://github.com/asgmodel/ontolink-skills.git
for /absolute/path/to/my-project. Use a separate distribution checkout.
Read the README and skills/ontolink-skills/.rule/ONTOLOGY-FIRST.md, resolve this host's project skill
directory, and run skills/ontolink-skills/scripts/project_setup.py with --project and --skills-dir.
Honor any existing explicit canonical state with --state. Preserve project data,
application files, user instructions and unrelated skills. Inspect fresh context
and report the installed paths, backup location, current revision and any failure.
```

### Update

```text
Update OntoLink for /absolute/path/to/my-project. Identify the existing distribution,
installation method, skill directory and canonical state. Pause active writers,
inspect local changes, and fast-forward the distribution without discarding work.
Read its current instructions and run skills/ontolink-skills/scripts/project_setup.py against the existing
project, passing --state when configured. Preserve graph bytes, records, proofs,
artifacts and application files. Keep backups and stop on compatibility errors;
do not reset state or invent a migration. Refresh context and report versions,
new commands and any host-required reload.
```

### Start or resume

```text
Use $ontolink-skills for this project. Follow .agents/skills/ontolink-skills/.rule/ONTOLOGY-FIRST.md and resolve
the installed coordinator. Create or reuse the canonical state with start,
query current context and continue the eligible phase. Inspect relevant source,
perform the authorized work, and keep generated JSON and text under .ontolink.
Record factual changes with the observed revision, refresh context after records,
and preserve the project's architecture and user changes.
```

## Comparison with other skills and Markdown

| Aspect | OntoLink Skills | A specialist engineering skill | Markdown project notes |
| --- | --- | --- | --- |
| Main role | Coordinate phases and persistent project knowledge | Perform a domain task using its tools | Explain decisions and context |
| Continuity | Canonical graph, revisions and selected context | Depends on the skill's implementation | Depends on what is recorded and reread |
| Dependencies | Explicit relationships and phase acceptance gates | Depends on the skill | Usually described in prose or links |
| Evidence | Artifact/proof hashes and workflow guards | Depends on the skill | Described or linked |
| Best use | Coordinate a project across phases and sessions | Implement or verify concrete outcomes | Document human-readable rationale |

These are complementary responsibilities, not benchmark rankings. Some specialist
skills also provide state and validation. OntoLink coordinates them without
replacing their capabilities. Markdown remains useful alongside the graph for
long explanations and narrative decisions.

## Python files and their responsibilities

### Distribution scripts: `scripts/`

| File | Responsibility |
| --- | --- |
| [project_setup.py](https://github.com/asgmodel/ontolink-skills/blob/main/scripts/project_setup.py) | Compatibility entry point for the bundled installer; backs up replaced paths, checks graph compatibility, preserves project state and rolls back replaced files on failure. |
| [check.py](https://github.com/asgmodel/ontolink-skills/blob/main/scripts/check.py) | Runs distribution checks: skill metadata, OWL/Turtle equivalence, SHACL, mediator validation, regression suites and sitemap completeness. |
| [generate_sitemap.py](https://github.com/asgmodel/ontolink-skills/blob/main/scripts/generate_sitemap.py) | Builds or checks sitemap.xml from the public skill documentation and reference pages. |
| [test_project_rules.py](https://github.com/asgmodel/ontolink-skills/blob/main/scripts/test_project_rules.py) | Tests fixed generated-file paths, post-record context refresh, revisions, locks, explicit state paths and failure recovery. |
| [test_project_setup.py](https://github.com/asgmodel/ontolink-skills/blob/main/scripts/test_project_setup.py) | Tests installation and updates, preserved registered knowledge/proof, new package files, unrelated instructions, rollback and path boundaries. |

### Coordinator runtime: `skills/ontolink-skills/scripts/`

| File | Responsibility |
| --- | --- |
| [mediator.py](https://github.com/asgmodel/ontolink-skills/blob/main/skills/ontolink-skills/scripts/mediator.py) | Core state engine: bootstrap, init, context, record and validate. Selects eligible tasks, computes progress, checks blockers and evidence, invalidates dependent work, and guards atomic revisioned writes. |
| [rdf_store.py](https://github.com/asgmodel/ontolink-skills/blob/main/skills/ontolink-skills/scripts/rdf_store.py) | Reads and writes the supported named-node RDF/XML triples. It is a constrained store, not a general OWL reasoner. |
| [project_indexer.py](https://github.com/asgmodel/ontolink-skills/blob/main/skills/ontolink-skills/scripts/project_indexer.py) | Builds or incrementally refreshes the generated code index with file hashes and lightweight symbols; it does not write canonical project state. |
| [retrieval.py](https://github.com/asgmodel/ontolink-skills/blob/main/skills/ontolink-skills/scripts/retrieval.py) | Ranks canonical knowledge and generated code hints using local BM25 lexical scores and graph-neighbor signals. |
| [context_compiler.py](https://github.com/asgmodel/ontolink-skills/blob/main/skills/ontolink-skills/scripts/context_compiler.py) | Adds budgeted optional retrieval hints while preserving the original mediator packet and its mandatory facts. |
| [project_intelligence.py](https://github.com/asgmodel/ontolink-skills/blob/main/skills/ontolink-skills/scripts/project_intelligence.py) | Command-line entry point for optional index, search and enriched context operations. |
| [benchmark_agent_iq.py](https://github.com/asgmodel/ontolink-skills/blob/main/skills/ontolink-skills/scripts/benchmark_agent_iq.py) | Runs a synthetic retrieval timing/ranking smoke benchmark. Its name does not imply a scientific intelligence or model-quality measurement. |
| [test_mediator.py](https://github.com/asgmodel/ontolink-skills/blob/main/skills/ontolink-skills/scripts/test_mediator.py) | Tests phase gates, evidence, dependency invalidation, uncertainty, communications, revisions, locking and parser boundaries. |
| [test_project_intelligence.py](https://github.com/asgmodel/ontolink-skills/blob/main/skills/ontolink-skills/scripts/test_project_intelligence.py) | Tests generated-index separation, incremental refresh, combined retrieval and preservation of mediator packet fields. |

### What performs monitoring?

`mediator.py` contains the core state inspection: progress, blockers, warnings,
current evidence and dependency impact. Its `context` and `validate` commands
perform checks when invoked. Changed upstream knowledge is reconciled through
records; querying context does not silently rewrite canonical state.

The bundled [`.rule/ontolink.py`](https://github.com/asgmodel/ontolink-skills/blob/main/skills/ontolink-skills/.rule/ontolink.py) adapter
orchestrates those checks, refreshes context after successful records and on
resume, and rebuilds an already-enabled optional index.

The [ontolink-monitoring phase skill](https://github.com/asgmodel/ontolink-skills/blob/main/skills/ontolink-skills/skills/ontolink-monitoring/SKILL.md)
defines the agent's monitoring procedure. There is no standalone `monitor.py`,
filesystem watcher or always-running monitoring service in this repository.

## Frequently asked questions

### What happens when an update adds commands to a project that already has data?

Use the update path that matches the installation method above. Package updates
retain the separate project graph and durable files; the complete setup path also
synchronizes external rules. New commands can use that
state if the format remains compatible; updating a package is not proof of migration.

### Does the ontology eliminate hallucinations or prove a product is correct?

No. The mediator checks structure, local provenance and workflow gates. Agents
must inspect source, test semantics and acceptance criteria. External receipts
and real-world outcomes still require actual tool evidence.

### Does OWL guarantee lower token costs?

No. The intended saving comes from selective retrieval and reusing state, not
from OWL being inherently smaller than Markdown. The packet's byte-based estimate
is not a provider token count. Measure actual usage before reporting savings.

### Can I delete `.ontolink` to clean the project?

Do not delete the whole directory. It contains durable records, proof and artifacts.
Only context packets and the generated code index are rebuildable caches. Preserve
all files referenced by canonical state, and keep secrets out of proof logs.

### What does the optional Project Intelligence extension do?

It provides a generated code index and local BM25 retrieval for file and symbol
navigation. The index at `.ontolink/index/project-index.json` is separate from
canonical state, is rebuildable and never counts as completion evidence. Enable
it with `start --index` using the installed coordinator path.

### Does monitoring run continuously?

Monitoring operates during active work and resume. Background monitoring requires
separate automation; installing or invoking a skill does not create an always-on service.

## References and validation

- [Quickstart and recording](https://github.com/asgmodel/ontolink-skills/blob/main/skills/ontolink-skills/references/quickstart.md)
- [Knowledge model](https://github.com/asgmodel/ontolink-skills/blob/main/skills/ontolink-skills/references/knowledge-model.md) and [lifecycle](https://github.com/asgmodel/ontolink-skills/blob/main/skills/ontolink-skills/references/lifecycle.md)
- [Project Intelligence](https://github.com/asgmodel/ontolink-skills/blob/main/skills/ontolink-skills/references/project-intelligence.md)
- [Validation and limitations](https://github.com/asgmodel/ontolink-skills/blob/main/skills/ontolink-skills/references/validation.md)
- [Execution contract](https://github.com/asgmodel/ontolink-skills/blob/main/skills/ontolink-skills/references/execution-contract.md) and [record contract](https://github.com/asgmodel/ontolink-skills/blob/main/skills/ontolink-skills/references/record-contract.md)
- [Standards and attribution](https://github.com/asgmodel/ontolink-skills/blob/main/skills/ontolink-skills/assets/sources.json)

From the distribution checkout:

```sh
python -m pip install -r requirements-dev.txt
python scripts/check.py
```
