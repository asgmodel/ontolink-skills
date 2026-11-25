"""Behavioral tests for workflow, evidence, uncertainty and concurrency guards."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from mediator import bootstrap, initialize, apply_record, snapshot, validate, update_file, sha, ONTOLOGY
from rdf_store import Store, O, TYPE


class MediatorTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.state = self.root / 'knowledge.owl'
        self.ontology = Store.read(ONTOLOGY)
        self.graph = initialize('fixture', 'Synthetic test fixture', self.state, self.ontology)

    def tearDown(self):
        self.directory.cleanup()

    def record(self, data):
        result = copy.deepcopy(self.graph)
        apply_record(result, data, self.root, self.ontology)
        self.graph = result

    def complete(self, phase='discover', kind='requirements'):
        artifact = self.root / (kind + '.txt'); artifact.write_text('Synthetic artifact fixture: ' + kind)
        proof = self.root / (kind + '.log'); proof.write_text('Synthetic provenance fixture; not a real application test')
        self.record({'id': kind, 'type': 'Artifact', 'kind': kind, 'path': artifact.name, 'contentHash': sha(artifact), 'status': 'CURRENT'})
        self.record({'id': kind + '-proof', 'type': 'Evidence', 'supports': kind, 'outcome': 'PASS', 'proofPath': proof.name, 'proofHash': sha(proof), 'targetHash': sha(artifact)})
        self.record({'id': 'task-' + phase, 'type': 'Task', 'usesArtifact': [kind], 'status': 'DONE'})

    def test_initial_context_routes_first_phase(self):
        packet = snapshot(self.graph, self.ontology, self.root)
        self.assertEqual(packet['workflow_skill'], 'ontolink-discovery')
        self.assertEqual(packet['progress']['percent'], 0)

    def test_live_owl_drives_skill_selection(self):
        self.ontology.set(self.ontology.one(O + 'discover', O + 'routesTo'), O + 'skillName', 'fixture-live-owl-skill')
        self.assertEqual(snapshot(self.graph, self.ontology, self.root)['workflow_skill'], 'fixture-live-owl-skill')

    def test_done_without_evidence_is_rejected(self):
        with self.assertRaises(ValueError):
            self.record({'id': 'task-discover', 'type': 'Task', 'status': 'DONE'})

    def test_valid_provenance_advances_sequence(self):
        self.complete()
        p = snapshot(self.graph, self.ontology, self.root)
        self.assertEqual(p['workflow_skill'], 'ontolink-architecture')
        self.assertEqual(p['progress']['completed_weight'], 1)
        self.assertTrue(p['evidence'][0]['current_provenance_pass'])

    def test_phase_outcome_cannot_be_removed(self):
        with self.assertRaises(ValueError):
            self.record({'id': 'task-discover', 'type': 'Task', 'requiredKind': ['unrelated']})

    def test_phase_cannot_jump_by_removing_dependencies(self):
        self.record({'id': 'task-build', 'type': 'Task', 'dependsOn': [], 'status': 'RUNNING'})
        task = next(x for x in snapshot(self.graph, self.ontology, self.root)['task_index'] if x['id'] == 'task-build')
        self.assertEqual(task['status'], 'TODO')

    def test_project_blocker_reopens_done_work(self):
        self.complete()
        self.record({'id': 'global-blocker', 'type': 'Blocker', 'affects': 'project', 'status': 'OPEN', 'summary': 'Synthetic project-wide prerequisite'})
        packet = snapshot(self.graph, self.ontology, self.root)
        self.assertIsNone(packet['active_task'])
        self.assertEqual(packet['progress']['completed_weight'], 0)
        self.assertEqual(len(packet['blockers']), 1)

    def test_critical_warning_is_blocking(self):
        self.record({'id': 'critical', 'type': 'Warning', 'affects': 'task-discover', 'severity': 'CRITICAL', 'status': 'OPEN', 'summary': 'Synthetic critical risk'})
        packet = snapshot(self.graph, self.ontology, self.root, 'task-discover')
        self.assertEqual(packet['active_task']['status'], ['BLOCKED'])
        self.assertIn('blocker:critical', packet['completion_gates'])

    def test_closing_blocker_does_not_complete_task(self):
        self.record({'id': 'blocked', 'type': 'Blocker', 'affects': 'task-discover', 'status': 'OPEN', 'summary': 'Synthetic prerequisite'})
        self.record({'id': 'blocked', 'type': 'Blocker', 'status': 'CLOSED'})
        p = snapshot(self.graph, self.ontology, self.root)
        self.assertEqual(p['active_task']['status'], ['READY'])
        self.assertEqual(p['progress']['percent'], 0)

    def assessment(self, kind='ConfidenceAssessment', **extra):
        return {'id': 'assessment', 'type': kind, 'assesses': 'task-discover', 'method': 'unit fixture', 'rationale': 'Synthetic test, no calibrated claim', 'calibrated': False, **extra}

    def test_unknown_confidence_remains_absent(self):
        self.record(self.assessment())
        p = snapshot(self.graph, self.ontology, self.root)
        self.assertNotIn('value', p['uncertainty'][0])
        self.assertEqual(p['progress']['percent'], 0)

    def test_invalid_and_nonfinite_scores_fail(self):
        for value in [-0.1, 1.1, 'NaN', 'Infinity']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.record(self.assessment(value=value))

    def test_likelihood_needs_event_and_horizon(self):
        with self.assertRaises(ValueError):
            self.record(self.assessment('LikelihoodAssessment', value=0.2))
        self.record(self.assessment('LikelihoodAssessment', eventScope='Synthetic provider failure', timeHorizon='Next fixture run'))
        self.assertNotIn('value', snapshot(self.graph, self.ontology, self.root)['uncertainty'][0])

    def test_confidence_does_not_override_a_blocker(self):
        self.record(self.assessment(value=0.99))
        self.record({'id': 'blocked', 'type': 'Blocker', 'affects': 'task-discover', 'status': 'OPEN', 'summary': 'Synthetic prerequisite'})
        self.assertEqual(snapshot(self.graph, self.ontology, self.root, 'task-discover')['active_task']['status'], ['BLOCKED'])

    def test_message_receipt_required_for_sent(self):
        draft = {'id': 'msg', 'type': 'Message', 'source': 'project', 'target': 'task-discover', 'summary': 'Synthetic handoff', 'messageStatus': 'DRAFT'}
        self.record(draft)
        with self.assertRaises(ValueError):
            self.record({'id': 'msg', 'type': 'Message', 'messageStatus': 'SENT'})
        self.assertEqual(snapshot(self.graph, self.ontology, self.root)['communication'][0]['messageStatus'], ['DRAFT'])

    def test_recommendation_needs_basis(self):
        with self.assertRaises(ValueError):
            self.record({'id': 'recommend', 'type': 'Recommendation', 'affects': 'task-discover', 'summary': 'Synthetic suggestion', 'status': 'PROPOSED'})

    def test_low_budget_preserves_blockers_and_assessments(self):
        self.record(self.assessment())
        self.record({'id': 'blocked', 'type': 'Blocker', 'affects': 'task-discover', 'status': 'OPEN', 'summary': 'Synthetic prerequisite'})
        p = snapshot(self.graph, self.ontology, self.root, 'task-discover', budget=1)
        self.assertTrue(p['context_budget']['overflow'])
        self.assertEqual(len(p['blockers']), 1)
        self.assertEqual(len(p['uncertainty']), 1)

    def test_changed_artifact_is_detected(self):
        self.complete(); (self.root / 'requirements.txt').write_text('Changed bytes')
        with self.assertRaises(ValueError):
            snapshot(self.graph, self.ontology, self.root)

    def test_new_artifact_revision_reopens_dependents(self):
        self.complete(); self.complete('design', 'contracts')
        (self.root / 'requirements.txt').write_text('Changed requirement revision')
        self.record({'id': 'requirements', 'type': 'Artifact', 'contentHash': sha(self.root / 'requirements.txt')})
        p = snapshot(self.graph, self.ontology, self.root)
        self.assertEqual(p['progress']['completed_weight'], 0)
        self.assertEqual(p['workflow_skill'], 'ontolink-discovery')

    def test_changed_proof_is_detected(self):
        self.complete(); (self.root / 'requirements.log').write_text('Altered proof')
        with self.assertRaises(ValueError):
            snapshot(self.graph, self.ontology, self.root)

    def test_cycle_and_dangling_reference_are_rejected(self):
        with self.assertRaises(ValueError):
            self.record({'id': 'task-discover', 'type': 'Task', 'dependsOn': 'task-design'})
        with self.assertRaises(ValueError):
            self.record({'id': 'blocked', 'type': 'Blocker', 'affects': 'missing-node', 'status': 'OPEN', 'summary': 'Synthetic'})

    def test_outside_proof_path_is_rejected(self):
        with self.assertRaises(ValueError):
            self.record({'id': 'outside', 'type': 'Artifact', 'path': '/etc/hosts', 'kind': 'requirements', 'contentHash': 'a' * 64, 'status': 'CURRENT'})

    def test_revision_conflict_preserves_file(self):
        before = self.state.read_bytes()
        with self.assertRaises(ValueError):
            update_file(self.state, self.assessment(), 99, self.ontology)
        self.assertEqual(before, self.state.read_bytes())

    def test_atomic_record_increments_revision_and_logs_event(self):
        result = update_file(self.state, self.assessment(), 0, self.ontology)
        current = Store.read(self.state)
        self.assertEqual(result['revision'], 1)
        self.assertEqual(len(current.typed('Event')), 1)
        self.assertEqual(validate(current, self.root, self.ontology)['revision'], 1)

    def test_existing_lock_prevents_lost_update(self):
        lock = self.state.with_suffix('.owl.lock'); lock.write_text('Synthetic active writer')
        with self.assertRaises(FileExistsError):
            update_file(self.state, self.assessment(), 0, self.ontology)
        self.assertTrue(lock.exists())

    def test_init_does_not_overwrite_state(self):
        before = self.state.read_bytes()
        with self.assertRaises(ValueError):
            initialize('fixture', 'Duplicate', self.state, self.ontology)
        self.assertEqual(before, self.state.read_bytes())

    def test_bootstrap_creates_root_state_and_reuses_bytes(self):
        target = self.root / 'New Project'; target.mkdir()
        result = bootstrap(target, self.ontology)
        state = target / 'knowledge.owl'
        self.assertTrue(result['created'])
        self.assertEqual(result['context']['workflow_skill'], 'ontolink-discovery')
        before = state.read_bytes()
        reused = bootstrap(target, self.ontology, 'other', 'Other')
        self.assertFalse(reused['created'])
        self.assertEqual(before, state.read_bytes())

    def test_bootstrap_preserves_invalid_state(self):
        self.state.write_text('invalid state')
        before = self.state.read_bytes()
        with self.assertRaises(ValueError):
            bootstrap(self.root, self.ontology)
        self.assertEqual(before, self.state.read_bytes())
        self.assertFalse(self.state.with_suffix('.owl.lock').exists())

    def test_bootstrap_respects_writer_lock(self):
        lock = self.state.with_suffix('.owl.lock'); lock.write_text('active writer')
        before = self.state.read_bytes()
        with self.assertRaises(FileExistsError):
            bootstrap(self.root, self.ontology)
        self.assertEqual(before, self.state.read_bytes())
        self.assertTrue(lock.exists())

    def test_bootstrap_rejects_symlink(self):
        target = self.root / 'linked'; target.mkdir()
        (target / 'knowledge.owl').symlink_to(self.state)
        with self.assertRaises(ValueError):
            bootstrap(target, self.ontology)

    def test_unsupported_rdfxml_constructs_are_rejected(self):
        path = self.root / 'invalid.owl'
        path.write_text('<!DOCTYPE x [<!ENTITY y "payload">]><x/>')
        with self.assertRaises(ValueError):
            Store.read(path)
        path.write_text('<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"><rdf:Description rdf:nodeID="x"/></rdf:RDF>')
        with self.assertRaises(ValueError):
            Store.read(path)


if __name__ == '__main__':
    unittest.main(verbosity=2)
