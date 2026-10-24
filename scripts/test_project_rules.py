"""Regression coverage for the external project adapter using real mediator calls."""
import argparse
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills/ontolink-skills'
SPEC = importlib.util.spec_from_file_location('project_rules', SKILL / '.rule/ontolink.py')
adapter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(adapter)


class ProjectRulesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def execute(self, command='start', **options):
        args = dict(root=self.root, skill_root=SKILL, state='knowledge.owl',
                    command=command, index=False)
        args.update(options)
        return adapter.execute(argparse.Namespace(**args))

    def payload(self, name='scope.json'):
        path = self.root / '.ontolink/records' / name
        path.write_text(json.dumps({'id': 'scope', 'type': 'Requirement',
                                    'title': 'Synthetic fixture requirement'}), encoding='utf-8')
        return path.relative_to(self.root).as_posix()

    def test_start_reuses_state_and_fixed_directory(self):
        first = self.execute()
        before = (self.root / 'knowledge.owl').read_bytes()
        self.execute()
        self.assertEqual((self.root / 'knowledge.owl').read_bytes(), before)
        self.assertEqual(first['context']['revision'], 0)
        self.assertTrue((self.root / '.ontolink/proofs').is_dir())
        self.assertTrue((self.root / '.ontolink/artifacts').is_dir())
        self.assertFalse(list(self.root.glob('*.json')))

    def test_record_refreshes_cache_and_receipt(self):
        self.execute()
        payload = self.payload()
        result = self.execute('record', input=payload, expected_revision=0)
        cache = json.loads((self.root / '.ontolink/context.json').read_text())
        receipt = json.loads((self.root / '.ontolink/records/revision-1.receipt.json').read_text())
        self.assertEqual(result['record']['revision'], 1)
        self.assertEqual(cache['revision'], 1)
        self.assertEqual(receipt['input'], payload)
        self.assertTrue((self.root / payload).exists())

    def test_stale_revision_preserves_graph(self):
        self.execute()
        before = (self.root / 'knowledge.owl').read_bytes()
        with self.assertRaisesRegex(ValueError, 'Revision conflict'):
            self.execute('record', input=self.payload(), expected_revision=99)
        self.assertEqual((self.root / 'knowledge.owl').read_bytes(), before)
        self.assertFalse((self.root / '.ontolink/context.json').exists())

    def test_payload_must_be_inside_fixed_records_directory(self):
        self.execute()
        (self.root / 'record.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'Record input must'):
            self.execute('record', input='record.json', expected_revision=0)
        self.assertFalse((self.root / '.ontolink/records/revision-1.receipt.json').exists())

    def test_invalid_json_preserves_state(self):
        self.execute()
        before = (self.root / 'knowledge.owl').read_bytes()
        payload = self.payload()
        (self.root / payload).write_text('{')
        with self.assertRaises(ValueError):
            self.execute('record', input=payload, expected_revision=0)
        self.assertEqual((self.root / 'knowledge.owl').read_bytes(), before)

    def test_existing_canonical_lock_is_preserved(self):
        self.execute()
        lock = self.root / 'knowledge.owl.lock'
        lock.write_text('Another writer')
        with self.assertRaises(ValueError):
            self.execute()
        self.assertEqual(lock.read_text(), 'Another writer')

    def test_adapter_lock_is_preserved(self):
        self.execute()
        lock = self.root / '.ontolink/session.lock'
        lock.write_text('Another adapter')
        with self.assertRaises(FileExistsError):
            self.execute()
        self.assertEqual(lock.read_text(), 'Another adapter')

    def test_symlink_generated_directory_is_rejected(self):
        elsewhere = self.root / 'elsewhere'
        elsewhere.mkdir()
        (self.root / '.ontolink').symlink_to(elsewhere, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'Symlink'):
            self.execute()
        self.assertEqual(list(elsewhere.iterdir()), [])
        self.assertFalse((self.root / 'knowledge.owl').exists())

    def test_explicit_state_does_not_bootstrap_second_graph(self):
        self.execute()
        nested = self.root / 'state'
        nested.mkdir()
        (self.root / 'knowledge.owl').rename(nested / 'custom.owl')
        result = self.execute(state='state/custom.owl')
        self.assertEqual(result['context']['revision'], 0)
        self.assertFalse((self.root / 'knowledge.owl').exists())
        self.assertTrue((nested / '.ontolink/context.json').exists())

    def test_missing_explicit_state_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Explicit state must already exist'):
            self.execute(state='custom.owl')
        self.assertFalse((self.root / 'knowledge.owl').exists())

    def test_index_refresh_catches_source_changes(self):
        source = self.root / 'example.py'
        source.write_text('def before(): pass\n')
        self.execute(index=True)
        source.write_text('def after(): pass\n')
        self.execute('record', input=self.payload(), expected_revision=0)
        index = json.loads((self.root / '.ontolink/index/project-index.json').read_text())
        names = [r.get('symbolName') for r in index['records']]
        self.assertIn('after', names)
        self.assertNotIn('before', names)
        source.unlink()
        self.execute()
        index = json.loads((self.root / '.ontolink/index/project-index.json').read_text())
        self.assertFalse(index['records'])

    def test_committed_record_refresh_failure_is_explicit(self):
        self.execute()
        payload = self.payload()
        with patch.object(adapter, 'refresh', side_effect=ValueError('Synthetic failure')):
            with self.assertRaisesRegex(ValueError, 'COMMITTED at revision 1'):
                self.execute('record', input=payload, expected_revision=0)
        self.assertTrue((self.root / '.ontolink/records/revision-1.receipt.json').exists())
        self.assertFalse((self.root / '.ontolink/context.json').exists())
        self.assertEqual(self.execute('context')['context']['revision'], 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
