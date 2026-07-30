from src.common_functions import log_lifecycle, save_parquet
import pandas as pd

from src.config import PURCHASE_THRESHOLD
from src.data_loader import load_campaign_customer_orders

from sklearn.preprocessing import RobustScaler

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


@log_lifecycle
def generate_recommendation_candidates(
    customer_domain_df,
    association_rules_df
):
    """
    Generate customer-specific recommendation candidates using
    customer purchase history and association rules.

    Parameters
    ----------
    transaction_df : pd.DataFrame

    customer_domain_df : pd.DataFrame
        Output of identify_customer_domains()

    association_rules_df : pd.DataFrame
        Output of generate_association_rules()

    Returns
    -------
    recommendation_candidates_df

        customer_id
        triggering_sku
        recommended_sku
        recommendation_domain
        confidence
        lift
    """
    transaction_df = load_campaign_customer_orders()

    print(f"Transactions            : {len(transaction_df):,}")
    print(f"Customer Domains        : {len(customer_domain_df):,}")
    print(f"Association Rules       : {len(association_rules_df):,}")

    # Keep only selected customer domains
    customer_domains = (
        customer_domain_df
        .loc[customer_domain_df["selected"]]
        [["customer_id", "domain"]]
        .drop_duplicates()
    )


    # Customer purchases within selected domains
    customer_purchases = (
        transaction_df
        .merge(
            customer_domains,
            left_on=["customer_id", "department"],
            right_on=["customer_id", "domain"],
            how="inner"
        )
        [["customer_id", "sku_id", "department"]]
        .drop_duplicates()
        .rename(columns={
            "sku_id": "triggering_sku"
        })
    )

    # Convert sets into one row per SKU
    association_rules = (
        association_rules_df.copy()
    )

    association_rules["antecedents"] = (
        association_rules["antecedents"]
        .apply(list)
    )

    association_rules["consequents"] = (
        association_rules["consequents"]
        .apply(list)
    )

    association_rules = (
        association_rules
        .explode("antecedents")
        .explode("consequents")
        .rename(columns={
            "antecedents": "triggering_sku",
            "consequents": "recommended_sku"
        })
    )


    # Join purchases with association rules
    recommendation_candidates_df = (
        customer_purchases
        .merge(
            association_rules[
                [
                    "triggering_sku",
                    "recommended_sku",
                    "confidence",
                    "lift"
                ]
            ],
            on="triggering_sku",
            how="inner"
        )
    )

    # Recommendation Domain
    sku_domain_lookup = (
        transaction_df[
            ["sku_id", "department"]
        ]
        .drop_duplicates()
        .rename(columns={
            "sku_id": "recommended_sku",
            "department": "recommendation_domain"
        })
    )

    recommendation_candidates_df = (
        recommendation_candidates_df
        .merge(
            sku_domain_lookup,
            on="recommended_sku",
            how="left"
        )
    )


    # Remove recommendations already purchased
    purchased = (
        transaction_df[
            ["customer_id", "sku_id"]
        ]
        .drop_duplicates()
        .rename(columns={
            "sku_id": "recommended_sku"
        })
    )

    recommendation_candidates_df = (
        recommendation_candidates_df
        .merge(
            purchased.assign(already_purchased=True),
            on=["customer_id", "recommended_sku"],
            how="left"
        )
    )

    recommendation_candidates_df = (
        recommendation_candidates_df
        .loc[
            recommendation_candidates_df["already_purchased"].isna()
        ]
        .drop(columns="already_purchased")
    )

    recommendation_candidates_df = (
        recommendation_candidates_df[
            [
                "customer_id",
                "triggering_sku",
                "recommended_sku",
                "recommendation_domain",
                "confidence",
                "lift"
            ]
        ]
        .drop_duplicates()
        .sort_values(
            ["customer_id", "lift", "confidence"],
            ascending=[True, False, False]
        )
        .reset_index(drop=True)
    )

    print(
        f"Recommendation Candidates : {len(recommendation_candidates_df):,}"
    )
    recommendation_candidates_df.to_excel('recommendation_candidates_df.xlsx', index=False)
    save_parquet(recommendation_candidates_df, "recommendation_candidates")

    return recommendation_candidates_df


@log_lifecycle
def rank_recommendations(
    recommendation_candidates_df
):

    #Rank recommendation candidates using association rule strength.

    required_columns = [
        "customer_id",
        "triggering_sku",
        "recommended_sku",
        "recommendation_domain",
        "confidence",
        "lift"
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in recommendation_candidates_df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    ranked_recommendations_df = (
        recommendation_candidates_df.copy()
    )

    # Robust Scaling
    # scaled value = (X - median) / IQR
    # scaled values can be negative
    scaler = RobustScaler()

    ranked_recommendations_df[ ["scaled_confidence", "scaled_lift"] ] = scaler.fit_transform(
        ranked_recommendations_df[
            [
                "confidence",
                "lift"
            ]
        ]
    )

    # Recommendation Score
    #Actual logic involves margin calculation, recency, seasonality and prior ad response rates

    ranked_recommendations_df[
        "recommendation_score"
    ] = (
        ranked_recommendations_df["scaled_confidence"]
        +
        ranked_recommendations_df["scaled_lift"]
    ) / 2


    # Rank recommendations within each customer

    ranked_recommendations_df[
        "recommendation_rank"
    ] = (
        ranked_recommendations_df
        .groupby("customer_id")["recommendation_score"]
        .rank(
            method="dense",
            ascending=False
        )
        .astype(int)
    )

    # Sort Output

    # Window function of bundle ranking for each customer
    ranked_recommendations_df = (
        ranked_recommendations_df
        .sort_values(
            [
                "customer_id",
                "recommendation_rank",
                "recommendation_score"
            ],
            ascending=[True, True, False]
        )
        .reset_index(drop=True)
    )

    print(
        f"Ranked recommendations : "
        f"{len(ranked_recommendations_df):,}"
    )

    save_parquet(
        ranked_recommendations_df,
        "ranked_recommendations"
    )
    ranked_recommendations_df.to_excel('recommendation_candidates_df.xlsx', index=False)

    return ranked_recommendations_df