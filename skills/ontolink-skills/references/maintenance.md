# Package maintenance

Maintain one `ontolink-skills` package. Its root `SKILL.md` is the entry point;
`skills/` contains the seven phase folders, and `.rule/` contains project policy
and its adapter. Keep `scripts/`, `references/`, `assets/` and `agents/` at the
coordinator root. Keep each phase's own metadata and references in its folder.

Update phase routing paths in `assets/catalog.json` and the coordinator links
when moving bundled procedures. Preserve phase names and the ontology's workflow
sequence. Do not require separate top-level phase installations.

Run the bundled checks from the coordinator root:

```sh
python scripts/test_mediator.py
python scripts/test_project_intelligence.py
python scripts/test_project_setup.py
```

For a project update, run `scripts/project_setup.py --project /path/to/project
--skills-dir .agents/skills` from the complete package. It copies the coordinator
and its nested resources as one unit, backs up replaced files, preserves existing
canonical graph bytes, and refreshes project context. Pass the existing explicit
`--state` path when configured. Keep project data outside the installed package.

Upstream provenance is recorded in `assets/package-source.json`. Repository-root scripts provide compatibility entry points and distribution
checks. The sitemap covers repository documentation and the bundled procedures.
These maintenance tools are not prerequisites for the bundled runtime.
