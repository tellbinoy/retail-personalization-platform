from src.common_functions import log_lifecycle, save_parquet
import pandas as pd

from src.config import PURCHASE_THRESHOLD
from src.data_loader import load_campaign_customer_orders


@log_lifecycle
def identify_customer_domains(
    domain_column="department",
    spend_column="sales_amount",
    threshold=0.80
):
    transaction_df = load_campaign_customer_orders()

    print(type(transaction_df))
    print(transaction_df.columns.tolist())
    print(transaction_df.columns[transaction_df.columns.duplicated()])
    print(transaction_df.head())

    # Spend per customer per domain
    customer_domain_df = (
        transaction_df
        .groupby(
            ["customer_id", domain_column],
            as_index=False
        )[spend_column]
        .sum()
        .rename(columns={

            domain_column: "domain",
            spend_column: "domain_spend"

        })
    )

    # Total customer spend
    customer_domain_df["total_spend"] = (
        customer_domain_df
        .groupby("customer_id")["domain_spend"]
        .transform("sum")
    )

    # Spend percentage
    customer_domain_df["spend_pct"] = (
        customer_domain_df["domain_spend"]
        / customer_domain_df["total_spend"]
    )

    # Sort by contribution
    customer_domain_df = (
        customer_domain_df
        .sort_values(
            ["customer_id", "domain_spend"],
            ascending=[True, False]
        )
        .reset_index(drop=True)
    )

    # Running cumulative percentage
    customer_domain_df["cumulative_spend_pct"] = (
        customer_domain_df
        .groupby("customer_id")["spend_pct"]
        .cumsum()
    )

    # Domain Rank
    customer_domain_df["domain_rank"] = (
        customer_domain_df
        .groupby("customer_id")
        .cumcount()
        + 1
    )

    # Select domains contributing up to threshold
    # Always include first domain.
    customer_domain_df["selected"] = (
        customer_domain_df["cumulative_spend_pct"] <= threshold
    )
    first_domain = customer_domain_df["domain_rank"] == 1
    customer_domain_df.loc[first_domain, "selected"] = True

    # Include the first domain crossing the threshold
    crossing = (
        customer_domain_df
        .loc[
            customer_domain_df["cumulative_spend_pct"] >= threshold
        ]
        .groupby("customer_id")
        .head(1)
        .index
    )

    customer_domain_df.loc[crossing, "selected"] = True
    print(f"Customer-Domain records : {len(customer_domain_df):,}")
    customer_domain_df = customer_domain_df.reset_index(drop=True)
    #customer_domain_df.to_excel('customer_domain_df.xlsx', index=False)
    save_parquet(customer_domain_df, "customer_domain")
    return customer_domain_df

#identify_customer_domains()