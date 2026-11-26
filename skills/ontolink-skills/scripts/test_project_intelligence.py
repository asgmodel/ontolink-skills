"""Tests for the optional generated Project Intelligence layer."""
from pathlib import Path
import tempfile
import unittest

from context_compiler import compile_context
from project_indexer import build_index, update_index
from rdf_store import Store, O, TYPE
from retrieval import search


class ProjectIntelligenceTests(unittest.TestCase):
    def graph(self):
        graph = Store()
        project = O + 'project:fixture'
        task = project + '/task-auth'
        graph.add(project, TYPE, O + 'Project', True)
        graph.add(project, O + 'title', 'Fixture')
        graph.add(project, O + 'revision', '1')
        graph.add(task, TYPE, O + 'Task', True)
        graph.add(task, O + 'title', 'Implement authentication refresh token')
        graph.add(task, O + 'status', 'READY')
        return graph, task

    def test_index_stays_separate_from_knowledge_owl(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / 'auth.py').write_text('def refresh_token(token):\n    return token\n', encoding='utf-8')
            data = build_index(root)
            self.assertTrue(any(r.get('symbolName') == 'refresh_token' for r in data['records']))
            self.assertFalse((root / 'knowledge.owl').exists())

    def test_incremental_refresh_preserves_unchanged_file(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / 'auth.py').write_text('def login():\n    return 1\n', encoding='utf-8')
            (root / 'billing.py').write_text('def invoice():\n    return 1\n', encoding='utf-8')
            first = build_index(root)
            billing_hash = next(r['contentHash'] for r in first['records'] if r.get('type') == 'SourceFile' and r.get('path') == 'billing.py')
            (root / 'auth.py').write_text('def refresh_token():\n    return 2\n', encoding='utf-8')
            second = update_index(root, first, ['auth.py'])
            self.assertTrue(any(r.get('symbolName') == 'refresh_token' for r in second['records']))
            self.assertEqual(billing_hash, next(r['contentHash'] for r in second['records'] if r.get('type') == 'SourceFile' and r.get('path') == 'billing.py'))

    def test_search_combines_knowledge_and_generated_index(self):
        graph, _ = self.graph()
        index = {'version': 1, 'records': [
            {'id': 'file-auth', 'type': 'SourceFile', 'path': 'src/auth.py', 'summary': 'JWT authentication service'},
            {'id': 'function-refresh', 'type': 'FunctionSymbol', 'path': 'src/auth.py', 'symbolName': 'refresh_token', 'summary': 'rotate refresh token'},
        ]}
        hits = search(graph, index, 'refresh token authentication', limit=5)
        self.assertIn('knowledge', {hit.source for hit in hits})
        self.assertIn('index', {hit.source for hit in hits})
        self.assertIn('function-refresh', {hit.id for hit in hits})

    def test_task_only_search_ignores_irrelevant_evidence_and_index(self):
        graph, task = self.graph()
        artifact = O + 'project:fixture/extra-artifact'
        graph.add(artifact, TYPE, O + 'Artifact', True)
        graph.add(artifact, O + 'title', 'Implement authentication refresh token')
        hits = search(graph, {'version': 1, 'records': [
            {'id': 'file-auth', 'type': 'SourceFile', 'path': 'auth.py',
             'summary': 'Implement authentication refresh token'}
        ]}, 'authentication refresh token', limit=5, only_tasks=True)
        self.assertEqual([hit.node for hit in hits], [task])
        self.assertTrue(all(hit.type == 'Task' for hit in hits))

    def test_context_preserves_legacy_packet_fields(self):
        base = {
            'project': 'Fixture',
            'task_index': [{'id': 'task-auth', 'status': 'READY'}],
            'workflow_skill': 'ontolink-implementation',
        }
        graph, _ = self.graph()
        hits = search(graph, {'version': 1, 'records': [
            {'id': 'file-auth', 'type': 'SourceFile', 'path': 'src/auth.py', 'summary': 'refresh token'}
        ]}, 'refresh token')
        packet = compile_context(base, hits, budget=2000)
        self.assertEqual(packet['task_index'], base['task_index'])
        self.assertEqual(packet['workflow_skill'], base['workflow_skill'])
        self.assertIn('project_intelligence', packet)


if __name__ == '__main__':
    unittest.main(verbosity=2)
