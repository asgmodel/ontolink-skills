"""Stage 2/3 of Python-only task access: verify one task and build a work packet.

This intentionally performs *targeted* validation rather than a full project
audit. Full mediator.validate() remains mandatory before committing DONE.
No generated evidence directories or duplicate task JSON files are created.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from mediator import (active_blocks, evidence_valid, identifier, phases, project,
                      short, task_gate, task_path)
from rdf_store import O, TYPE
from task_contract import TASK_DETAILS, validate_sections

_HASH = set('0123456789abcdef')
_CORE = ('title', 'status', 'owner', 'phase')
_DETAIL = tuple(sorted(TASK_DETAILS))
_RELATIONS = ('dependsOn', 'usesArtifact', 'derivedFrom')


def _node(graph, uri):
    data = {'id': short(uri), 'type': graph.one(uri, TYPE).removeprefix(O)}
    for field in ('title', 'status', 'kind', 'path'):
        value = graph.one(uri, O + field)
        if value:
            data[field] = value
    return data


def _task_document(graph, target, root):
    record = graph.one(target, O + 'taskRecord')
    if record is None:
        return {}  # Legacy graph without a task JSON stays readable.
    expected = '.ontolink/tasks/' + short(target) + '.json'
    digest = graph.one(target, O + 'taskRecordHash', '')
    if record != expected or len(digest) != 64 or any(c not in _HASH for c in digest):
        raise ValueError('Unsafe task JSON path or invalid SHA-256 reference')
    file = task_path(root, target)
    if not file.is_file():
        raise ValueError('Task JSON missing: ' + short(target))
    raw = file.read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError('Task JSON SHA-256 mismatch: ' + short(target))
    data = json.loads(raw)
    if (not isinstance(data, dict) or data.get('id') != short(target)
            or data.get('type') != 'Task' or data.get('uri') != target):
        raise ValueError('Task JSON identity mismatch')
    validate_sections(data)
    props, rels = data.get('properties', {}), data.get('relationships', {})
    if not isinstance(props, dict) or not isinstance(rels, dict) or set(props) & set(rels):
        raise ValueError('Invalid or duplicated task JSON sections')
    for field in _CORE:
        if field in props and props[field] != graph.one(target, O + field):
            raise ValueError('Task JSON does not match ontology: ' + field)
    for field in _RELATIONS + ('belongsTo',):
        actual = sorted(graph.values(target, O + field))
        if field in rels:
            values = rels[field]
            if not isinstance(values, list) or values != sorted(set(values)) or values != actual:
                raise ValueError('Task JSON relation mismatch: ' + field)
        elif actual:
            raise ValueError('Missing task relation in JSON: ' + field)
    return data


def focused_work_packet(graph, ontology, root, task_id, budget=2000):
    """Return the selected task, dependencies, gates and evidence references.

    This is safe for focused *planning*; it does NOT claim whole-graph validation,
    successful test execution, or permission to mark a task DONE.
    """
    if not isinstance(budget, int) or budget < 1:
        raise ValueError('Budget must be positive')
    root = Path(root)
    p = project(graph)
    task = identifier(graph, task_id)
    if not graph.has_type(task, 'Task') or graph.one(task, O + 'belongsTo') != p:
        raise ValueError('Unknown or foreign task: ' + task_id)
    phase = graph.one(task, O + 'phase')
    all_phases = {x['id']: x for x in phases(ontology)}
    if phase not in all_phases:
        raise ValueError('Unknown phase for task')
    for field in ('title', 'owner', 'status'):
        if not graph.one(task, O + field):
            raise ValueError('Task missing ' + field)
    if graph.one(task, O + 'status') not in {'TODO', 'READY', 'RUNNING', 'BLOCKED', 'DONE'}:
        raise ValueError('Invalid task status')
    details = _task_document(graph, task, root)
    dependencies = []
    for dep in graph.values(task, O + 'dependsOn'):
        if not graph.has_type(dep, 'Task') and not graph.has_type(dep, 'Artifact'):
            raise ValueError('Dangling or unsupported task dependency: ' + dep)
        dependencies.append(_node(graph, dep))
    required = graph.values(task, O + 'requiredKind')
    if all_phases[phase]['required_kind'] not in required:
        raise ValueError('Missing phase-required outcome')
    gates = task_gate(graph, task, root)
    # Honor phase ordering without scanning entire project per task.
    earlier = {x['id'] for x in all_phases.values() if x['order'] < all_phases[phase]['order']}
    if earlier:
        phase_by_task = {}
        statuses = {}
        types = set(graph.typed('Task'))
        for subject, pred, value, resource in graph.triples:
            if subject in types and pred == O + 'phase' and resource:
                phase_by_task[subject] = value
            if subject in types and pred == O + 'status' and not resource:
                statuses[subject] = value
        if any(phase_by_task.get(node) in earlier and statuses.get(node) != 'DONE'
               for node in types):
            gates.append('earlier-phase-incomplete')
    if graph.one(task, O + 'status') == 'BLOCKED' and not gates:
        gates.append('task-status-blocked')
    signals = []
    relevant = {task, p} | set(graph.values(task, O + 'dependsOn')) | set(graph.values(task, O + 'usesArtifact'))
    for kind in ('Blocker', 'Warning'):
        for signal in graph.typed(kind):
            if graph.one(signal, O + 'status') == 'OPEN' and set(graph.values(signal, O + 'affects')) & relevant:
                signals.append({'id': short(signal), 'type': kind,
                                'summary': graph.one(signal, O + 'summary'),
                                'severity': graph.one(signal, O + 'severity')})
    verified = []
    for evidence in graph.typed('Evidence'):
        if graph.one(evidence, O + 'supports') in relevant:
            verified.append({'id': short(evidence),
                             'artifact': short(graph.one(evidence, O + 'supports')),
                             'outcome': graph.one(evidence, O + 'outcome'),
                             'proof': graph.one(evidence, O + 'proofPath'),
                             'current': evidence_valid(graph, evidence, root)})
    packet = {
        'task': {'id': task_id, 'title': graph.one(task, O + 'title'),
                 'status': graph.one(task, O + 'status'),
                 'owner': graph.one(task, O + 'owner'),
                 'phase': phase.removeprefix(O),
                 'requiredKind': required},
        'revision': int(graph.one(p, O + 'revision')),
        'skill': all_phases[phase]['skill'],
        'dependencies': dependencies,
        'completion_gates': sorted(set(gates)),
        'validation_scope': 'targeted: task SHA, links, direct gates and proof hashes only',
    }
    if signals:
        packet['signals'] = signals
    if verified:
        packet['verified_proofs'] = verified
    # Task-owned evidence is metadata, not independently verified PASS evidence.
    material = {key: details[key] for key in _DETAIL if details.get(key) not in (None, [], '')}
    if material:
        packet['task_details'] = material
    if details:
        packet['task_record_revision'] = details.get('revision')
    # A TODO/BLOCKED task must never be advertised as safely executable.
    # Missing final proof prevents DONE, but must not prevent beginning a READY task.
    work_blockers = [gate for gate in gates if not gate.startswith('missing-current-evidence:')]
    packet['next_action'] = ('Resolve prerequisites before work'
                             if work_blockers or packet['task']['status'] not in {'READY', 'RUNNING'}
                             else 'Implement the task; satisfy completion gates before DONE')
    estimate = (len(json.dumps(packet, ensure_ascii=False, separators=(',', ':')).encode('utf-8')) + 2) // 3
    packet['context_budget'] = {'estimate': estimate, 'limit': budget,
                                'overflow': estimate > budget, 'method': 'UTF-8 bytes/3 proxy'}
    return packet
