
from src.common_functions import log_lifecycle, open_parquet
from src.purchase_patterns import identify_customer_domains, generate_recommendation_candidates


@log_lifecycle
def run( association_rules_df = None ):
    if len(association_rules_df) == 0:
        association_rules_df = open_parquet('association_rules')
    # Vertex AI - Inputs
    # ----------------
    # load_campaign_customer_orders()
    #
    # Vertex AI - Outputs
    # ----------------
    # artifacts/data/customer_domain.parquet
    identify_customer_domains()

    # Vertex AI - Inputs
    # ----------------
    # load_campaign_customer_orders()
    # artifacts/data/customer_domain.parquet
    # artifacts/data/association_rules.parquet
    #
    # Vertex AI - Outputs
    # ----------------
    # artifacts/data/recommendation_candidates.parquet
    customer_domain_df = open_parquet('customer_domain')
    recommendation_candidates_df = generate_recommendation_candidates(
        customer_domain_df,
        association_rules_df
    )

    return recommendation_candidates_df
    


if __name__ == "__main__":
    run()