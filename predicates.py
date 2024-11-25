import csv
from rdflib import Graph, RDFS

# Load the graph
graph = Graph()
graph.parse('./14_graph.nt', format='turtle')

# Extract predicates and their corresponding labels (if available)
predicates = set()  # Use a set to avoid duplicates
for predicate in graph.predicates():
    # Look for a label for the predicate
    label = None
    for _, _, obj in graph.triples((predicate, RDFS.label, None)):
        label = str(obj)  # Extract label as a string if present
    
    predicates.add((str(predicate), label if label else 'No label'))  # Add to set (automatically removes duplicates)

# Write the results into a CSV file
with open('predicates.csv', mode='w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    # Write the header
    writer.writerow(['Predicate URI', 'Predicate Name'])
    # Write the predicate URI and name rows
    for predicate_uri, predicate_name in predicates:
        writer.writerow([predicate_uri, predicate_name])

print("Predicate names and URIs have been written to predicates.csv (duplicates removed).")
