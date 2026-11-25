#!/usr/bin/env python3
"""OWL-mediated project state, compact context and guarded local updates."""
import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile
from datetime import datetime, timezone
from xml.etree.ElementTree import ParseError
from rdf_store import Store, O, TYPE

ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY = ROOT / 'assets' / 'ontolink.owl'
STATUSES = {'TODO', 'READY', 'RUNNING', 'BLOCKED', 'DONE'}
TYPES = {'Task', 'Artifact', 'Evidence', 'Requirement', 'Contract', 'Decision', 'Recommendation', 'Warning', 'Blocker', 'Risk', 'Actor', 'Message', 'ConfidenceAssessment', 'LikelihoodAssessment', 'Event'}
RESOURCES = {'dependsOn', 'usesArtifact', 'affects', 'supports', 'assesses', 'derivedFrom', 'satisfies', 'source', 'target'}
LISTS = RESOURCES | {'requiredKind'}
LITERALS = {'title', 'owner', 'role', 'status', 'kind', 'path', 'contentHash', 'proofPath', 'proofHash', 'targetHash', 'outcome', 'summary', 'severity', 'rationale', 'method', 'value', 'calibrated', 'eventScope', 'timeHorizon', 'messageStatus', 'externalReference', 'weight', 'createdAt', 'blocking', 'action', 'basis'}
HASH = re.compile(r'^[a-f0-9]{64}$')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def stamp():
    return datetime.now(timezone.utc).isoformat()


def local_path(root, value):
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise ValueError('Evidence/artifact paths must be relative to the project state directory')
    path = (root / value).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError(f'Missing or out-of-scope file: {value}')
    return path


def phases(ontology):
    result = []
    for node in ontology.typed('Phase'):
        route = ontology.one(node, O + 'routesTo')
        if not route or not ontology.has_type(route, 'Skill'):
            raise ValueError('Phase routesTo must reference a Skill individual')
        result.append({'id': node, 'order': int(ontology.one(node, O + 'order')), 'skill': ontology.one(route, O + 'skillName'), 'required_kind': ontology.one(node, O + 'requiredKind'), 'engineering': sorted(ontology.one(s, O + 'skillName') for s in ontology.values(node, O + 'usesSkill')), 'next': ontology.one(node, O + 'nextPhase')})
    result.sort(key=lambda x: x['order'])
    if not result or len({p['order'] for p in result}) != len(result):
        raise ValueError('Ontology needs unique, ordered phases')
    if any(not p['skill'] or not p['required_kind'] for p in result):
        raise ValueError('Every phase needs a skill and an outcome artifact kind')
    for index, phase in enumerate(result):
        expected = result[index + 1]['id'] if index + 1 < len(result) else None
        if phase['next'] != expected:
            raise ValueError('OWL nextPhase relations disagree with the ordered phase sequence')
    return result


def project(graph):
    nodes = graph.typed('Project')
    if len(nodes) != 1:
        raise ValueError('State must contain exactly one Project')
    return nodes[0]


def identifier(graph, short):
    if not isinstance(short, str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,79}', short):
        raise ValueError('Node IDs use lowercase letters, numbers and hyphens')
    return project(graph) + '/' + short


def short(node):
    return node.rsplit('/', 1)[-1]


def evidence_valid(graph, evidence, root):
    if graph.one(evidence, O + 'outcome') != 'PASS':
        return False
    artifact = graph.one(evidence, O + 'supports')
    if not artifact or not graph.has_type(artifact, 'Artifact') or graph.one(artifact, O + 'status') != 'CURRENT':
        return False
    try:
        return (graph.one(evidence, O + 'targetHash') == graph.one(artifact, O + 'contentHash') == sha(local_path(root, graph.one(artifact, O + 'path')))
                and graph.one(evidence, O + 'proofHash') == sha(local_path(root, graph.one(evidence, O + 'proofPath'))))
    except (ValueError, OSError, TypeError):
        return False


def reachable(graph, seeds):
    found = set(seeds)
    while True:
        more = {s for s, p, v, r in graph.triples if r and p in {O + 'dependsOn', O + 'usesArtifact', O + 'derivedFrom'} and v in found}
        if more <= found:
            return found
        found |= more


