# OntoLink Skills

**One coordinator, one ontology, one JSON record per task.** OntoLink tracks project work with a compact RDF/XML graph and task-focused records without recording every update as a new event.

## Install

```sh
python skills/ontolink-skills/scripts/project_setup.py --project /path/to/app
python /path/to/app/.rule/ontolink.py start --root /path/to/app --skill-root /path/to/app/.agents/skills/ontolink-skills
```

The first run inspects the project and suggests a footprint: **small** (1 starter task), **medium** (3), or **large** (7 phase tasks). More tasks are created only for actual work.

## Project state

```text
app/
  knowledge.owl                  # project + compact task relationships
  .ontolink/
    tasks/
      task-discover.json         # one complete, current record for this task
```

Task JSON includes properties, one `relationships` map (no duplicated `dependsOn`), relevant files/proofs/evidence, revision and latest update. Empty arrays are omitted. `knowledge.owl` stores a routing projection and a SHA-256 reference to the task JSON. Task details are not copied into the graph. Records, proofs, archive and events folders are virtual until needed; no Python files are generated inside `.ontolink`.

```sh
python /path/to/skill/scripts/mediator.py context --state /path/to/app/knowledge.owl --task task-discover
python /path/to/skill/scripts/mediator.py record --state /path/to/app/knowledge.owl --json '{"id":"task-discover","type":"Task","lastUpdate":"Reviewed source files"}' --expected-revision 0
python /path/to/skill/scripts/mediator.py validate --state /path/to/app/knowledge.owl
```

A task may be completed only with verified current artifact/proof hashes. Dependencies remain directed and unique, and revision checks prevent conflicting writes. Older graphs without task JSON remain readable and are migrated as tasks change.

The seven phase procedures stay installed for on-demand routing. Read [the coordinator](skills/ontolink-skills/SKILL.md) for operational instructions, [task record contract](skills/ontolink-skills/references/record-contract.md) for fields, and [project rules](skills/ontolink-skills/.rule/ONTOLOGY-FIRST.md) for integration.

Tests: `python scripts/check.py` (requires `requirements-dev.txt`). This repository does **not** include generated `.ontolink` directories or project-specific task JSON.
