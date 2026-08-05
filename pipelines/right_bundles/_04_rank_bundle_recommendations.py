
from src.common_functions import log_lifecycle, open_parquet
from src.purchase_patterns import identify_customer_domains, generate_recommendation_candidates, rank_recommendations, \
    filter_recommendations, publish_recommendations


@log_lifecycle
def run(recommendation_candidates=None, ranked_recommendations=None, filtered_recommendations=0):

    # Vertex AI - Inputs
    # ----------------
    # artifacts/data/recommendation_candidates.parquet
    #
    # Vertex AI - Outputs
    # ----------------
    # artifacts/data/ranked_recommendations
    if len(recommendation_candidates) == 0:
        recommendation_candidates = open_parquet('recommendation_candidates')

    rank_recommendations(recommendation_candidates)

    if len(ranked_recommendations) == 0:
        ranked_recommendations = open_parquet('ranked_recommendations')

    filter_recommendations(ranked_recommendations)

    if len(filtered_recommendations) == 0:
        filtered_recommendations = open_parquet('filtered_recommendations')

    recommendation_df = publish_recommendations(filtered_recommendations)
    return recommendation_df

