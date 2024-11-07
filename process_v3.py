from transformers import pipeline
import process_v2
import pandas as pd
from sklearn.neighbors import NearestNeighbors
from sklearn.feature_extraction.text import TfidfVectorizer

# Load movie features from the CSV file
df = pd.read_csv('./movie_features.csv')

# Fill NaN values with an empty string for vectorization
df = df.fillna('')

# Combine the features into a single column for vectorization (you can include more columns if needed)
df['combined_features'] = df['director'] + ' ' + df['genre'] + ' ' + df['publisher'] + ' ' + df['publication date'] 

# Vectorization using TF-IDF
vectorizer = TfidfVectorizer(stop_words='english')
X = vectorizer.fit_transform(df['combined_features'])

# Fit KNN model
knn = NearestNeighbors(n_neighbors=5, metric='cosine')
knn.fit(X)

def handleRecommendation(question):
    ner_pipeline = pipeline('ner', model='dbmdz/bert-large-cased-finetuned-conll03-english')
    entities = ner_pipeline(question, aggregation_strategy="simple")

    # Extract movie names (entities) from NER
    favorite_movies = [entity['word'] for entity in entities]
    
    # Search for these movies in the DataFrame and get their indices
    movie_indices = []
    for movie in favorite_movies:
        matched_movies = df[df['Title'].str.contains(movie, case=False)]
        if not matched_movies.empty:
            movie_indices.append(matched_movies.index[0])

    # If there are favorite movies, find similar movies using KNN
    recommendations = []
    if movie_indices:
        # Get the feature vectors of the favorite movies
        movie_features = X[movie_indices]
        
        # Get KNN recommendations for these movies
        distances, indices = knn.kneighbors(movie_features)
        
        # Collect the recommended movie titles
        for idx_list in indices:
            for idx in idx_list:
                recommendations.append(df.iloc[idx]['Title'])
        
        # Remove duplicates from the recommendations
        recommendations = list(set(recommendations))
        entities = ner_pipeline(', '.join(recommendations), aggregation_strategy="simple")

        # Extract movie names (entities) from NER
        recommendations = [entity['word'] for entity in entities]
    
    return ', '.join(recommendations)