def active_blocks(graph, task):
    nodes = []
    scope = {task} | set(graph.values(task, O + 'usesArtifact')) | {project(graph)}
    for node in graph.typed('Blocker') + graph.typed('Warning'):
        blocking = graph.has_type(node, 'Blocker') or graph.one(node, O + 'severity') == 'CRITICAL' or graph.one(node, O + 'blocking') == 'true'
        if graph.one(node, O + 'status') == 'OPEN' and blocking and scope & set(graph.values(node, O + 'affects')):
            nodes.append(node)
    return sorted(nodes)


def task_gate(graph, task, root):
    errors = []
    for dep in graph.values(task, O + 'dependsOn'):
        if graph.has_type(dep, 'Task') and graph.one(dep, O + 'status') != 'DONE':
            errors.append('dependency:' + short(dep))
        if graph.has_type(dep, 'Artifact') and graph.one(dep, O + 'status') != 'CURRENT':
            errors.append('stale-artifact:' + short(dep))
    errors += ['blocker:' + short(x) for x in active_blocks(graph, task)]
    artifacts = [a for a in graph.typed('Artifact') if a in graph.values(task, O + 'usesArtifact') and graph.one(a, O + 'status') == 'CURRENT']
    for kind in graph.values(task, O + 'requiredKind'):
        matching = [a for a in artifacts if graph.one(a, O + 'kind') == kind]
        if not any(evidence_valid(graph, e, root) for e in graph.typed('Evidence') if graph.one(e, O + 'supports') in matching):
            errors.append('missing-current-evidence:' + kind)
    return errors


