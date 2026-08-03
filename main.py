import warnings

from pipelines.right_bundles._01_preprocessing_pipeline import run  as preprocessing
from pipelines.right_bundles._02_association_mining import run as associations
from pipelines.right_bundles._03a_purchase_pattern_identification import run as purchase_pattern_identification
from pipelines.right_bundles._03b_customer_persona import run as customer_persona_grouping
from pipelines.right_bundles._04_rank_bundle_recommendations import run as bundle_recommendations
from pipelines.right_bundles._05_campaign_summary_maker import run as campaign_summary
from pipelines.right_bundles._06_gemini_writeup import run as gemini_insights

from src.common_functions import log_lifecycle, use_cloud_artifacts, print_runtime_context



@log_lifecycle
def main():
    #Uncomment this when moving to PROD
    print_runtime_context()
    use_cloud_artifacts()

    #What products are bought together in the population
    #customer_order_history_df, transaction_baskets_df = preprocessing()
    #associations(transaction_baskets_df)

    #What products are interesting to the customer
    #purchase_pattern_identification()

    #Discover hidden customer personas
    #customer_persona_grouping()

    #Which bundle recommendations are top picks
    #bundle_recommendations()

    #customer clustering into Personas by purchase patterns
    #campaign_summary()

    #Gemini Write up
    gemini_insights()


if __name__ == "__main__":
    warnings.filterwarnings("ignore")
    main()

    #Test Vertex Components separately
    #import vertex.test.test_executive_business_report_component
