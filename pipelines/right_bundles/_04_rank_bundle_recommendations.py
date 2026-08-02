
from src.common_functions import log_lifecycle, open_parquet
from src.purchase_patterns import identify_customer_domains, generate_recommendation_candidates, rank_recommendations, \
    filter_recommendations, publish_recommendations


@log_lifecycle
def run():

    # Vertex AI - Inputs
    # ----------------
    # artifacts/data/recommendation_candidates.parquet
    #
    # Vertex AI - Outputs
    # ----------------
    # artifacts/data/ranked_recommendations

    recommendation_candidates = open_parquet('recommendation_candidates')
    rank_recommendations(recommendation_candidates)
    ranked_recommendations = open_parquet('ranked_recommendations')
    filter_recommendations(ranked_recommendations)
    filtered_recommendations = open_parquet('filtered_recommendations')
    publish_recommendations(filtered_recommendations)


