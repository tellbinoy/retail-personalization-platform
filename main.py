import warnings

from pipelines.right_bundles._01_preprocessing_pipeline import run  as preprocessing

from src.common_functions import log_lifecycle, use_cloud_artifacts, print_runtime_context



@log_lifecycle
def main():
    #Uncomment this when moving to PROD
    print_runtime_context()
    use_cloud_artifacts()
    preprocessing()
    #fp_growth()
    #association_rules()
    #customer_domain_identification()
    #feature_importance()
    #bundle_ranking()
    #gemini_recommendation()
    #make_executive_report(context=build_gemini_context())

if __name__ == "__main__":
    warnings.filterwarnings("ignore")
    main()

    #Test Vertex Components separately
    #import vertex.test.test_executive_business_report_component
