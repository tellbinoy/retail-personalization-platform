import warnings

from pipelines.right_bundles._01_preprocessing_pipeline import run  as preprocessing
from pipelines.right_bundles._02_association_mining import run as associations
from pipelines.right_bundles._03_purchase_pattern_identification import run as purchase_pattern_identification
from pipelines.right_bundles._04_rank_bundle_recommendations import run as bundle_recommendations

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

    #Which bundle recommendations are top picks
    bundle_recommendations()

    #customer clustering into Personas by purchase patterns

    """
    I am planning to close my day for now, tomorrow, lets think of filtering the recommendations by rank. Lets write a code to wrap it up.
Also think of creating metadata and datasets for using Gemini to give recommendations. My end in mind is, these recommendations should help the CMO understand somethings like this
"In the purchase history of customers provided, Department Lumber also had $324,000 worth of products from Department Electrical. It has a high attach rate with Dept Electrical (12%) and Dept Tools (9%). Out of 15k customer provided in this campaign, 43% of them were recommended bundles containing products from Plumbing and Power Tools as they had a prior purchase of Lumber."
Lets do something like the above at Department Levels, for the top 5 Departments. Then we will also have to cluster customers by their purchase histories into professions. And tell something like the one below "Purchase patterns across 15k customers provided were analyzed into broader "profession buckets" 34% resonated with "Carpentry" (reason, 40% purchase concentrations were around Lumber, Tools), 18% resonated with "Plumbing" (reason 32% purchase concentrations were around faucets and bathroom tiling).
Think on these lines, what should we do to prepare datasets or metadata jsons which will eventually help Gemini narrate the broader "Campaign budget spend design" in simple terms to a CMO.
    
    Campaign Summary Dataset
Department Intelligence Dataset
Cross Department Dataset
Persona Dataset
Recommendation Evidence Dataset
Campaign Opportunity Dataset

    """



    #feature_importance()
    #bundle_ranking()
    #gemini_recommendation()
    #make_executive_report(context=build_gemini_context())

if __name__ == "__main__":
    warnings.filterwarnings("ignore")
    main()

    #Test Vertex Components separately
    #import vertex.test.test_executive_business_report_component
