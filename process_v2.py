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

def handleQuestion(question) -> (str, str):    # Classify the question types
    multi_medias = ["picture", "look like", "looks like", "photo"]

    if "recommend" in question.lower(): # Recommendation question
        result = process_v3.handleRecommendation(question)
        return "recommendation", result
    elif any(multi_media in question.lower() for multi_media in multi_medias): # Multi-media question
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

def get_graph_nodes():
    nodes = {}
    for node in graph.all_nodes():
        if isinstance(node, URIRef):
            label = graph.value(node, SCHEMA.name) or graph.value(node, RDFS.label)
            if label:
                nodes[node] = label.toPython()
            else:
                nodes[node] = re.sub(str(WD), "", node.toPython())  # Use the URI if no label found
    return nodes

def get_graph_predicates():
    predicates = {}
    for s, p, o in graph:
        if isinstance(p, URIRef):
            # Try to get human-readable label for predicate
            label = graph.value(p, RDFS.label) or graph.value(p, SCHEMA.name)
            if label:
                predicates[p] = label.toPython()  # Add relation with its label
            else:
                predicates[p] = re.sub(str(WDT), "", p.toPython())  # Use ID if no label found
    return predicates

def match_entity(question):
    factual_patterns = [
        r"who is the (.+?) of (.+?)\?",
        r"who (.+?)ed (.+?)\?",
        r"when was \"(.+?)\" (.+?)d\?",
        r"what is the (.+?) of (.+?)\?"
    ]

    entity_part = None
    for pattern in factual_patterns:
        match = re.search(pattern, question.lower())
        if match:
            if pattern == r'when was \"(.+?)\" (.+?)d\?':
                entity_part = match.group(1).strip()  # For "when was" pattern, entity is in group 1
            else:
                entity_part = match.group(2).strip()  # For other patterns, entity is in group 2
            break

    if not entity_part:
        print("No matching pattern found in question.")
        return None

    # First, try to find an exact match for the entity
    nodes = get_graph_nodes()  # Get nodes with their labels
    entity = None
    min_distance = float('inf')

    print("--- Entity matching for \"{}\"\n".format(entity_part))

    for key, value in nodes.items():
        value_lower = value.lower()  # Compare the label of the entity, not the ID
        if value_lower == entity_part.lower():
            entity = key  # Exact match found
            print(f"Exact match found: {value} -> {key}")
            return entity  # Return the URI of the exact match

    # If no exact match, fall back to similarity-based matching using edit distance
    print("No exact match found. Attempting similarity-based match...")
    for key, value in nodes.items():
        value_lower = value.lower()
        distance = editdistance.eval(value_lower, entity_part.lower())
        if distance < min_distance:
            min_distance = distance
            entity = key  # Return the URI of the closest matching entity

    print(f"Closest match found using edit distance: {ent2lbl.get(entity, entity)} with distance {min_distance}")

    return entity

def match_relation(question):
    relation_patterns = [
        r"who is the (.+?) of",      
        r"who (.+?)ed (.+?)\?",      
        r"when was \"(.+?)\" (.+?)d\?",
        r"what is the (.+?) of"  
    ]
    
    relation_part = None
    for pattern in relation_patterns:
        match = re.search(pattern, question.lower())
        if match:
            if pattern == r'when was \"(.+?)\" (.+?)d\?':
                relation_part = match.group(2).strip()  # For "when was" pattern, relation is in group 2
            else:
                relation_part = match.group(1).strip()  # For other patterns, relation is in group 1
            break
    
    if not relation_part:
        print("No matching relation pattern found in question.")
        return None
    
    # First, try to find an exact match for the relation
    predicates = get_graph_predicates()  # Get available predicates (relations)
    relation = None
    min_distance = float('inf')

    print("\n--- Relation matching for \"{}\"\n".format(relation_part))
    
    # Check for exact match
    for key, value in predicates.items():
        value_lower = value.lower()
        if value_lower == relation_part.lower():
            relation = key  # Exact match found
            print(f"Exact match found: {value} -> {key}")
            return relation

    # If no exact match, fall back to similarity-based matching using edit distance
    print("No exact match found. Attempting similarity-based match...")
    for key, value in predicates.items():
        value_lower = value.lower()
        distance = editdistance.eval(value_lower, relation_part.lower())
        if distance < min_distance:
            min_distance = distance
            relation = key  # Return the URI of the closest matching relation

    print(f"Closest match found using edit distance: {predicates.get(relation, relation)} with distance {min_distance}")
    return relation

def handleEmbedding(entity, relation):    
    # Check if the full URI format is required for entity lookup
    if entity in ent2id:
        entity_id = ent2id[entity]
    else:
        # Handle shortened form if necessary
        if entity.startswith("http://www.wikidata.org/entity/"):
            entity_short = entity.replace("http://www.wikidata.org/entity/", "WD.")
            if entity_short in ent2id:
                entity_id = ent2id[entity_short]
            else:
                raise ValueError(f"Entity '{entity}' not found in ent2id")
        else:
            raise ValueError(f"Entity '{entity}' not found in ent2id")
        
    # Similar checks for relations
    if relation in rel2id:
        relation_id = rel2id[relation]
    else:
        if relation.startswith("http://www.wikidata.org/prop/direct/"):
            relation_short = relation.replace("http://www.wikidata.org/prop/direct/", "WDT.")
            if relation_short in rel2id:
                relation_id = rel2id[relation_short]
            else:
                raise ValueError(f"Relation '{relation}' not found in rel2id")
        else:
            raise ValueError(f"Relation '{relation}' not found in rel2id")
        
    # Proceed with embedding operations
    head = entity_emb[entity_id]
    pred = relation_emb[relation_id]

    lhs = head + pred
    dist = pairwise_distances(lhs.reshape(1, -1), entity_emb).reshape(-1)
    most_likely = dist.argsort()

    top_3_idxs = most_likely[:3]
    top_3_labels = [ent2lbl.get(id2ent[idx], "No Label") for idx in top_3_idxs]

    return ",".join(top_3_labels)
