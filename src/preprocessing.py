from src.common_functions import log_lifecycle, save_parquet
import pandas as pd

@log_lifecycle
def preprocess_fp_tree_transactions(df):
    df = df.copy()

    print(f"Initial records: {len(df):,}")

    # Remove returned items
    df = df[df["return_flag"] == False]

    # Remove invalid records
    df = df.dropna(subset=[
        "customer_id",
        "order_id",
        "sku_id"
    ])

    # Remove invalid quantities
    fp_tree_trx_df = df[df["quantity"] > 0]
    return fp_tree_trx_df

@log_lifecycle
def preprocess_customer_order_combo(fp_tree_trx_df):
    # Keep customer_order_id mapping
    customer_order_history_df = fp_tree_trx_df[
        [
            "customer_id",
            "order_id" #,
            #"sku_id"
        ]
    ]
    customer_order_history_df = customer_order_history_df.drop_duplicates(
        subset=["customer_id", "order_id"]
    )
    # Save artifacts
    save_parquet(customer_order_history_df, "customer_order_history")

    return customer_order_history_df

@log_lifecycle
def preprocess_sku_order_combo(fp_tree_trx_df):
    # Keep only columns required for FP-Growth
    sku_order_df = fp_tree_trx_df[
        [
            "order_id"  ,
            "sku_id"
        ]
    ]

    # Remove duplicate products within the same order
    sku_order_df = sku_order_df.drop_duplicates(
        subset=["order_id", "sku_id"]
    )
    save_parquet(sku_order_df, "sku_order")
    return sku_order_df


@log_lifecycle
def preprocess_fp_tree_basket_prep(sku_order_df):
    print(f"Input transactions : {len(sku_order_df):,}")

    transaction_baskets_df = (
        sku_order_df
        .groupby("order_id")["sku_id"]
        .agg(list)
        .reset_index(name="items")
    )

    print(f"Transaction baskets : {len(transaction_baskets_df):,}")
    save_parquet(transaction_baskets_df, "transaction_baskets")
    return transaction_baskets_df


