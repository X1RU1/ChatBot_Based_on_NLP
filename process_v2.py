import re
import editdistance
from sklearn.metrics import pairwise_distances
from rdflib import Graph, Namespace, URIRef, Literal, RDFS
import rdflib
import numpy as np
import csv
import process_v3
import process_v4

WD = Namespace('http://www.wikidata.org/entity/')
WDT = Namespace('http://www.wikidata.org/prop/direct/')
SCHEMA = Namespace('http://schema.org/')
DDIS = Namespace('http://ddis.ch/atai/')

# Load the graph
graph = Graph()
graph.parse('./14_graph.nt', format='turtle')

# Load the embeddings
entity_emb = np.load(r'./entity_embeds.npy')
relation_emb = np.load(r'./relation_embeds.npy')

# Load the dictionaries
with open(r'./entity_ids.del', 'r', encoding='utf-8') as ifile:
    ent2id = {rdflib.term.URIRef(ent): int(idx) for idx, ent in csv.reader(ifile, delimiter='\t')}
    id2ent = {v: k for k, v in ent2id.items()}
with open(r'./relation_ids.del', 'r', encoding='utf-8') as ifile:
    rel2id = {rdflib.term.URIRef(rel): int(idx) for idx, rel in csv.reader(ifile, delimiter='\t')}
    id2rel = {v: k for k, v in rel2id.items()}

ent2lbl = {ent: str(lbl) for ent, lbl in graph.subject_objects(RDFS.label)}
lbl2ent = {lbl: ent for ent, lbl in ent2lbl.items()}

# Load entities and predicates from CSV files
entities = {}
predicates = {}

with open('./entities.csv', 'r', encoding='utf-8') as file:
    reader = csv.reader(file)
    next(reader)  # Skip header
    entities = {row[0]: row[1] for row in reader}  # {Entity URI: Entity Name}

with open('./predicates.csv', 'r', encoding='utf-8') as file:
    reader = csv.reader(file)
    next(reader)  # Skip header
    predicates = {row[0]: row[1] for row in reader}  # {Predicate URI: Predicate Name}


def handleQuestion(question) -> (str, str):
    multi_medias = ["picture", "look like", "looks like", "photo"]

    if "recommend" in question.lower():  # Recommendation question
        result = process_v3.handleRecommendation(question)
        return "recommendation", result
    elif any(multi_media in question.lower() for multi_media in multi_medias):  # Multi-media question
        result = process_v4.handleMultiMedia(question)
        return "multi_media", result
    else:
        matched_entity = match_entity(question)
        matched_relation = match_relation(question)

        result = handleFactual(matched_entity, matched_relation)  # Factual question
        if result:  
            return "factual", result
        else:
            result = handleEmbedding(matched_entity, matched_relation)  # Embedding question
            if result:  
                return "embedding", result
                
    return None, None


def match_entity(question):
    """
    Match entities based on entity names in the question.
    """
    # Extract the potential entity from the question
    entity_part = None
    patterns = [
        r"who is the (.+?) of (.+?)\?",
        r"who (.+?)ed (.+?)\?",
        r"when was \"(.+?)\" (.+?)d\?",
        r"what is the (.+?) of (.+?)\?"
    ]
    for pattern in patterns:
        match = re.search(pattern, question.lower())
        if match:
            entity_part = match.group(2) if pattern != r'when was \"(.+?)\" (.+?)d\?' else match.group(1)
            break

    if not entity_part:
        print("No matching pattern found in the question.")
        return None

    # Match against the entities dictionary
    entity = None
    min_distance = float('inf')

    print(f"--- Matching entity for \"{entity_part}\" ---\n")

    for uri, name in entities.items():
        name_lower = name.lower()
        if name_lower == entity_part.lower():
            entity = uri  # Exact match
            print(f"Exact match found: {name} -> {uri}")
            return entity

        # Use edit distance for approximate match
        distance = editdistance.eval(name_lower, entity_part.lower())
        if distance < min_distance:
            min_distance = distance
            entity = uri

    print(f"Closest match found: {entities.get(entity)} with distance {min_distance}")
    return entity


def match_relation(question):
    """
    Match relations based on relation names in the question.
    """
    # Extract the potential relation from the question
    relation_part = None
    patterns = [
        r"who is the (.+?) of",      
        r"who (.+?)ed (.+?)\?",      
        r"when was \"(.+?)\" (.+?)d\?",
        r"what is the (.+?) of"  
    ]
    for pattern in patterns:
        match = re.search(pattern, question.lower())
        if match:
            relation_part = match.group(1) if pattern != r'when was \"(.+?)\" (.+?)d\?' else match.group(2)
            break

    if not relation_part:
        print("No matching relation pattern found in the question.")
        return None

    # Match against the predicates dictionary
    relation = None
    min_distance = float('inf')

    print(f"--- Matching relation for \"{relation_part}\" ---\n")

    for uri, name in predicates.items():
        name_lower = name.lower()
        if name_lower == relation_part.lower():
            relation = uri  # Exact match
            print(f"Exact match found: {name} -> {uri}")
            return relation

        # Use edit distance for approximate match
        distance = editdistance.eval(name_lower, relation_part.lower())
        if distance < min_distance:
            min_distance = distance
            relation = uri

    print(f"Closest match found: {predicates.get(relation)} with distance {min_distance}")
    return relation


def handleFactual(entity, relation):
    query = f"""
    SELECT ?x 
    WHERE {{
        <{entity}> <{relation}> ?y.
        ?y rdfs:label ?x.
    }}
    LIMIT 3
    """

    print(query)  
    return graph.query(query) 


def handleEmbedding(entity, relation):
    """
    Handle embedding-based queries using entity and relation embeddings.
    """
    entity_id = ent2id.get(rdflib.term.URIRef(entity))
    relation_id = rel2id.get(rdflib.term.URIRef(relation))

    if entity_id is None or relation_id is None:
        raise ValueError("Entity or Relation not found in embeddings.")

    head = entity_emb[entity_id]
    pred = relation_emb[relation_id]

    lhs = head + pred
    dist = pairwise_distances(lhs.reshape(1, -1), entity_emb).reshape(-1)
    most_likely = dist.argsort()

    top_3_idxs = most_likely[:3]
    top_3_labels = [ent2lbl.get(id2ent[idx], "No Label") for idx in top_3_idxs]

    return ",".join(top_3_labels)
