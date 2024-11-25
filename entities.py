import csv
from rdflib import Graph, RDFS

# Load the graph
graph = Graph()
graph.parse('./14_graph.nt', format='turtle')

# Extract entity URIs and their corresponding labels
entities = []
for entity, label in graph.subject_objects(RDFS.label):
    # Convert to string to ensure compatibility (e.g., for URIs)
    entities.append((str(entity), str(label)))

# Write the results into a CSV file
with open('./entities.csv', mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    # Write the header
    writer.writerow(['Entity URI', 'Entity Name'])
    # Write the entity URI and name rows
    for entity_uri, entity_name in entities:
        writer.writerow([entity_uri, entity_name])

print("Entity names and URIs have been written to entities.csv.")
