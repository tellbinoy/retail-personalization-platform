
from src.common_functions import log_lifecycle, open_parquet
from src.purchase_patterns import identify_customer_domains, generate_recommendation_candidates, rank_recommendations


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
    rank_recommendations(
        recommendation_candidates
    )

