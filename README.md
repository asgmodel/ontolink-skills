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

Task JSON **v4** includes properties, one `relationships` map (no duplicated `dependsOn`), relevant files/proofs/evidence, revision and latest update. It supports `actors`, `artifacts`, `assessments`, `blockers`, `communication`, `contracts`, `decisions`, `evidence`, `files`, `proofs`, `recommendations`, `requirements`, `risks`, `testResults`, `warnings`, `inputs`, `outputs`, `steps`, `reports`, **`confidence` and `likelihood`**, and optional `timestamps` / `lastUpdate`. The **[fixed reference template](skills/ontolink-skills/assets/task-template.json)** includes all fields, but **runtime files omit empty sections**, and never create a duplicate evidence folder. Validated confidence represents support for a specified claim; likelihood represents an event with an explicit time horizon and is not interchangeable with confidence. `knowledge.owl` stores a routing projection and a SHA-256 reference to the task JSON. Task details are not copied into the graph. Records, proofs, archive and events folders are virtual until needed; no Python files are generated inside `.ontolink`.

**Format choice:** RDF/OWL handles relationships and workflow routing; JSON stores one current task snapshot; Markdown documents the process. The writer uses compact typed XML nodes without redundant `rdf:datatype="...#string"`. Numeric datatypes remain explicit for SHACL correctness, and duplicate RDF task timestamps/default weights are omitted.

**Optional records:** add `--save-record` to the installed `.rule/ontolink.py record` command only if an operation receipt is needed. It creates a brief `.ontolink/records/revision-N.json` (identity, revision and time), **not** another task copy or Event node.

```sh
python /path/to/skill/scripts/mediator.py context --state /path/to/app/knowledge.owl --task task-discover
python /path/to/skill/scripts/mediator.py record --state /path/to/app/knowledge.owl --json '{"id":"task-discover","type":"Task","lastUpdate":"Reviewed source files"}' --expected-revision 0
python /path/to/skill/scripts/mediator.py validate --state /path/to/app/knowledge.owl
```

A task may be completed only with verified current artifact/proof hashes. Dependencies remain directed and unique, and revision checks prevent conflicting writes. Older graphs without task JSON remain readable and are migrated as tasks change.

The seven phase procedures stay installed for on-demand routing. Read [the coordinator](skills/ontolink-skills/SKILL.md) for operational instructions, [task record contract](skills/ontolink-skills/references/record-contract.md) for fields, and [project rules](skills/ontolink-skills/.rule/ONTOLOGY-FIRST.md) for integration.

Tests: `python scripts/check.py` (requires `requirements-dev.txt`). This repository does **not** include generated `.ontolink` directories or project-specific task JSON.

## Reproducible RDF / JSON / Markdown benchmark

Four **synthetic**, equivalent task sets test account signup (8 tasks), SQL login
(40), WhatsApp sending (200), and Azure deployment (900). In each format the
benchmark reads and parses the data, retrieves the selected task and direct
dependencies, decides its READY/BLOCKED status, writes an actual work-order
artifact, and verifies that artifact's SHA-256. It does not deploy, modify
application source, or call a language model.

Run from the distribution checkout (Python standard library only):

    python scripts/benchmark_storage_formats.py --out /tmp/ontolink-benchmark --repeats 100 --price-per-million 0.75

Local example (median from 100 repetitions; estimated tokens are UTF-8 bytes / 3,
the existing OntoLink context proxy, NOT actual billed token counts):

| Target | Task count | Full JSON est. tokens | Focused JSON est. tokens | Saving | Read/focus p50 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Signup | 8 | 985 | 265 | 73.1% | ~0.10 ms |
| SQL login | 40 | 4,851 | 411 | 91.5% | ~0.11 ms |
| WhatsApp | 200 | 24,076 | 676 | 97.2% | ~0.38 ms |
| Azure | 900 | 108,134 | 1,094 | 99.0% | ~1.54 ms |

At $0.75 per 1M input tokens ([GPT-5.4 mini price](https://developers.openai.com/api/docs/models/gpt-5.4-mini)),
1,000 hypothetical calls in the 900-task JSON case would cost approximately
**$81.10 full** versus **$0.82 focused** in **input tokens only**. This excludes
output, caching, API calls and tools. Actual tokenization and pricing may differ.

All 12 format/case checks recovered the correct task, immediate dependencies and
readiness decision; this is **deterministic fixture fidelity**, not measured LLM
hallucination. The writing step is measured separately from read/focus time.
There is no real LLM response-time measurement or actual code/deployment task
benchmark here.

Structured Markdown was smallest in this sample, JSON generally parsed faster,
and RDF/XML retained explicit semantic relations but used more bytes. **Focused
retrieval matters more than changing extensions.** Preferred architecture:
compact OWL for relations, one JSON for each active task, optional records on
request, and Markdown for explanatory documentation. Output CSV/JSON files go
to the chosen benchmark output path, never automatically to the skills repository
or the project's .ontolink directory.

## Find a task without spending tokens on the whole graph

From an installed project, use the task-only search, then expand exactly one result:

```sh
python .rule/ontolink.py search --root . --skill-root .agents/skills/ontolink-skills --query "SQL login" --limit 5
python .rule/ontolink.py context --root . --skill-root .agents/skills/ontolink-skills --task task-build
```

Search returns a short `query/tasks` response with **id, title, status, phase** only.
The search reads the canonical graph and does not load the optional source-code
index or return unrelated graph entities. A focused context still validates
evidence and dependencies, retains blockers, warnings and uncertainty, but avoids
repeating RDF hashes, project membership, empty arrays and unrelated task-index
entries. The regular `context` command is unchanged for callers that need its
full output. The project adapter now validates only once per context call.

**Never create `.ontolink/evidence/`.** The task's single JSON stores evidence
and proof references, while actual logs remain at their original file paths.
`.ontolink/records/` is still created only if `record --save-record` was
explicitly requested.

Regression checks run with `python scripts/check.py`. The byte/3 token
estimates represent output size, **not observed tokenizer usage or hallucination**.
