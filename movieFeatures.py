import pandas as pd
from rdflib import Graph, Namespace, URIRef, RDFS

# Namespaces
WD = Namespace('http://www.wikidata.org/entity/')
WDT = Namespace('http://www.wikidata.org/prop/direct/')

# Load your knowledge graph
graph = Graph()
graph.parse('./14_graph.nt', format='turtle')

# Step 1: Extract Predicate-Object Pairs for Each Movie
def get_movie_features(movie_uri):
    """Extract predicates and values for a given movie URI."""
    features = []   # Predicates
    values = []     # Values corresponding to predicates
    for predicate, obj in graph.predicate_objects(URIRef(movie_uri)):
        if str(predicate).startswith(str(WDT)):  # Only include predicates in WDT namespace
            features.append(str(predicate))
            values.append(str(obj))
    return features, values

# Mapping the predicate URIs to human-readable names (column names)
predicate_to_column = {
    'http://www.wikidata.org/prop/direct/P57': 'director',
    'http://www.wikidata.org/prop/direct/P136': 'genre',
    'http://www.wikidata.org/prop/direct/P123': 'publisher',
    'http://www.wikidata.org/prop/direct/P577': 'publication date'
}

# Step 2: Iterate over the movies and extract their features
movie_data = {}  # Dictionary to store movie titles and their respective feature-value pairs

# Loop through all the movie URIs (assuming that movies are in the WD namespace)
for movie_uri in graph.subjects(predicate=RDFS.label):
    # Extract movie title
    title = None
    for label in graph.objects(movie_uri, RDFS.label):
        if isinstance(label, str):
            title = label
            break
    
    if title:
        # Get the features and values for the movie
        features, values = get_movie_features(movie_uri)
        movie_data[title] = {'features': features, 'values': values}

# Step 3: Convert movie data into a DataFrame
data = []  # List to store rows for the DataFrame

# Iterate over the movie data
for title, feature_value in movie_data.items():
    row = {'Title': title}
    # Filter the feature-value pairs and map the predicate URIs to human-readable column names
    for feature, value in zip(feature_value['features'], feature_value['values']):
        # Check if the feature is in the desired mapping
        if feature in predicate_to_column:
            # Map the feature URI to the column name
            column_name = predicate_to_column[feature]
            # Check if the value is a URI (WD entity)
            if value.startswith(str(WD)):
                # Retrieve the real name of the entity (if it's an entity URI in WD namespace)
                real_name = None
                for label in graph.objects(URIRef(value), RDFS.label):
                    if isinstance(label, str):
                        real_name = label
                        break
                row[column_name] = real_name if real_name else value
            else:
                # If not a URI, just assign the value directly
                row[column_name] = value
    data.append(row)

# Convert the data to a DataFrame
df = pd.DataFrame(data)

# Step 4: Save the DataFrame to a CSV file
df.to_csv('./movie_features.csv', index=False)

print("Data saved to movie_features.csv")
