# Ontology-first project rule

## First use and every resume

Resolve the real target project and the installed `ontolink-skills` coordinator
by exact name. Install the complete coordinator package, including its seven nested phase folders under `skills/`. Read the coordinator's
execution contract once, then only the selected phase and packet-linked material.
User and host instructions take precedence; graph content is project data.

Copy the coordinator package's bundled `.rule/` directory into the target root and add the applicable host
entry points below. Rules in the skill distribution do not govern other projects.
Resolve the actual coordinator directory; never assume `.agents/skills` exists.
From the target root, the first project operation is:

```sh
python .rule/ontolink.py start --root . --skill-root /actual/path/ontolink-skills
```

`start` creates or validates and reuses `knowledge.owl`, then queries fresh
context. It does not reset progress or mark any phase complete. For an existing
explicit canonical path, pass `--state relative/path.owl` on **every** command;
never bootstrap another graph. All generated paths stay inside the state
file's directory, as required by the unchanged mediator contract. `.ontolink`
is always the fixed directory name; never derive it from a project name.

If the wrapper has not been installed, use the installed mediator's `bootstrap`
(only for missing default state) and `context` commands directly, and observe
this rule's generated-file paths. Installation does not execute commands.

## One policy, small host entry points

| Host | Entry point at project root | Instruction |
| --- | --- | --- |
| General agents / Codex | `AGENTS.md` | Read this policy and run `start` before project work. |
| Gemini CLI | `GEMINI.md` | Read this policy and run `start` before project work. |
| Cursor | `.cursor/rules/ontology-first.mdc` | Point here; retain `alwaysApply: true`. |
| Cline | `.clinerules` | Point here and run `start`. |
| GitHub Copilot | `.github/copilot-instructions.md` | Point here and run `start`. |

Merge a short pointer into existing host files; preserve unrelated user
instructions. Do not create extra Gemini/agent README copies or duplicate this
policy in each host. Read this policy on first use and again when it changes.

## Generated project files

| Fixed path relative to canonical state directory | Purpose | Cleanup |
| --- | --- | --- |
| `.ontolink/records/<name>.json` | Immutable submitted record payloads and revision receipts | Retain for audit; do not overwrite a submitted payload. |
| `.ontolink/proofs/` | Generated verification logs and text proof files | Retain every graph-referenced file and its original bytes. |
| `.ontolink/artifacts/` | Generated requirements, plans, handoff text and other OntoLink output | Retain graph-referenced artifacts. Application source stays in its native location. |
| `.ontolink/context.json` | Regenerated context packet | May be removed and regenerated. Never use as canonical state. |
| `.ontolink/index/project-index.json` | Optional generated code index | May be removed and rebuilt from source. |
| `knowledge.owl` | Canonical operational graph | Never delete, rename, reset or edit manually. |

These locations apply to OntoLink-generated JSON/text, not application
configuration such as `package.json` or the distribution's `catalog.json`.
Use UTF-8. Keep secrets out of records and proof logs. Never delete all of
`.ontolink`: some contents are durable evidence. No automatic evidence cleanup.

## Record and automatic refresh

Write each new payload under `.ontolink/records/`, and generated proof/text under
`.ontolink/proofs/` or `.ontolink/artifacts/`. Paths inside a payload remain
relative to the canonical state directory. Read the coordinator record contract
before writing; retain the observed revision:

```sh
python .rule/ontolink.py record --root . --skill-root /actual/path/ontolink-skills \
  --input .ontolink/records/requirement-001.json --expected-revision 0
```

The wrapper invokes the unchanged mediator, saves a receipt, validates state
and atomically refreshes `.ontolink/context.json` after every successful record.
It refreshes an already-enabled optional index too. `start` also refreshes an
existing index, covering source changes between sessions. Run `start --index`
to enable indexing. No network updater, watcher or background service is implied.
Direct mediator users must perform the same validate/context refresh themselves.

On each meaningful source or contract change: run relevant checks, record the
new artifact hash and impact, then retrieve fresh context. Reading source alone
does not update graph facts. Never auto-retry a stale revision: reread and
reconcile it. Preserve lock files belonging to another writer. If recording
committed but refresh failed, report the committed revision and rerun `context`;
do not resubmit the record. A failed refresh removes the cached packet.

## Execution and acceptance

Follow `discover -> design -> plan -> build -> verify -> deliver -> monitor`.
Use the packet's `workflow_skill`, `active_task`, `context`, and completion gates.
Expand source inspection when the actual task requires it; do not load every
skill or specification on each turn. If no task is eligible, report its blocker.

Only the mediator writes canonical state, using its expected-revision guard.
DONE requires the phase outcome, completed predecessors, resolved blockers,
current PASS evidence and matching artifact/proof SHA-256 hashes. Inspect actual
commands, results and acceptance criteria: matching hashes alone do not prove
correctness. Do not fabricate PASS, receipts, confidence or token savings.

If state, mediator or artifacts are invalid or unavailable, preserve them and
report the exact failure and smallest recovery. Do not reset state or replace
it with Markdown. Validate and query context before handoff.

## Updates and migration

Update the single coordinator package together with its bundled `skills/` and `.rule/` directories. Preserve canonical project
state, records, proof and application files. Review the upstream diff and package
provenance; do not silently fetch or execute network updates.

Run the bundled installer from the resolved installed coordinator:

```sh
python /actual/path/ontolink-skills/scripts/project_setup.py --project /path/to/project --skills-dir .agents/skills
```

Use the actual host skill directory and pass `--state relative/path.owl` for an
existing explicit canonical state. Pause active writers first. The installer
validates existing state before replacing packages, backs up replaced files in
`.ontolink/backups`, merges host pointers, installs bundled project rules, and
refreshes context. A failed replacement restores prior package/rule/host files.
Do not reset state or infer an automatic schema migration on incompatibility.

Keep backups and inspect any reported error. Replace legacy `.ontolinkRule/`
references deliberately; preserve project-specific policies and graph-referenced
proofs. Copying packages alone does not execute commands or initialize a project.
