# Quick start

Run `python <skill-root>/scripts/project_setup.py --project /app` once to install. In the application, call `python .rule/ontolink.py start --skill-root .agents/skills/ontolink-skills`. The result includes a small/medium/large starter proposal. The task JSON is stored only in `.ontolink/tasks/<id>.json`; all other generated folders are optional.

Use `context --task <id>` to focus, `record --json '...' --expected-revision N` to change state, and `validate` before handoff. See [record contract](record-contract.md).
