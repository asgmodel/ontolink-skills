"""Local retrieval across canonical OntoLink knowledge and a generated code index.

The canonical state and generated index stay separate. Retrieval may rank both,
but generated index hits never become canonical project facts automatically.
"""
from __future__ import annotations

from collections import Counter, defaultdict, deque
from dataclasses import dataclass
import math
import re

from rdf_store import O, TYPE

TOKEN = re.compile(r"[A-Za-z0-9_./:-]+|[\u0600-\u06FF]+")
CORE_TEXT_FIELDS = ('title', 'summary', 'kind', 'path', 'rationale', 'basis', 'role')
INDEX_TEXT_FIELDS = (
    'path', 'summary', 'language', 'symbolName', 'qualifiedName', 'signature',
    'httpMethod', 'route', 'type',
)
GRAPH_PREDICATES = {
    O + 'dependsOn', O + 'usesArtifact', O + 'derivedFrom', O + 'satisfies',
    O + 'affects', O + 'supports', O + 'assesses', O + 'source', O + 'target',
}


def tokenize(text: str) -> list[str]:
    return [x.lower() for x in TOKEN.findall(text or '') if len(x) > 1]


def _short(node: str) -> str:
    return node.rsplit('/', 1)[-1]


def core_documents(graph) -> list[dict]:
    docs = []
    for node in sorted(graph.subjects()):
        types = graph.values(node, TYPE)
        kind = types[0].removeprefix(O) if types else 'Unknown'
        parts = [_short(node), kind]
        for field in CORE_TEXT_FIELDS:
            parts.extend(graph.values(node, O + field))
        docs.append({'key': 'core:' + node, 'source': 'knowledge', 'node': node, 'type': kind, 'text': ' '.join(parts)})
    return docs


def index_documents(index_data: dict | None) -> list[dict]:
    docs = []
    for record in (index_data or {}).get('records', []):
        parts = []
        for field in INDEX_TEXT_FIELDS:
            value = record.get(field)
            if isinstance(value, list):
                parts.extend(str(x) for x in value)
            elif value is not None:
                parts.append(str(value))
        docs.append({
            'key': 'index:' + record['id'], 'source': 'index', 'node': record['id'],
            'type': record.get('type', 'Unknown'), 'text': ' '.join(parts), 'record': record,
        })
    return docs


class BM25:
    def __init__(self, documents: list[dict], k1: float = 1.5, b: float = 0.75):
        self.documents = documents
        self.k1 = k1
        self.b = b
        self.tf = {}
        self.df = Counter()
        self.lengths = {}
        for doc in documents:
            counts = Counter(tokenize(doc['text']))
            self.tf[doc['key']] = counts
            self.lengths[doc['key']] = sum(counts.values())
            for token in counts:
                self.df[token] += 1
        self.avgdl = sum(self.lengths.values()) / max(1, len(documents))

    def scores(self, query: str) -> dict[str, float]:
        scores = defaultdict(float)
        count = max(1, len(self.documents))
        for term in tokenize(query):
            df = self.df.get(term, 0)
            if not df:
                continue
            idf = math.log(1 + (count - df + 0.5) / (df + 0.5))
            for doc in self.documents:
                key = doc['key']
                frequency = self.tf[key].get(term, 0)
                if not frequency:
                    continue
                length = self.lengths[key]
                denom = frequency + self.k1 * (1 - self.b + self.b * length / max(self.avgdl, 1e-9))
                scores[key] += idf * (frequency * (self.k1 + 1)) / denom
        return scores


@dataclass
class SearchHit:
    source: str
    id: str
    type: str
    score: float
    lexical: float
    graph: float
    node: str | None = None
    record: dict | None = None

    def as_dict(self):
        data = {
            'source': self.source, 'id': self.id, 'type': self.type,
            'score': round(self.score, 6),
            'components': {'lexical': round(self.lexical, 6), 'graph': round(self.graph, 6)},
        }
        if self.source == 'knowledge':
            data['node'] = self.node
        else:
            for key in ('path', 'symbolName', 'qualifiedName', 'signature', 'httpMethod', 'route', 'lineStart', 'language', 'summary', 'indexMethod'):
                if self.record and key in self.record:
                    data[key] = self.record[key]
        return data


def _core_neighbors(graph, seeds: set[str], max_hops: int = 1) -> dict[str, float]:
    if not seeds or max_hops < 1:
        return {}
    found = {seed: 0 for seed in seeds}
    queue = deque(seeds)
    triples = list(graph.triples)
    while queue:
        node = queue.popleft()
        depth = found[node]
        if depth >= max_hops:
            continue
        for subject, predicate, value, resource in triples:
            if not resource or predicate not in GRAPH_PREDICATES:
                continue
            other = None
            if subject == node:
                other = value
            elif value == node:
                other = subject
            if other and other not in found:
                found[other] = depth + 1
                queue.append(other)
    return {node: 1.0 / (distance + 1) for node, distance in found.items() if distance > 0}


def search(graph, index_data: dict | None, query: str, limit: int = 10, graph_hops: int = 1,
           only_tasks: bool = False) -> list[SearchHit]:
    if not 1 <= limit <= 50:
        raise ValueError('Search limit must be between 1 and 50')
    documents = core_documents(graph)
    if only_tasks:
        documents = [item for item in documents if item['type'] == 'Task']
        graph_hops = 0  # Avoid adjacent non-task hits and wasted context tokens.
    else:
        documents += index_documents(index_data)
    by_key = {doc['key']: doc for doc in documents}
    lexical_raw = BM25(documents).scores(query)
    max_lex = max(lexical_raw.values(), default=1.0)

    core_seed_nodes = {
        by_key[key]['node'] for key in sorted(lexical_raw, key=lexical_raw.get, reverse=True)[: max(10, limit * 2)]
        if by_key[key]['source'] == 'knowledge'
    }
    graph_scores = _core_neighbors(graph, core_seed_nodes, graph_hops)

    hits = []
    for doc in documents:
        lex = lexical_raw.get(doc['key'], 0.0) / max_lex if max_lex else 0.0
        graph_score = graph_scores.get(doc['node'], 0.0) if doc['source'] == 'knowledge' else 0.0
        score = 0.8 * lex + 0.2 * graph_score
        if score <= 0:
            continue
        hits.append(SearchHit(
            source=doc['source'], id=_short(doc['node']), type=doc['type'], score=score,
            lexical=lex, graph=graph_score, node=doc['node'] if doc['source'] == 'knowledge' else None,
            record=doc.get('record'),
        ))
    hits.sort(key=lambda hit: (-hit.score, hit.source, hit.id))
    return hits[:limit]
