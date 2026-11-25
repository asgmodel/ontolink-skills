# Quickstart

For complete terminal installation or an existing-project update, run
`python <skill-root>/scripts/project_setup.py --project /path/to/project
--skills-dir .agents/skills` using the target host's actual directory. The same
command backs up replaced package/rule files and preserves existing project
knowledge. See the [bilingual README](https://github.com/asgmodel/ontolink-skills/blob/3231c081fd8a5e7338dbab5410619665e13ca0fc/README.md) for the two update commands
and agent prompts. Manual installation remains supported below.

Install the single `ontolink-skills` package, including its seven nested phase folders, and copy its `.rule/` to the target project. Merge the
applicable host entry point without replacing existing user instructions.
The [canonical rule](../.rule/ONTOLOGY-FIRST.md) defines first use, file placement,
updates and cleanup. All paths below assume the default root `knowledge.owl`.

## Start or resume automatically

On the first project-scoped invocation and every resume, the agent runs:

```sh
python .rule/ontolink.py start --root . --skill-root /installed/ontolink-skills
```

Use `--state path/to/existing.owl` on every command for an explicit canonical
state. Never initialize another graph. Generated `.ontolink/` files are beside
that state, preserving the mediator's relative-path contract.

Read the returned phase skill and relevant source excerpts; perform real work.
Put generated phase text under `.ontolink/artifacts/` and proof logs under
`.ontolink/proofs/`. Hash current artifacts and proofs with SHA-256, inspect
results, and create a new payload under `.ontolink/records/` for each record.
Application files remain at their existing paths.

## Record and refresh

Read the coordinator's [record contract](https://github.com/asgmodel/ontolink-skills/blob/3231c081fd8a5e7338dbab5410619665e13ca0fc/skills/ontolink-skills/references/record-contract.md)
for exact types/fields. Use the observed revision; this example records a
requirement, without claiming that a phase is complete:

```sh
mkdir -p .ontolink/records
cat > .ontolink/records/scope-001.json <<'JSON'
{"id":"scope","type":"Requirement","title":"Agreed project scope"}
JSON
python .rule/ontolink.py record --root . --skill-root /installed/ontolink-skills \
  --input .ontolink/records/scope-001.json --expected-revision 0
```

Successful records produce a revision receipt, validate state and replace
`.ontolink/context.json` automatically. Preserve submitted payloads and their
receipts. A revision conflict requires rereading and reconciling. If the writer
committed but refresh failed, do not replay the payload; repair the reported
failure and run:

```sh
python .rule/ontolink.py context --root . --skill-root /installed/ontolink-skills
```

Record artifacts, their current proof evidence, and task completion separately
with each fresh revision. DONE still requires all original mediator gates.

## Optional generated index

```sh
python .rule/ontolink.py start --root . --skill-root /installed/ontolink-skills --index
```

Once the index exists, `start`, `context` and successful `record` commands refresh
it. The index is navigational and never completion evidence. No background
watcher or network update is installed. Details: [Project Intelligence](project-intelligence.md).
