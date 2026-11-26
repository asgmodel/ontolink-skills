"""Python-only task search: RDF is parsed locally, output is a few ranked task IDs.

Deterministic multilingual lexical ranking. No LLM, embeddings or extra index
files; do not describe this method as full semantic understanding.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from difflib import get_close_matches
import math
import re
import unicodedata
from rdf_store import O, TYPE

TOKEN_RE = re.compile(r"[a-z0-9]+|[\u0621-\u064a]+")
MARKS_RE = re.compile(r"[\u064b-\u065f\u0670\u0640]")
ALIASES = {
    "login": ("login", "signin", "auth", "authentication", "دخول",
              "الدخول", "تسجيل", "التسجيل", "مصادقه", "المصادقه"),
    "signup": ("signup", "register", "registration", "انشاء", "حساب", "حسابات"),
    "database": ("db", "sql", "database", "databases", "قاعده", "القاعده", "بيانات"),
    "whatsapp": ("whatsapp", "واتساب", "الواتساب", "واتس"),
    "azure": ("azure", "ازور", "الازور"),
    "deploy": ("deploy", "deployment", "publish", "نشر", "النشر", "رفع"),
    "issue": ("fix", "repair", "error", "bug", "اصلاح", "مشكله", "الخطا"),
    "message": ("message", "messages", "رساله", "رسائل", "الرسائل"),
}
_LOOKUP = {term: canonical for canonical, terms in ALIASES.items() for term in terms}
_FIELDS = {'title', 'summary', 'phase', 'owner', 'status'}


def normalized(text):
    value = unicodedata.normalize('NFKC', str(text or '')).lower()
    value = MARKS_RE.sub('', value)
    return value.translate(str.maketrans('أإآٱىة', 'اااايه'))


def tokenize(text):
    return [_LOOKUP.get(term, term) for term in TOKEN_RE.findall(normalized(text))
            if len(term) > 1]


def _catalog(graph):
    """Scan triples once, instead of scanning the whole graph per task/property."""
    nodes = defaultdict(dict)
    tasks = set()
    for subject, pred, value, resource in graph.triples:
        if pred == TYPE and resource and value == O + 'Task':
            tasks.add(subject)
        elif pred.startswith(O) and pred[len(O):] in _FIELDS and not resource:
            nodes[subject][pred[len(O):]] = value
        elif pred == O + 'phase' and resource:
            nodes[subject]['phase'] = value
    return [dict(node=node, id=node.rsplit('/', 1)[-1],
                 title=nodes[node].get('title', ''),
                 status=nodes[node].get('status', ''),
                 phase=nodes[node].get('phase', ''),
                 summary=nodes[node].get('summary', ''))
            for node in sorted(tasks)]


def smart_search_tasks(graph, query, limit=5):
    """Bounded, ranked task search over the canonical graph (no JSON/index reads)."""
    if not isinstance(query, str) or not query.strip() or len(query) > 500:
        raise ValueError('Query must be nonempty and <=500 characters')
    if not isinstance(limit, int) or not 1 <= limit <= 20:
        raise ValueError('Search limit must be between 1 and 20')
    tasks = _catalog(graph)
    if not tasks:
        return []
    postings, df, fields_by_task = defaultdict(set), Counter(), []
    lengths = []
    for pos, task in enumerate(tasks):
        fields = {key: Counter(tokenize(task[key])) for key in ('id', 'title', 'summary')}
        fields_by_task.append(fields)
        length = sum(sum(v.values()) for v in fields.values())
        lengths.append(length)
        for term in set().union(*(set(v) for v in fields.values())):
            postings[term].add(pos)
            df[term] += 1
    q = list(dict.fromkeys(tokenize(query)))
    if not q:
        return []
    vocabulary = list(postings)
    matches = []
    for term in q:
        if term in postings:
            matches.append((term, 1.0))
        elif len(term) >= 4:
            matches.extend((candidate, .65) for candidate in
                           get_close_matches(term, vocabulary, n=1, cutoff=.8))
    if not matches:
        return []
    candidates = set()
    for term, _ in matches:
        candidates.update(postings[term])
    average = max(sum(lengths) / len(tasks), 1)
    q_id = normalized(query).strip().replace(' ', '-').replace('_', '-')
    normalized_q = ' '.join(q)
    ranked = []
    for pos in candidates:
        task, fields = tasks[pos], fields_by_task[pos]
        score, matching = 0., set()
        for term, certainty in matches:
            frequency = 4 * fields['id'][term] + 3 * fields['title'][term] + fields['summary'][term]
            if not frequency:
                continue
            matching.add(term)
            idf = math.log(1 + (len(tasks) - df[term] + .5) / (df[term] + .5))
            score += certainty * idf * frequency * 2.5 / (frequency + 1.5 * (.25 + .75 * lengths[pos] / average))
        score *= 1 + .5 * len(matching) / max(1, len(matches))
        if normalized(task['id']) == q_id:
            score += 100
        if ' '.join(tokenize(task['title'])) == normalized_q:
            score += 30
        ranked.append((score, task))
    ranked.sort(key=lambda item: (-item[0], item[1]['id']))
    return [{'id': item['id'], 'title': item['title'], 'status': item['status'],
             'phase': item['phase'].removeprefix(O)} for _, item in ranked[:limit]]
