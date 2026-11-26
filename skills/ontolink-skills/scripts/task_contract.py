"""Single source of truth for the OntoLink task JSON v4 detail sections.

The bundled JSON template documents ALL supported fields. Generated task records
OMIT empty optional sections. Confidence assesses support for a claim; likelihood
assesses a named event over a defined time horizon. They are not interchangeable.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

FORMAT_VERSION = 4
LIST_SECTIONS = (
    'actors', 'artifacts', 'assessments', 'blockers', 'communication',
    'contracts', 'decisions', 'evidence', 'files', 'proofs', 'recommendations',
    'requirements', 'risks', 'testResults', 'warnings', 'inputs', 'outputs',
    'steps', 'reports', 'confidence', 'likelihood',
)
TASK_DETAILS = set(LIST_SECTIONS) | {'lastUpdate', 'timestamps'}
TEMPLATE = Path(__file__).resolve().parents[1] / 'assets' / 'task-template.json'
_ALLOWED_TIMES = {'startedAt', 'dueAt', 'completedAt'}
_REQUIRED_BASE = {'method', 'rationale', 'calibrated'}


def validate_sections(document):
    """Validate task-only metadata without introducing extra storage files."""
    version = document.get('formatVersion')
    if version not in (2, 3, FORMAT_VERSION):
        raise ValueError('Unknown task JSON formatVersion')
    if version == FORMAT_VERSION:
        allowed = {'formatVersion', 'id', 'type', 'uri', 'revision',
                   'updatedAt', 'properties', 'relationships'} | TASK_DETAILS
        unknown = set(document) - allowed
        if unknown:
            raise ValueError('Unknown task fields: ' + ', '.join(sorted(unknown)))
    for key in LIST_SECTIONS:
        value = document.get(key)
        if value is None:
            continue
        if not isinstance(value, list):
            raise ValueError('Task section must be an array: ' + key)
        signatures = set()
        for item in value:
            signature = json.dumps(item, sort_keys=True, ensure_ascii=False)
            if signature in signatures:
                raise ValueError('Duplicate task item in ' + key)
            signatures.add(signature)
            if key in {'confidence', 'likelihood'}:
                validate_assessment(key, item)
    # Events are a deprecated history log; only the newest update is retained.
    if version == FORMAT_VERSION:
        if document.get('events') is not None or document.get('resourceFields') is not None:
            raise ValueError('Task history and redundant resourceFields are forbidden')
    if 'lastUpdate' in document and not isinstance(document['lastUpdate'], (str, dict)):
        raise ValueError('lastUpdate must be string or object')
    times = document.get('timestamps')
    if times is not None:
        if not isinstance(times, dict) or set(times) - _ALLOWED_TIMES:
            raise ValueError('timestamps accepts only startedAt/dueAt/completedAt')
        for key, value in times.items():
            if not isinstance(value, str) or not value.strip():
                raise ValueError('Task timestamp must be a nonempty ISO-8601 string: ' + key)
            from datetime import datetime
            try:
                datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError as error:
                raise ValueError('Invalid ISO-8601 timestamp: ' + key) from error
    for kind in ('reports', 'warnings', 'blockers', 'risks'):
        if kind not in document:
            continue
        # One incident ID must not be silently copied across multiple categories.
        ids = [entry['id'] for entry in document[kind]
               if isinstance(entry, dict) and isinstance(entry.get('id'), str)]
        if len(ids) != len(set(ids)):
            raise ValueError('Duplicate signal ID within ' + kind)
    signals = {}
    for key in ('reports', 'warnings', 'blockers', 'risks'):
        for item in document.get(key, []):
            if not isinstance(item, dict) or not item.get('id'):
                continue
            ident = item['id']
            if ident in signals and signals[ident] != key:
                raise ValueError('A signal must have one category: ' + ident)
            signals[ident] = key
    # Do not represent the same assessment twice in assessments + typed sections.
    seen = {}
    for key in ('assessments', 'confidence', 'likelihood'):
        for item in document.get(key, []):
            ident = item.get('id') if isinstance(item, dict) else None
            if ident:
                if ident in seen:
                    raise ValueError('Duplicate assessment ID: ' + str(ident))
                seen[ident] = key
    return True


def validate_assessment(kind, item):
    if not isinstance(item, dict):
        raise ValueError(kind + ' entries must be objects')
    required = _REQUIRED_BASE | ({'target'} if kind == 'confidence'
                                  else {'eventScope', 'timeHorizon'})
    if not required <= set(item):
        raise ValueError(kind + ' missing required basis: ' +
                         ', '.join(sorted(required - set(item))))
    for field in required - {'calibrated'}:
        if not isinstance(item[field], str) or not item[field].strip():
            raise ValueError(kind + '.' + field + ' must be nonempty text')
    if not isinstance(item['calibrated'], bool):
        raise ValueError(kind + '.calibrated must be boolean')
    if 'value' in item:
        value = item['value']
        if isinstance(value, bool) or not isinstance(value, (int, float)) or (
                not math.isfinite(value) or not 0 <= value <= 1):
            raise ValueError(kind + '.value must be a finite number in [0, 1]')
    return True


def template():
    return json.loads(TEMPLATE.read_text(encoding='utf-8'))
