from mlxtend.preprocessing import TransactionEncoder
from mlxtend.frequent_patterns import fpgrowth

from src.common_functions import log_lifecycle
from src.config import MIN_SUPPORT, MIN_THRESHOLD

import pandas as pd

@log_lifecycle
def run_fp_growth(
    transaction_baskets_df,
    min_support=MIN_SUPPORT,
    use_colnames=True
):
    #min_support: minimum support threshold.
    #use_colnames: Return item names instead of column indices.

    print(f"Transaction baskets : {len(transaction_baskets_df):,}")

    # Extract list of baskets
    transactions = transaction_baskets_df["items"].tolist()

    # One-hot encode using TransactionEncoder
    te = TransactionEncoder()

    encoded_transactions = te.fit(transactions).transform(transactions)

    encoded_df = pd.DataFrame(
        encoded_transactions,
        columns=te.columns_
    )

    print(f"Unique SKUs : {encoded_df.shape[1]:,}")

    # Run FP-Growth
    frequent_itemsets_df = fpgrowth(
        encoded_df,
        min_support=min_support,
        use_colnames=use_colnames
    )

    # Sort by support
    frequent_itemsets_df = (
        frequent_itemsets_df
        .sort_values("support", ascending=False)
        .reset_index(drop=True)
    )

    print(f"Frequent itemsets discovered : {len(frequent_itemsets_df):,}")

    return frequent_itemsets_df

from mlxtend.frequent_patterns import association_rules

@log_lifecycle
def generate_association_rules(
    frequent_itemsets_df,
    metric="confidence", #lift #leverage #conviction
    min_threshold=MIN_THRESHOLD
):

    print(f"Frequent itemsets : {len(frequent_itemsets_df):,}")

    association_rules_df = association_rules(
        frequent_itemsets_df,
        metric=metric,
        min_threshold=min_threshold
    )

    if association_rules_df.empty:
        print("No association rules found.")
        return association_rules_df

    # Convert frozensets into sorted lists for readability
    association_rules_df["antecedents"] = (
        association_rules_df["antecedents"]
        .apply(lambda x: sorted(list(x)))
    )

    association_rules_df["consequents"] = (
        association_rules_df["consequents"]
        .apply(lambda x: sorted(list(x)))
    )

    # Sort strongest rules first
    association_rules_df = (
        association_rules_df
        .sort_values(
            by=["lift", "confidence"],
            ascending=False
        )
        .reset_index(drop=True)
    )

    print(f"Association rules generated : {len(association_rules_df):,}")

    return association_rules_df