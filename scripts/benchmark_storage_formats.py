#!/usr/bin/env python3
"""Four-case OntoLink RDF/JSON/Markdown access benchmark; Python stdlib only.

Measured: local decode + focused task context and verified work-order writing.
Not measured: LLM output, actual tokenization, hallucination, API latency or real deployment.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics
import tempfile
import time
import xml.etree.ElementTree as ET

RDF = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
OL = 'urn:benchmark:'
ET.register_namespace('rdf', RDF)
ET.register_namespace('ol', OL)
FIELDS = ('id', 'title', 'phase', 'owner', 'status', 'file', 'summary', 'blocker', 'evidence')
CASES = (
    ('small-account', 'Create account page', 8, 1, ''),
    ('medium-database', 'Fix SQL database login', 40, 2, 'Missing SQL access approval'),
    ('large-whatsapp', 'Implement WhatsApp bulk send', 200, 4, ''),
    ('huge-azure', 'Fix Azure deployment', 900, 7, 'Azure subscription billing suspended'),
)


def fixture(title, count, n_deps, blocker):
    result = []
    for i in range(count):
        is_target = i == count - 1
        is_dep = count - n_deps - 1 <= i < count - 1
        result.append(dict(
            id=f'task-{i:04d}', title=title if is_target else f'Implement component {i:04d}',
            phase='implementation', owner='ai-coordinator' if is_target else 'engineering',
            status=('BLOCKED' if blocker else 'READY') if is_target else ('DONE' if is_dep else 'TODO'),
            file=f'src/module_{i // 20:03d}/component_{i:04d}.py',
            summary='Review current implementation and verify required inputs',
            blocker=blocker if is_target else '',
            evidence=f'proof/verification_{i:04d}.log' if is_dep else '',
            dependsOn=[f'task-{j:04d}' for j in range(count - n_deps - 1, count - 1)] if is_target else []
        ))
    return result


def encode(fmt, tasks):
    if fmt == 'json':
        return (json.dumps({'tasks': tasks}, indent=2) + '\n').encode()
    if fmt == 'md':
        lines = ['# OntoLink Tasks', '']
        for t in tasks:
            lines.append('## ' + t['id'])
            lines.extend(f'- {key}: {t[key]}' for key in FIELDS)
            lines.extend(('- dependsOn: ' + ', '.join(t['dependsOn']), ''))
        return ('\n'.join(lines) + '\n').encode()
    root = ET.Element('{' + RDF + '}RDF')
    for t in tasks:
        node = ET.SubElement(root, '{' + OL + '}Task', {'{' + RDF + '}about': OL + t['id']})
        for field in FIELDS:
            ET.SubElement(node, '{' + OL + '}' + field).text = t[field]
        for dep in t['dependsOn']:
            ET.SubElement(node, '{' + OL + '}dependsOn', {'{' + RDF + '}resource': OL + dep})
    ET.indent(root)
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def decode(fmt, data):
    if fmt == 'json':
        tasks = json.loads(data)['tasks']
    elif fmt == 'md':
        tasks = []
        for line in data.decode().splitlines():
            if line.startswith('## task-'):
                tasks.append({'id': line[3:]})
            elif line.startswith('- ') and tasks:
                key, separator, val = line[2:].partition(': ')
                if not separator:
                    raise ValueError('Malformed Markdown task field')
                tasks[-1][key] = val.split(', ') if key == 'dependsOn' and val else ([] if key == 'dependsOn' else val)
    else:
        root = ET.fromstring(data)
        tasks = []
        for node in root.findall('{' + OL + '}Task'):
            task = {'id': node.attrib['{' + RDF + '}about'].split(':')[-1], 'dependsOn': []}
            for field in node:
                name = field.tag[len('{' + OL + '}'):]
                if name == 'dependsOn':
                    task[name].append(field.attrib['{' + RDF + '}resource'].split(':')[-1])
                else:
                    task[name] = field.text or ''
            tasks.append(task)
    return {t['id']: t for t in tasks}


def work_packet(index, target):
    task = index[target]
    deps = [index[d] for d in task['dependsOn']]
    if task['blocker']:
        action = 'BLOCKED: ' + task['blocker']
    elif any(d['status'] != 'DONE' or not d['evidence'] for d in deps):
        action = 'BLOCKED: incomplete or unverified dependencies'
    else:
        action = 'READY: implement then verify evidence'
    return {'target': task, 'dependencies': deps, 'next_action': action}


def write_work_order(packet, path):
    task = packet['target']
    if any(d['id'] not in task['dependsOn'] for d in packet['dependencies']):
        raise ValueError('Broken dependency mapping')
    if task['blocker'] and not packet['next_action'].startswith('BLOCKED:'):
        raise ValueError('Incorrect readiness decision')
    order = {'task': task['id'], 'action': packet['next_action'],
             'dependencies': [d['id'] for d in packet['dependencies']],
             'proofs': [d['evidence'] for d in packet['dependencies']]}
    expected = json.dumps(order, sort_keys=True, separators=(',', ':')).encode()
    path.write_bytes(expected)
    actual = path.read_bytes()
    if actual != expected:
        raise ValueError('Unverified work order')
    return hashlib.sha256(actual).hexdigest()


def benchmark(repeats, rate):
    output = []
    for label, title, count, n_deps, blocker in CASES:
        tasks = fixture(title, count, n_deps, blocker)
        target = tasks[-1]['id']
        expected = work_packet({t['id']: t for t in tasks}, target)
        for fmt in ('rdf', 'json', 'md'):
            source = encode(fmt, tasks)
            retrieval, execution = [], []
            with tempfile.TemporaryDirectory() as folder:
                file = Path(folder) / ('tasks.' + fmt)
                order = Path(folder) / 'verified-work-order.json'
                file.write_bytes(source)
                for _ in range(repeats):
                    begin = time.perf_counter_ns()
                    packet = work_packet(decode(fmt, file.read_bytes()), target)
                    focused = encode(fmt, packet['dependencies'] + [packet['target']])
                    retrieval.append((time.perf_counter_ns() - begin) / 1_000_000)
                    begin = time.perf_counter_ns()
                    digest = write_work_order(packet, order)
                    execution.append((time.perf_counter_ns() - begin) / 1_000_000)
            assert packet == expected and decode(fmt, focused)[target] == expected['target']
            full_tokens, focused_tokens = math.ceil(len(source)/3), math.ceil(len(focused)/3)
            output.append(dict(
                scenario=label, format=fmt, task_count=count,
                dependency_count=n_deps, full_bytes=len(source), focused_bytes=len(focused),
                estimated_full_tokens=full_tokens, estimated_focused_tokens=focused_tokens,
                reduction_pct=round(100 * (1 - focused_tokens/full_tokens), 2),
                retrieval_p50_ms=round(statistics.median(retrieval), 4),
                work_order_p50_ms=round(statistics.median(execution), 4),
                cost_full_per_1000_usd=round(full_tokens * rate / 1000, 5),
                cost_focused_per_1000_usd=round(focused_tokens * rate / 1000, 5),
                exact_fact_match=True, decision=packet['next_action'],
                target_in_naive_1200_token_prefix=target.encode() in source[:3600],
                work_order_sha256=digest))
    for label, *_ in CASES:
        assert len({r['work_order_sha256'] for r in output if r['scenario'] == label}) == 1
    return output


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--out', type=Path, default=Path('benchmark-output'))
    cli.add_argument('--repeats', type=int, default=50)
    cli.add_argument('--price-per-million', type=float, default=0.75)
    args = cli.parse_args()
    if args.repeats < 2 or args.price_per_million < 0:
        cli.error('Invalid benchmark options')
    rows = benchmark(args.repeats, args.price_per_million)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'results.json').write_text(json.dumps({
        'methodology': 'synthetic equivalent facts, local read/parse/focus, 100% exact checks, bytes/3 token proxy, input-only price; no LLM, hallucination or production code execution',
        'repeats': args.repeats, 'input_price_per_million_usd': args.price_per_million,
        'results': rows}, indent=2) + '\n')
    with (args.out / 'results.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    for r in rows:
        print(f"{r['scenario']:20} {r['format']:4} {r['estimated_full_tokens']:>8} -> {r['estimated_focused_tokens']:>5} tokens_est; retrieval {r['retrieval_p50_ms']:.3f} ms; work order {r['work_order_p50_ms']:.3f} ms")


if __name__ == '__main__':
    main()
