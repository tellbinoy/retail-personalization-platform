
from src.data_loader import load_campaign_customer_orders

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
    # artifacts/data/customer_order_history.parquet
    # artifacts/data/sku_order.parquet
    # artifacts/data/transaction_baskets.parquet

    df = load_campaign_customer_orders()
    print("Loaded campaign customer data")
    fp_tree_trx_df = preprocess_fp_tree_transactions(df)
    print("FP Tree TRX completed")
    customer_order_history_df = preprocess_customer_order_combo(fp_tree_trx_df)
    sku_order_df= preprocess_sku_order_combo(fp_tree_trx_df)
    print("SKU Order combo completed")
    transaction_baskets_df = preprocess_fp_tree_basket_prep(sku_order_df)
    print("Transaction basket completed")
    return customer_order_history_df, transaction_baskets_df



if __name__ == "__main__":
    run()