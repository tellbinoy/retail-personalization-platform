from src.association_mining import run_fp_growth, generate_association_rules
from src.config import MIN_SUPPORT, MIN_THRESHOLD
from src.common_functions import log_lifecycle

@log_lifecycle
def run(transaction_baskets_df):
    # Vertex AI - Inputs
    # ----------------
    # artifacts/data/transaction_baskets.parquet
    #
    # Vertex AI - Outputs
    # ----------------
    # artifacts/data/association_rules.parquet

    frequent_itemsets_df= run_fp_growth( transaction_baskets_df, min_support=MIN_SUPPORT, use_colnames=True )
    print("Frequent Itemsets completed")
    association_rules_df = generate_association_rules(frequent_itemsets_df, metric="confidence",  # lift #leverage #conviction
        min_threshold=MIN_THRESHOLD)
    print("Association Rules completed")
    #association_rules_df.to_excel('association_rules.xlsx', index=False)
    return association_rules_df


if __name__ == "__main__":
    run()