def validate(graph, root, ontology):
    p = project(graph)
    revision = int(graph.one(p, O + 'revision'))
    if revision < 0:
        raise ValueError('Project revision must be non-negative')
    known = graph.subjects() | ontology.subjects()
    allowed_types = TYPES | {'Project'}
    for s in graph.subjects():
        kinds = graph.values(s, TYPE)
        if len(kinds) != 1 or kinds[0].removeprefix(O) not in allowed_types:
            raise ValueError('Each state node needs one supported class: ' + s)
        if s != p and (not s.startswith(p + '/') or graph.one(s, O + 'belongsTo') != p):
            raise ValueError('State node must belong to this project: ' + s)
    for s, pred, value, resource in graph.triples:
        if resource and value not in known:
            raise ValueError('Dangling relationship: ' + value)
        if pred != TYPE and not pred.startswith(O):
            raise ValueError('Unsupported state predicate')
    phase_map = {item['id']: item for item in phases(ontology)}
    phase_ids = set(phase_map)
    for task in graph.typed('Task'):
        if graph.one(task, O + 'status') not in STATUSES or graph.one(task, O + 'phase') not in phase_ids:
            raise ValueError('Invalid task status or phase')
        if not graph.one(task, O + 'owner') or not graph.one(task, O + 'title') or not graph.values(task, O + 'requiredKind'):
            raise ValueError('Task needs an owner, title and acceptance artifact kind')
        phase = graph.one(task, O + 'phase')
        if phase_map[phase]['required_kind'] not in graph.values(task, O + 'requiredKind'):
            raise ValueError('Task cannot remove the ontology-required outcome kind')
        if graph.one(task, O + 'status') in {'READY', 'RUNNING', 'DONE'}:
            for earlier in phases(ontology):
                if earlier['order'] >= phase_map[phase]['order']:
                    break
                earlier_tasks = [t for t in graph.typed('Task') if graph.one(t, O + 'phase') == earlier['id']]
                if not earlier_tasks or any(graph.one(t, O + 'status') != 'DONE' for t in earlier_tasks):
                    raise ValueError('Earlier phase is incomplete: ' + earlier['id'])
        weight = float(graph.one(task, O + 'weight', '1'))
        if not math.isfinite(weight) or weight <= 0:
            raise ValueError('Task weight must be finite and positive')
        if graph.one(task, O + 'status') == 'DONE' and task_gate(graph, task, root):
            raise ValueError('DONE task lacks current evidence or has unmet dependencies/blockers: ' + short(task))
    visited, pending = set(), set()
    def visit(node):
        if node in pending:
            raise ValueError('Dependency cycle')
        if node in visited:
            return
        pending.add(node)
        for dep in graph.values(node, O + 'dependsOn') + graph.values(node, O + 'derivedFrom'):
            visit(dep)
        pending.remove(node); visited.add(node)
    for node in graph.subjects():
        visit(node)
    for artifact in graph.typed('Artifact'):
        if graph.one(artifact, O + 'status') not in {'CURRENT', 'STALE'}:
            raise ValueError('Artifact status must be CURRENT or STALE')
        if not graph.one(artifact, O + 'kind') or not HASH.fullmatch(graph.one(artifact, O + 'contentHash', '')):
            raise ValueError('Artifact needs a kind and SHA-256')
        if graph.one(artifact, O + 'status') == 'CURRENT' and sha(local_path(root, graph.one(artifact, O + 'path'))) != graph.one(artifact, O + 'contentHash'):
            raise ValueError('Artifact bytes changed; record the new revision and invalidate dependents')
    for evidence in graph.typed('Evidence'):
        if graph.one(evidence, O + 'outcome') not in {'PASS', 'FAIL', 'BLOCKED'} or not graph.has_type(graph.one(evidence, O + 'supports'), 'Artifact'):
            raise ValueError('Evidence needs an artifact and PASS/FAIL/BLOCKED outcome')
        if not all(HASH.fullmatch(graph.one(evidence, O + prop, '')) for prop in ['targetHash', 'proofHash']):
            raise ValueError('Evidence needs target and proof hashes')
        if sha(local_path(root, graph.one(evidence, O + 'proofPath'))) != graph.one(evidence, O + 'proofHash'):
            raise ValueError('Evidence proof bytes changed')
    for kind in ['ConfidenceAssessment', 'LikelihoodAssessment']:
        for node in graph.typed(kind):
            if not graph.one(node, O + 'assesses') or not graph.one(node, O + 'method') or not graph.one(node, O + 'rationale'):
                raise ValueError('Assessment needs target, method and rationale')
            value = graph.one(node, O + 'value')
            if value is not None and (not math.isfinite(float(value)) or not 0 <= float(value) <= 1):
                raise ValueError('Assessment value must be finite and in [0,1]; omit it when unknown')
            if graph.one(node, O + 'calibrated') not in {'true', 'false'}:
                raise ValueError('Assessment must declare whether it is calibrated')
            if kind == 'LikelihoodAssessment' and (not graph.one(node, O + 'eventScope') or not graph.one(node, O + 'timeHorizon')):
                raise ValueError('Likelihood needs a named event and time horizon')
    for kind in ['Warning', 'Blocker']:
        for node in graph.typed(kind):
            if graph.one(node, O + 'status') not in {'OPEN', 'CLOSED'} or not graph.values(node, O + 'affects') or not graph.one(node, O + 'summary'):
                raise ValueError('Signal needs OPEN/CLOSED, affected nodes and a summary')
            if kind == 'Warning' and graph.one(node, O + 'severity') not in {'INFO', 'WARNING', 'CRITICAL'}:
                raise ValueError('Warning needs an explicit severity')
    for message in graph.typed('Message'):
        if graph.one(message, O + 'messageStatus') not in {'DRAFT', 'SENT', 'ACKNOWLEDGED'}:
            raise ValueError('Invalid communication status')
        if not all(graph.one(message, O + k) for k in ['source', 'target', 'summary']):
            raise ValueError('Message needs source, target and summary')
        if graph.one(message, O + 'messageStatus') != 'DRAFT' and not graph.one(message, O + 'externalReference'):
            raise ValueError('Sent/acknowledged communication needs an actual receipt reference')
    for node in graph.typed('Recommendation'):
        if graph.one(node, O + 'status') not in {'PROPOSED', 'ACCEPTED', 'REJECTED'} or not graph.values(node, O + 'affects') or not graph.one(node, O + 'summary') or not graph.one(node, O + 'basis'):
            raise ValueError('Recommendation needs a status, affected nodes, summary and basis')
    return {'status': 'VALID', 'tasks': len(graph.typed('Task')), 'revision': int(graph.one(p, O + 'revision')), 'scope': 'Structure, local provenance and workflow guards; proof semantics and external receipts require agent review.'}


def reconcile(graph, ontology):
    phase_order = {p['id']: p['order'] for p in phases(ontology)}
    for task in graph.typed('Task'):
        status = graph.one(task, O + 'status')
        if status == 'DONE':
            continue
        deps = graph.values(task, O + 'dependsOn')
        unmet = any((graph.has_type(d, 'Task') and graph.one(d, O + 'status') != 'DONE') or (graph.has_type(d, 'Artifact') and graph.one(d, O + 'status') != 'CURRENT') for d in deps)
        current_order = phase_order.get(graph.one(task, O + 'phase'))
        if current_order is None:
            raise ValueError('Unknown task phase')
        unmet |= any(graph.one(t, O + 'status') != 'DONE' for t in graph.typed('Task') if phase_order.get(graph.one(t, O + 'phase'), 999) < current_order)
        if active_blocks(graph, task):
            graph.set(task, O + 'status', 'BLOCKED')
        elif unmet:
            graph.set(task, O + 'status', 'TODO')
        elif status in {'TODO', 'BLOCKED'}:
            graph.set(task, O + 'status', 'READY')


