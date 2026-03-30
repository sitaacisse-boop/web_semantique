"""
query_parser.py
Parsing des requêtes SPARQL et extraction des BGP (Basic Graph Patterns).
Extrait les classes et propriétés mentionnées dans chaque requête.
"""

import re
from typing import List, Tuple, Set

RDF_TYPE_URIS = {
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
    "rdf:type",
    "a",
}

# Namespaces courants pour résolution de préfixes
WELL_KNOWN_PREFIXES = {
    "rdf":  "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "owl":  "http://www.w3.org/2002/07/owl#",
    "xsd":  "http://www.w3.org/2001/XMLSchema#",
    "foaf": "http://xmlns.com/foaf/0.1/",
    "dbo":  "http://dbpedia.org/ontology/",
    "dbp":  "http://dbpedia.org/property/",
    "schema": "http://schema.org/",
}


class SPARQLQueryParser:
    """
    Parse les requêtes SPARQL pour en extraire les BGP.
    Approche : analyse lexicale + régulière (robuste sans dépendance lourde).
    """

    def __init__(self, schema_graph=None):
        self.schema = schema_graph  # RDFSchemaGraph (optionnel)

    # ------------------------------------------------------------------
    # Interface principale
    # ------------------------------------------------------------------

    def extract_bgp(self, query: str) -> Tuple[Set[str], Set[str]]:
        """
        Retourne (classes, propriétés) extraites du BGP de la requête.
        """
        prefixes = self._extract_prefixes(query)
        triples = self._extract_triple_patterns(query)

        classes: Set[str] = set()
        properties: Set[str] = set()

        for subj, pred, obj in triples:
            pred_full = self._resolve(pred, prefixes)
            obj_full = self._resolve(obj, prefixes)

            if pred_full in RDF_TYPE_URIS or pred == "a":
                # ?x rdf:type <Classe>
                if not obj_full.startswith("?") and obj_full:
                    classes.add(obj_full)
            else:
                if pred_full and not pred_full.startswith("?"):
                    properties.add(pred_full)
                    # Inférence des classes via domain/range du schéma
                    if self.schema:
                        domain, range_ = self.schema.get_domain_range(pred_full)
                        if domain:
                            classes.add(domain)
                        if range_:
                            classes.add(range_)

        return classes, properties

    # ------------------------------------------------------------------
    # Extraction des préfixes déclarés dans la requête
    # ------------------------------------------------------------------

    def _extract_prefixes(self, query: str) -> dict:
        prefixes = dict(WELL_KNOWN_PREFIXES)
        pattern = re.compile(
            r'PREFIX\s+([\w\-]*)\s*:\s*<([^>]+)>', re.IGNORECASE
        )
        for alias, uri in pattern.findall(query):
            prefixes[alias] = uri
        return prefixes

    # ------------------------------------------------------------------
    # Extraction des triplets du corps WHERE { ... }
    # ------------------------------------------------------------------

    def _extract_triple_patterns(self, query: str) -> List[Tuple[str, str, str]]:
        """
        Extrait les triplets (s, p, o) du bloc WHERE de la requête.
        Gère : <URI>, ?var, prefix:local, et le mot-clé 'a'.
        """
        # Isoler le contenu du WHERE
        where_match = re.search(r'WHERE\s*\{(.*)\}', query, re.IGNORECASE | re.DOTALL)
        if not where_match:
            return []
        where_body = where_match.group(1)

        # Supprimer les sous-requêtes, FILTER, OPTIONAL (simplifié)
        where_body = re.sub(r'FILTER\s*\([^)]*\)', '', where_body, flags=re.IGNORECASE)
        where_body = re.sub(r'OPTIONAL\s*\{[^}]*\}', '', where_body, flags=re.IGNORECASE)

        triples = []
        # Motif pour un terme SPARQL : <URI>, ?var, ou prefix:local ou 'a'
        term = r'(?:<[^>]+>|\?[\w\-]+|[\w\-]+:[\w\-]+|a(?=\s))'
        pattern = re.compile(
            rf'({term})\s+({term})\s+({term})\s*[;,.]?'
        )
        for m in pattern.finditer(where_body):
            s, p, o = m.group(1), m.group(2), m.group(3)
            triples.append((s.strip(), p.strip(), o.strip()))

        return triples

    # ------------------------------------------------------------------
    # Résolution des URIs (préfixes → URI complète)
    # ------------------------------------------------------------------

    def _resolve(self, term: str, prefixes: dict) -> str:
        if term.startswith("<") and term.endswith(">"):
            return term[1:-1]
        if term.startswith("?"):
            return term
        if term == "a":
            return "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
        if ":" in term:
            prefix, local = term.split(":", 1)
            if prefix in prefixes:
                return prefixes[prefix] + local
        return term


# ------------------------------------------------------------------
# Chargement d'un fichier de requêtes (séparées par lignes vides ou '#')
# ------------------------------------------------------------------

def load_queries(filepath: str) -> List[str]:
    """
    Charge les requêtes SPARQL depuis un fichier texte.
    Les requêtes sont séparées par des lignes vides.
    Les lignes commençant par '#' sont des commentaires de séparation.
    """
    queries = []
    current = []
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            # Commentaire de séparation entre requêtes
            if stripped.startswith("#") and current:
                q = "\n".join(current).strip()
                if "WHERE" in q.upper():
                    queries.append(q)
                current = []
            elif stripped.startswith("#"):
                continue
            elif stripped == "" and current:
                q = "\n".join(current).strip()
                if "WHERE" in q.upper():
                    queries.append(q)
                current = []
            else:
                current.append(line.rstrip())
    if current:
        q = "\n".join(current).strip()
        if "WHERE" in q.upper():
            queries.append(q)
    return queries
