import warnings

from pipelines.right_bundles._01_preprocessing_pipeline import run  as preprocessing
from pipelines.right_bundles._02_association_mining import run as associations
from pipelines.right_bundles._03_purchase_pattern_identification import run as purchase_pattern_identification

from src.common_functions import log_lifecycle, use_cloud_artifacts, print_runtime_context



@log_lifecycle
def main():
    #Uncomment this when moving to PROD
    print_runtime_context()
    use_cloud_artifacts()

    #What products are bought together in the population
    customer_order_history_df, transaction_baskets_df = preprocessing()
    associations(transaction_baskets_df)

    #What products are interesting to the customer
    purchase_pattern_identification()

    #Customer intelligence + domain intelligence
    generate_recommendation_candidates(
        transaction_df,
        customer_domain_df,
        association_rules_df
    )

    #feature_importance()
    #bundle_ranking()
    #gemini_recommendation()
    #make_executive_report(context=build_gemini_context())

if __name__ == "__main__":
    warnings.filterwarnings("ignore")
    main()

    #Test Vertex Components separately
    #import vertex.test.test_executive_business_report_component