def apply_record(graph, record, root, ontology):
    allowed = {'id', 'type', 'phase'} | LISTS | LITERALS
    if not isinstance(record, dict) or set(record) - allowed or record.get('type') not in TYPES:
        raise ValueError('Unknown record type or fields')
    node = identifier(graph, record.get('id'))
    previous_triples = {t for t in graph.triples if t[0] == node}
    original_type = graph.values(node, TYPE)
    if original_type and original_type != [O + record['type']]:
        raise ValueError('Changing a node class is unsupported')
    previous_hash = graph.one(node, O + 'contentHash')
    graph.set(node, TYPE, O + record['type'], True)
    graph.set(node, O + 'belongsTo', project(graph), True)
    for key, value in record.items():
        if key in {'id', 'type'}:
            continue
        predicate = O + key
        graph.triples = {t for t in graph.triples if t[:2] != (node, predicate)}
        if value is None:
            continue
        if key == 'phase':
            graph.add(node, predicate, O + value, True)
        elif key in RESOURCES:
            items = value if isinstance(value, list) else [value]
            for item in items:
                target = project(graph) if item == 'project' else identifier(graph, item)
                graph.add(node, predicate, target, True)
        elif key in LISTS:
            if not isinstance(value, list):
                raise ValueError('List required for ' + key)
            for item in value:
                graph.add(node, predicate, item)
        else:
            if isinstance(value, (dict, list)):
                raise ValueError('Literal field must be a scalar')
            graph.add(node, predicate, str(value).lower() if isinstance(value, bool) else value)
    if not graph.one(node, O + 'createdAt'):
        graph.add(node, O + 'createdAt', stamp())
    changed = bool(record['type'] == 'Artifact' and previous_hash and previous_hash != graph.one(node, O + 'contentHash'))
    changed |= record['type'] == 'Task' and record.get('status') in {'TODO', 'READY', 'RUNNING', 'BLOCKED'}
    changed |= bool(previous_triples) and record['type'] in {'Contract', 'Requirement', 'Decision'} and previous_triples != {t for t in graph.triples if t[0] == node}
    if changed:
        for dep in reachable(graph, {node}) - {node}:
            if graph.has_type(dep, 'Artifact'):
                graph.set(dep, O + 'status', 'STALE')
            elif graph.has_type(dep, 'Task'):
                graph.set(dep, O + 'status', 'TODO')
    if record['type'] in {'Warning', 'Blocker'}:
        for affected in graph.typed('Task'):
            if active_blocks(graph, affected):
                graph.set(affected, O + 'status', 'BLOCKED')
                for dep in reachable(graph, {affected}) - {affected}:
                    if graph.has_type(dep, 'Task'):
                        graph.set(dep, O + 'status', 'TODO')
    reconcile(graph, ontology)
    validate(graph, root, ontology)
    return node


