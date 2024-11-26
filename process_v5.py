import pandas as pd
from collections import Counter
import numpy as np

def handleCrowdSourcing(entity, relation):
    # Load data
    df = pd.read_csv("./crowd_data.tsv", sep="\t")
    entities_df = pd.read_csv("entities.csv")  # Assuming entities.csv is loaded here
    
    entity = entity.replace("http://www.wikidata.org/entity/", "wd:")
    relation = relation.replace("http://www.wikidata.org/prop/direct/", "wdt:")

    # Filter malicious workers
    filtered_data = filter_malicious_workers(df)

    # Filter tasks related to the entity and relation
    relevant_data = filtered_data[(filtered_data["Input1ID"] == entity) & 
                                  (filtered_data["Input2ID"] == relation)]
    if relevant_data.empty:
        return None
    
    # Extract the answer from Input3ID
    answer = relevant_data["Input3ID"].astype(str).unique()[0]
    
    # Check if answer starts with "wd:" and process accordingly
    if answer.startswith("wd:"):
        entity_id = answer.split(":")[1]  # Extract the part after "wd:"
        entity_info = entities_df[entities_df["Entity URI"].str.contains(entity_id, na=False)]
        
        if not entity_info.empty:
            # Replace with entity name from the entities.csv
            entity_name = entity_info["Entity Name"].values[0]
            answer = entity_name  # Replace the ID with the entity name
    
    # Aggregate answers
    answers = relevant_data["AnswerLabel"].tolist()
    majority_answer, answer_distribution = majority_voting(answers)

    # Compute inter-rater agreement
    kappa = compute_fleiss_kappa(answers)

    # Format the response
    response = (
        f"The answer is {answer}. "
        f"[Crowd, inter-rater agreement {kappa}, "
        f"The answer distribution for this specific task was {answer_distribution}]"
    )
    return response

def filter_malicious_workers(data):
    """Filter out malicious workers based on approval rate and work time."""
    approval_threshold = 50  # Minimum approval rate
    min_work_time = 10       # Minimum work time
    
    # Convert columns to numeric types
    data['LifetimeApprovalRate'] = data['LifetimeApprovalRate'].str.replace('%', '').astype(float)
    data["LifetimeApprovalRate"] = pd.to_numeric(data["LifetimeApprovalRate"], errors="coerce")
    data["WorkTimeInSeconds"] = pd.to_numeric(data["WorkTimeInSeconds"], errors="coerce")

    # Drop rows with invalid numeric values
    data = data.dropna(subset=["LifetimeApprovalRate", "WorkTimeInSeconds"])
    
    # Apply the filtering conditions
    return data[(data["LifetimeApprovalRate"] >= approval_threshold) & 
                (data["WorkTimeInSeconds"] > min_work_time)]

def majority_voting(answers):
    """Aggregate answers using majority voting."""
    # Count the number of CORRECT and INCORRECT votes
    support_votes = answers.count("CORRECT")
    reject_votes = answers.count("INCORRECT")

    # Determine the majority answer (CORRECT or INCORRECT)
    majority_answer = "CORRECT" if support_votes > reject_votes else "INCORRECT"
    
    # Prepare the answer distribution in the desired format
    answer_distribution = f"{support_votes} support votes, {reject_votes} reject votes"
    
    return majority_answer, answer_distribution

def compute_fleiss_kappa(votes):
    """Compute Fleiss' kappa for inter-rater agreement with binary integer values (1 for CORRECT, 0 for INCORRECT)."""
    # Map 'CORRECT' to 1 and 'INCORRECT' to 0 
    votes = [1 if vote == 'CORRECT' else 0 for vote in votes]
    category_counts = {0: votes.count(0), 1: votes.count(1)}
    
    n_raters = len(votes)   # Number of raters 
    n_items = 1 # The number of tasks 
    
    total_count = sum(votes) 
    p_o = total_count / n_raters  # Observed agreement (proportion of agreement)
    
    # Calculate the expected agreement (P_e)
    p_e = sum((count / n_raters) ** 2 for count in category_counts.values())
    
    # Compute Fleiss' Kappa
    kappa = (p_o - p_e) / (1 - p_e) if (1 - p_e) > 0 else 0
    return round(kappa, 3)
