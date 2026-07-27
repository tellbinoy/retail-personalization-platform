from src.association_mining import run_fp_growth, generate_association_rules
from src.config import MIN_SUPPORT, MIN_THRESHOLD
from src.data_loader import load_campaign_customer_orders

from src.common_functions import save_parquet, open_parquet, open_json_file
from src.common_functions import log_lifecycle
from src.preprocessing import preprocess_fp_tree_transactions, preprocess_customer_order_combo, \
    preprocess_sku_order_combo, preprocess_fp_tree_basket_prep


#load_customer_orders()
#preprocess_fp_tree_transactions()
#create_transaction_baskets()
#one_hot_encode_transactions() #not required as the mlxtend.preprocessing already does that
#run_fp_growth()
#generate_association_rules()

@log_lifecycle
def run():
    # Vertex AI - Inputs
    # ----------------
    # `retailmarketing-123.analytics.campaign_customer`
    #
    # Vertex AI - Outputs
    # ----------------
    # artifacts/metadata/column_metadata.json

    df = load_campaign_customer_orders()
    print("Loaded campaign customer data")
    fp_tree_trx_df = preprocess_fp_tree_transactions(df)
    print("FP Tree TRX completed")
    customer_order_history_df = preprocess_customer_order_combo(fp_tree_trx_df)
    sku_order_df= preprocess_sku_order_combo(fp_tree_trx_df)
    print("SKU Order combo completed")
    transaction_baskets_df = preprocess_fp_tree_basket_prep(sku_order_df)
    print("Transaction basket completed")

    frequent_itemsets_df= run_fp_growth( transaction_baskets_df, min_support=MIN_SUPPORT, use_colnames=True )
    print("Frequent Itemsets completed")
    association_rules_df = generate_association_rules(frequent_itemsets_df, metric="confidence",  # lift #leverage #conviction
    min_threshold=MIN_THRESHOLD)
    print("Association Rules completed")

    association_rules_df.to_excel('association_rules.xlsx', index=False)



if __name__ == "__main__":
    run()