def snapshot(graph, ontology, root, focus=None, budget=4000):
    validate(graph, root, ontology)
    tasks = graph.typed('Task')
    if focus:
        selected = identifier(graph, focus)
        if selected not in tasks:
            raise ValueError('Unknown focus task')
    else:
        order = {p['id']: p['order'] for p in phases(ontology)}
        eligible = [t for t in tasks if graph.one(t, O + 'status') in {'READY', 'RUNNING'}]
        selected = min(eligible, key=lambda t: (order[graph.one(t, O + 'phase')], t)) if eligible else None
    done = sum(float(graph.one(t, O + 'weight', '1')) for t in tasks if graph.one(t, O + 'status') == 'DONE')
    total = sum(float(graph.one(t, O + 'weight', '1')) for t in tasks)
    def node_data(node):
        data = {'id': short(node), 'type': graph.one(node, TYPE).removeprefix(O)}
        for _, pred, value, resource in sorted(t for t in graph.triples if t[0] == node and t[1] != TYPE):
            key = pred.removeprefix(O)
            data.setdefault(key, []).append(short(value) if resource and value.startswith(project(graph) + '/') else value)
        return data
    packet = {'project': graph.one(project(graph), O + 'title'), 'revision': int(graph.one(project(graph), O + 'revision')), 'progress': {'completed_weight': done, 'total_weight': total, 'percent': round(100 * done / total, 2) if total else None, 'definition': 'Evidence-gated DONE task weights / all task weights; not confidence or likelihood'}, 'active_task': node_data(selected) if selected else None, 'workflow_skill': None, 'engineering_candidates': [], 'context': [], 'evidence': [], 'uncertainty': [], 'warnings': [], 'blockers': [], 'recommendations': [], 'communication': [], 'task_index': [{'id': short(t), 'phase': graph.one(t, O + 'phase').removeprefix(O), 'status': graph.one(t, O + 'status'), 'owner': graph.one(t, O + 'owner')} for t in tasks], 'routing_graph_hash': hashlib.sha256(json.dumps(sorted(ontology.triples)).encode()).hexdigest()}
    relevant = {project(graph)}
    if selected:
        relevant.add(selected)
        queue = [selected]
        while queue:
            node = queue.pop()
            for pred in ['dependsOn', 'usesArtifact', 'derivedFrom']:
                for dep in graph.values(node, O + pred):
                    if dep not in relevant:
                        relevant.add(dep); queue.append(dep)
        phase = next(p for p in phases(ontology) if p['id'] == graph.one(selected, O + 'phase'))
        packet['workflow_skill'] = phase['skill']
        packet['engineering_candidates'] = phase['engineering']
        packet['context'] = [node_data(n) for n in sorted(relevant - {selected, project(graph)})]
        packet['completion_gates'] = task_gate(graph, selected, root)
    for evidence in graph.typed('Evidence'):
        if graph.one(evidence, O + 'supports') in relevant:
            item = node_data(evidence); item['current_provenance_pass'] = evidence_valid(graph, evidence, root)
            packet['evidence'].append(item)
    for kind, field in [('ConfidenceAssessment', 'uncertainty'), ('LikelihoodAssessment', 'uncertainty'), ('Warning', 'warnings'), ('Blocker', 'blockers'), ('Recommendation', 'recommendations'), ('Message', 'communication')]:
        for node in graph.typed(kind):
            targets = set(graph.values(node, O + 'affects') + graph.values(node, O + 'assesses') + graph.values(node, O + 'source') + graph.values(node, O + 'target'))
            if targets & relevant and (kind not in {'Warning', 'Blocker'} or graph.one(node, O + 'status') == 'OPEN'):
                packet[field].append(node_data(node))
    if not selected:
        packet['blockers'] = [node_data(n) for n in graph.typed('Blocker') if graph.one(n, O + 'status') == 'OPEN']
        packet['warnings'] = [node_data(n) for n in graph.typed('Warning') if graph.one(n, O + 'status') == 'OPEN']
        packet['next_action'] = 'Review blocked/unmet dependencies; DONE is not assumed when no task is ready.'
    estimate = math.ceil(len(json.dumps(packet, ensure_ascii=False).encode('utf-8')) / 3)
    packet['context_budget'] = {'estimate': estimate, 'limit': budget, 'overflow': estimate > budget, 'method': 'UTF-8 bytes/3 heuristic for packet only, not observed model tokens', 'policy': 'No mandatory facts silently removed; split work or increase the budget if overflowing.'}
    return packet


def initialize(name, title, output, ontology):
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}', name):
        raise ValueError('Project ID must use lowercase hyphen-case')
    if output.exists():
        raise ValueError('Refuse to overwrite existing project state')
    graph = Store(); p = O + 'project:' + name
    graph.add(p, TYPE, O + 'Project', True); graph.add(p, O + 'title', title); graph.add(p, O + 'revision', 0)
    previous = None
    for phase in phases(ontology):
        phase_name = phase['id'].removeprefix(O)
        task = p + '/task-' + phase_name
        graph.add(task, TYPE, O + 'Task', True); graph.add(task, O + 'phase', phase['id'], True); graph.add(task, O + 'belongsTo', p, True)
        graph.add(task, O + 'title', phase_name.capitalize() + ' project work')
        graph.add(task, O + 'owner', 'coordinator'); graph.add(task, O + 'weight', 1)
        graph.add(task, O + 'requiredKind', phase['required_kind'])
        graph.add(task, O + 'status', 'TODO' if previous else 'READY')
        if previous:
            graph.add(task, O + 'dependsOn', previous, True)
        previous = task
    output.parent.mkdir(parents=True, exist_ok=True)
    validate(graph, output.parent, ontology); graph.write(output)
    return graph


