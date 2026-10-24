# Validation and limitations

Run the bundled `scripts/test_mediator.py`, `scripts/test_project_intelligence.py` and `scripts/test_project_setup.py` checks from this coordinator root. The repository root also has `scripts/check.py` for RDFLib/SHACL and sitemap checks; that distribution-only command is not required to install or run this package.

The behavioral tests exercise phase acceptance, dependency ordering, blockers, critical warnings, changed artifacts and proofs, revision conflicts, atomic records, cycles, escaping paths, uncertainty separation, message receipts and budget overflow preservation. Fixture proof files are synthetic unit-test inputs, not application test results.

The runtime validates local provenance and state rules. It cannot establish that a test command really ran, that a PASS log proves business correctness, that an external receipt is authentic, or that an estimate is statistically calibrated. Those checks require real agent/tool evidence and human-readable review.

Normal routing uses only Python's standard library. RDFLib and pySHACL are maintenance dependencies. The constrained parser rejects unsupported RDF/XML constructs and does not implement general OWL reasoning. An initialized project is a lifecycle scaffold, not a built app.

The budget estimate is UTF-8 bytes divided by three for the emitted packet only. It is not a provider token count and excludes loaded skills, tool logs and host context. No benchmark saving is asserted. Compare real usage on comparable tasks before reporting percentages.


The optional Project Intelligence extension has a separate unit-test suite in `scripts/test_project_intelligence.py`. It checks that generated indexing remains separate from `knowledge.owl`, incremental refresh preserves unrelated entries, retrieval can combine canonical knowledge with generated code hints, and context extension preserves legacy mediator fields. `benchmark_agent_iq.py` is an engineering smoke benchmark only; do not treat its synthetic latency or ranking output as a scientific intelligence score.

The external adapter suite uses temporary projects to check fixed output paths,
first-use reuse, automatic post-record refresh, stale revisions, writer locks,
explicit state paths, malformed input, symlink rejection and post-commit
refresh failures. CI runs the same check on pull requests and pushes.

The complete-setup suite checks initial installation, state and proof preservation
after adding a command, unrelated host/skill preservation, copy-failure rollback,
invalid existing state and symlink boundaries. Sitemap checks cover all eight
skill entry points and their Markdown references. Third-party CLI examples are
documented from their upstream project and are not part of this test suite.
