from src.campaign_summary_builder import build_campaign_summary, build_department_summary, \
    build_cross_department_summary
from src.common_functions import log_lifecycle, open_json_file, open_parquet
from src.purchase_patterns import build_recommendation_evidence

#build_campaign_summary()
#build_department_intelligence()
#build_cross_department_summary()
#build_persona_summary()
#build_recommendation_evidence()
#build_campaign_opportunities()

"""
generate_cmo_campaign_brief(
    campaign_summary,
    department_summary,
    cross_department_summary,
    persona_summary,
    recommendation_evidence,
    campaign_opportunities
)"""


@log_lifecycle
def run():
    filtered_recommendations_df = open_parquet('customer_recommendations')
    build_campaign_summary(filtered_recommendations_df)
    build_department_summary(filtered_recommendations_df)
    build_cross_department_summary(filtered_recommendations_df)
    build_recommendation_evidence(filtered_recommendations_df)