def bootstrap(root, ontology, name=None, title=None):
    """Create or validate root state without resetting an existing project."""
    root = root.resolve()
    if not root.is_dir():
        raise ValueError('Project root must be an existing directory')
    path = root / 'knowledge.owl'
    if path.is_symlink():
        raise ValueError('Canonical state must not be a symlink')
    lock = path.with_suffix('.owl.lock')
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        os.close(fd)
        created = not path.exists()
        if created:
            inferred = re.sub(r'[^a-z0-9]+', '-', root.name.lower()).strip('-')[:64] or 'project'
            graph = initialize(name or inferred, title or root.name, path, ontology)
        else:
            try:
                graph = Store.read(path)
            except ParseError as error:
                raise ValueError('Invalid canonical RDF/XML state; preserve and repair it') from error
            validate(graph, root, ontology)
        return {'state': str(path), 'created': created, 'context': snapshot(graph, ontology, root)}
    finally:
        lock.unlink(missing_ok=True)


def update_file(path, record, expected, ontology):
    # Lock file plus compare-and-swap prevents two cooperating writers from losing updates.
    lock = path.with_suffix(path.suffix + '.lock')
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    temporary = None
    try:
        os.close(fd)
        graph = Store.read(path); p = project(graph)
        actual = int(graph.one(p, O + 'revision'))
        if expected != actual:
            raise ValueError(f'Revision conflict: expected {expected}, found {actual}; reread state')
        updated = copy.deepcopy(graph)
        node = apply_record(updated, record, path.parent, ontology)
        updated.set(p, O + 'revision', actual + 1)
        event = p + '/event-' + str(actual + 1)
        updated.add(event, TYPE, O + 'Event', True); updated.add(event, O + 'affects', node, True)
        updated.add(event, O + 'belongsTo', p, True)
        updated.add(event, O + 'action', 'record-upsert'); updated.add(event, O + 'createdAt', stamp())
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='ontolink-', suffix='.owl', delete=False) as tmp:
            temporary = Path(tmp.name)
        updated.write(temporary); os.replace(temporary, path)
        return {'revision': actual + 1, 'recorded': short(node), 'invalidated': [short(a) for a in updated.typed('Artifact') if updated.one(a, O + 'status') == 'STALE']}
    finally:
        if temporary and temporary.exists():
            temporary.unlink()
        lock.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ontology', type=Path, default=ONTOLOGY)
    sub = parser.add_subparsers(dest='command', required=True)
    boot = sub.add_parser('bootstrap', help='Create or reuse knowledge.owl at the project root')
    boot.add_argument('--root', type=Path, default=Path.cwd())
    boot.add_argument('--project'); boot.add_argument('--title')
    init = sub.add_parser('init'); init.add_argument('--project', required=True); init.add_argument('--title', required=True); init.add_argument('--output', type=Path, required=True)
    for command in ['validate', 'context', 'record']:
        child = sub.add_parser(command); child.add_argument('--state', type=Path, required=True)
        if command == 'context':
            child.add_argument('--task'); child.add_argument('--budget', type=int, default=4000)
        if command == 'record':
            child.add_argument('--input', type=Path, required=True); child.add_argument('--expected-revision', type=int, required=True)
    args = parser.parse_args(); ontology = Store.read(args.ontology)
    try:
        if args.command == 'bootstrap':
            result = bootstrap(args.root, ontology, args.project, args.title)
        elif args.command == 'init':
            g = initialize(args.project, args.title, args.output, ontology); result = snapshot(g, ontology, args.output.parent)
        elif args.command == 'record':
            result = update_file(args.state, json.loads(args.input.read_text()), args.expected_revision, ontology)
        else:
            graph = Store.read(args.state)
            if args.command == 'validate':
                result = validate(graph, args.state.parent, ontology)
            else:
                if args.budget < 1:
                    raise ValueError('Budget must be positive')
                result = snapshot(graph, ontology, args.state.parent, args.task, args.budget)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, OSError, TypeError, KeyError) as error:
        parser.exit(2, 'OntoLink: ' + str(error) + '\n')


if __name__ == '__main__':
    main()
