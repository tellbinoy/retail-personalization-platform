from src.common_functions import open_parquet, log_lifecycle
from src.purchase_patterns import build_customer_persona_features, cluster_customer_personas, build_persona_summary


@log_lifecycle
def run():
    build_customer_persona_features()
    customer_features_df = open_parquet('customer_persona_features')
    cluster_customer_personas(customer_features_df)
    customer_personas_df = open_parquet('customer_personas')
    build_persona_summary( customer_features_df, customer_personas_df)