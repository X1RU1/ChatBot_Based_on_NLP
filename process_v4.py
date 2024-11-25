from transformers import pipeline
import requests
import csv
import pandas as pd
import json
import random


# Load the CSV files into DataFrames for easy querying
entities_df = pd.read_csv("./entities.csv")

def handleMultiMedia(question):
    ner_pipeline = pipeline('ner', model='dbmdz/bert-large-cased-finetuned-conll03-english')
    entities = ner_pipeline(question, aggregation_strategy="simple")
    person_names = [entity['word'] for entity in entities]

    if not person_names:
        return "No person name found in the question."
    
    imdb_ids = []
    for name in person_names:
        imdb_id = get_imdb_id_from_wikidata(name)
        if imdb_id:
            imdb_ids.append(imdb_id)
    
    picture_link = get_random_image(imdb_ids)
    return picture_link

def get_imdb_id_from_wikidata(person_name):
    # SPARQL query to retrieve IMDb ID (P345) for the given person name
    query = f"""
    SELECT ?person ?imdb_id WHERE {{
      ?person rdfs:label "{person_name}"@en.
      ?person wdt:P345 ?imdb_id.
    }}
    LIMIT 1
    """
    
    url = "https://query.wikidata.org/sparql"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    params = {
        'format': 'json',
        'query': query
    }
    
    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    
    if data['results']['bindings']:
        imdb_id = data['results']['bindings'][0]['imdb_id']['value']
        return imdb_id
    return None

def get_random_image(imdb_ids):
    with open('./images.json', 'r') as file:
        images_data = json.load(file)

    # List to store possible image paths for matching IMDb IDs
    matching_images = []
    
    # Iterate over the data in images.json
    for entry in images_data:
        # Check if any of the imdb_ids are in the cast list
        if any(imdb_id in entry['cast'] for imdb_id in imdb_ids):
            # If a match is found, add the image path to the list
            matching_images.append(entry['img'])
    
    # Return a random image from the matching images
    if matching_images:
        return random.choice(matching_images)
    else:
        return "No matching images found."


