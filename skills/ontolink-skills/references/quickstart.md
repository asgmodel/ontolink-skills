# Quick start

Run `python <skill-root>/scripts/project_setup.py --project /app` once to install. In the application, call `python .rule/ontolink.py start --skill-root .agents/skills/ontolink-skills`. The result includes a small/medium/large starter proposal. The task JSON is stored only in `.ontolink/tasks/<id>.json`; all other generated folders are optional.

Use `search --query 'account login'` to find up to five compact, **task-only** matches without opening the optional source index. Then use `context --task <id>` to fetch a validated, focused packet containing the task, its immediate dependencies, evidence validity, blockers and completion gates. Without `--task`, `context` retains its full backward-compatible output. Use `record --json '...' --expected-revision N` to change state, and `validate` before handoff. See [record contract](record-contract.md).
