"""Project adapter tests: no redundant cache, per-task JSON and safe updates."""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
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
                    command=command, index=False, input=None, json=None)
        args.update(options)
        return adapter.execute(argparse.Namespace(**args))

    def payload(self):
        return json.dumps({'id': 'scope', 'type': 'Requirement',
                           'title': 'Required project scope'})

    def test_start_reuses_state_and_virtual_folders(self):
        first = self.execute()
        before = (self.root / 'knowledge.owl').read_bytes()
        self.execute()
        self.assertEqual((self.root / 'knowledge.owl').read_bytes(), before)
        self.assertEqual(first['proposal']['scale'], 'small')
        self.assertEqual(first['context']['revision'], 0)
        self.assertTrue((self.root / '.ontolink/tasks/task-discover.json').is_file())
        for name in ['records', 'proofs', 'events', 'archive']:
            self.assertFalse((self.root / '.ontolink' / name).exists())
        self.assertFalse((self.root / '.ontolink/context.json').exists())

    def test_record_updates_without_cache_or_receipt(self):
        self.execute()
        result = self.execute('record', json=self.payload(), expected_revision=0)
        self.assertEqual(result['record']['revision'], 1)
        self.assertEqual(result['context']['revision'], 1)
        files = sorted(x.relative_to(self.root).as_posix()
                       for x in (self.root / '.ontolink').rglob('*.json'))
        self.assertEqual(files, ['.ontolink/tasks/task-discover.json'])

    def test_operation_record_is_opt_in_and_does_not_copy_task(self):
        self.execute()
        updated = self.execute('record', json=self.payload(), expected_revision=0,
                               save_record=True)
        folder = self.root / '.ontolink/records'
        files = list(folder.glob('*.json'))
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].name, 'revision-1.json')
        receipt = json.loads(files[0].read_text(encoding='utf-8'))
        self.assertEqual(receipt['entity'], {'id': 'scope', 'type': 'Requirement'})
        self.assertEqual(receipt['revision'], 1)
        self.assertNotIn('properties', receipt)
        self.assertNotIn('relationships', receipt)
        self.assertEqual(updated['record']['operation_record'],
                         '.ontolink/records/revision-1.json')
        self.execute('record', json=self.payload(), expected_revision=1)
        self.assertEqual(len(list(folder.glob('*.json'))), 1)
        self.assertFalse((self.root / '.ontolink/events').exists())

    def test_stale_revision_does_not_change_state(self):
        self.execute()
        before = (self.root / 'knowledge.owl').read_bytes()
        with self.assertRaisesRegex(ValueError, 'Revision conflict'):
            self.execute('record', json=self.payload(), expected_revision=99)
        self.assertEqual((self.root / 'knowledge.owl').read_bytes(), before)

    def test_external_input_is_not_copied(self):
        self.execute()
        path = self.root / 'external-input.json'
        path.write_text(self.payload(), encoding='utf-8')
        self.execute('record', input=path.name, expected_revision=0)
        self.assertTrue(path.exists())
        self.assertFalse((self.root / '.ontolink/records').exists())

    def test_invalid_json_preserves_state(self):
        self.execute()
        before = (self.root / 'knowledge.owl').read_bytes()
        with self.assertRaises(ValueError):
            self.execute('record', json='{', expected_revision=0)
        self.assertEqual((self.root / 'knowledge.owl').read_bytes(), before)

    def test_existing_canonical_lock_is_preserved(self):
        self.execute()
        lock = self.root / 'knowledge.owl.lock'
        lock.write_text('Another writer')
        with self.assertRaises(ValueError):
            self.execute()
        self.assertEqual(lock.read_text(), 'Another writer')

    def test_session_lock_is_preserved(self):
        self.execute()
        lock = self.root / '.ontolink/session.lock'
        lock.write_text('Another adapter')
        with self.assertRaises(FileExistsError):
            self.execute()
        self.assertEqual(lock.read_text(), 'Another adapter')

    def test_symlink_storage_is_rejected(self):
        outside = self.root / 'outside'
        outside.mkdir()
        (self.root / '.ontolink').symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'Symlink'):
            self.execute()
        self.assertEqual(list(outside.iterdir()), [])

    def test_explicit_state_requires_task_records_beside_it(self):
        self.execute()
        nested = self.root / 'state'
        nested.mkdir()
        (self.root / 'knowledge.owl').rename(nested / 'custom.owl')
        shutil.move(str(self.root / '.ontolink'), str(nested / '.ontolink'))
        result = self.execute(state='state/custom.owl')
        self.assertEqual(result['context']['revision'], 0)
        self.assertFalse((self.root / 'knowledge.owl').exists())

    def test_missing_explicit_state_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Explicit state must already exist'):
            self.execute(state='custom.owl')

    def test_index_is_only_created_when_requested_and_refreshed(self):
        source = self.root / 'example.py'
        source.write_text('def before(): pass\n')
        self.execute(index=True)
        source.write_text('def after(): pass\n')
        self.execute('record', json=self.payload(), expected_revision=0)
        index = json.loads((self.root / '.ontolink/index/project-index.json').read_text())
        names = [r.get('symbolName') for r in index['records']]
        self.assertIn('after', names)
        self.assertNotIn('before', names)

    def test_committed_record_reports_failed_refresh(self):
        self.execute()
        with patch.object(adapter, 'refresh', side_effect=ValueError('Synthetic failure')):
            with self.assertRaisesRegex(ValueError, 'COMMITTED at revision 1'):
                self.execute('record', json=self.payload(), expected_revision=0)
        self.assertFalse((self.root / '.ontolink/context.json').exists())
        self.assertEqual(self.execute('context')['context']['revision'], 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
