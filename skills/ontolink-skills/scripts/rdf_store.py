"""Small named-node RDF/XML store. Not a general RDF parser or OWL reasoner."""
from pathlib import Path
import xml.etree.ElementTree as ET

RDF = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
OWL = 'http://www.w3.org/2002/07/owl#'
O = 'urn:ontolink:'
XSD = 'http://www.w3.org/2001/XMLSchema#'
TYPE = RDF + 'type'
ET.register_namespace('rdf', RDF)
ET.register_namespace('ol', O)


class Store:
    def __init__(self):
        self.triples = set()

    def add(self, subject, predicate, value, resource=False):
        self.triples.add((subject, predicate, str(value), bool(resource)))

    def set(self, subject, predicate, value, resource=False):
        self.triples = {t for t in self.triples if t[:2] != (subject, predicate)}
        self.add(subject, predicate, value, resource)

    def values(self, subject, predicate):
        return sorted(t[2] for t in self.triples if t[:2] == (subject, predicate))

    def one(self, subject, predicate, default=None):
        values = self.values(subject, predicate)
        if len(values) > 1:
            raise ValueError(f'Multiple values for {predicate} on {subject}')
        return values[0] if values else default

    def typed(self, kind):
        return sorted(t[0] for t in self.triples if t[1:] == (TYPE, O + kind, True))

    def has_type(self, subject, kind):
        return (subject, TYPE, O + kind, True) in self.triples

    def subjects(self):
        return {t[0] for t in self.triples}

    @classmethod
    def read(cls, path):
        raw = Path(path).read_bytes()
        if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
            raise ValueError('DTD and entity declarations are unsupported')
        root = ET.fromstring(raw)
        if root.tag != '{' + RDF + '}RDF':
            raise ValueError('Expected named-node RDF/XML')
        if root.attrib:
            raise ValueError('Root attributes such as xml:base are unsupported')
        graph = cls()
        for node in root:
            if set(node.attrib) != {'{' + RDF + '}about'}:
                raise ValueError('Every node needs an absolute rdf:about; blank nodes are unsupported')
            subject = node.attrib['{' + RDF + '}about']
            if ':' not in subject:
                raise ValueError('Relative subjects are unsupported')
            if node.tag != '{' + RDF + '}Description':
                ns, local = node.tag[1:].split('}', 1)
                graph.add(subject, TYPE, ns + local, True)
            for prop in node:
                ns, local = prop.tag[1:].split('}', 1)
                if len(prop):
                    raise ValueError('Nested/anonymous RDF/XML nodes are unsupported')
                resource = prop.attrib.get('{' + RDF + '}resource')
                if resource is not None:
                    if set(prop.attrib) != {'{' + RDF + '}resource'} or ':' not in resource:
                        raise ValueError('Invalid resource property')
                    graph.add(subject, ns + local, resource, True)
                else:
                    if set(prop.attrib) - {'{' + RDF + '}datatype', '{http://www.w3.org/XML/1998/namespace}lang'}:
                        raise ValueError('Unsupported RDF/XML property attributes')
                    graph.add(subject, ns + local, prop.text or '')
        return graph

    def write(self, path):
        root = ET.Element('{' + RDF + '}RDF')
        for subject in sorted(self.subjects()):
            triples = sorted(t for t in self.triples if t[0] == subject)
            types = [t for t in triples if t[1] == TYPE and t[3] and t[2].startswith(O)]
            typed = len(types) == 1
            tag = '{' + O + '}' + types[0][2][len(O):] if typed else '{' + RDF + '}Description'
            node = ET.SubElement(root, tag, {'{' + RDF + '}about': subject})
            for _, predicate, value, resource in triples:
                if typed and predicate == TYPE and resource and value == types[0][2]:
                    continue
                if predicate.startswith(O):
                    tag = '{' + O + '}' + predicate[len(O):]
                elif predicate.startswith(RDF):
                    tag = '{' + RDF + '}' + predicate[len(RDF):]
                else:
                    raise ValueError('State writer only supports the project and RDF vocabularies')
                prop = ET.SubElement(node, tag)
                if resource:
                    prop.set('{' + RDF + '}resource', value)
                else:
                    local = predicate[len(O):] if predicate.startswith(O) else ''
                    # RDF 1.1 plain text is already xsd:string; preserve non-string types.
                    dtype = {'revision': 'integer', 'order': 'integer', 'weight': 'decimal', 'value': 'decimal', 'calibrated': 'boolean', 'blocking': 'boolean', 'createdAt': 'dateTime'}.get(local)
                    if dtype:
                        prop.set('{' + RDF + '}datatype', XSD + dtype)
                    prop.text = value
        ET.indent(root)
        ET.ElementTree(root).write(path, encoding='utf-8', xml_declaration=True)
