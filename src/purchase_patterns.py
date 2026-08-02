from src.common_functions import log_lifecycle, save_parquet, save_joblib, update_json_file
import pandas as pd

from src.config import PURCHASE_THRESHOLD, RECOMMENDATION_BUNDLE_CUTOFF, USE_BIGQUERY, CUSTOMER_PERSONA_BUCKETS
from src.data_loader import load_campaign_customer_orders, write_to_bigquery

from sklearn.preprocessing import RobustScaler

from sklearn.cluster import KMeans
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


@log_lifecycle
def generate_recommendation_candidates(
    customer_domain_df,
    association_rules_df
):

    transaction_df = load_campaign_customer_orders()

    print(f"Transactions              : {len(transaction_df):,}")
    print(f"Customer Domains          : {len(customer_domain_df):,}")
    print(f"Association Rules         : {len(association_rules_df):,}")

    # --------------------------------------------------
    # Keep only selected customer domains
    # --------------------------------------------------

    customer_domains = (
        customer_domain_df
        .loc[customer_domain_df["selected"]]
        [["customer_id", "domain"]]
        .drop_duplicates()
    )

    # --------------------------------------------------
    # Customer purchases within selected domains
    # --------------------------------------------------

    customer_purchases = (
        transaction_df
        .merge(
            customer_domains,
            left_on=["customer_id", "department"],
            right_on=["customer_id", "domain"],
            how="inner"
        )
        [
            [
                "customer_id",
                "sku_id",
                "department",
                "class"
            ]
        ]
        .drop_duplicates()
        .rename(columns={
            "sku_id": "triggering_sku",
            "department": "triggering_department",
            "class": "triggering_class"
        })
    )

    # --------------------------------------------------
    # Expand association rules
    # --------------------------------------------------

    association_rules = association_rules_df.copy()

    association_rules["antecedents"] = (
        association_rules["antecedents"].apply(list)
    )

    association_rules["consequents"] = (
        association_rules["consequents"].apply(list)
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

    # --------------------------------------------------
    # Customer purchases × Association Rules
    # --------------------------------------------------

    recommendation_candidates_df = (
        customer_purchases
        .merge(
            association_rules[
                [
                    "triggering_sku",
                    "recommended_sku",
                    "support",
                    "confidence",
                    "lift"
                ]
            ],
            on="triggering_sku",
            how="inner"
        )
    )

    # --------------------------------------------------
    # Recommended SKU lookup
    # --------------------------------------------------

    sku_lookup = (
        transaction_df[
            [
                "sku_id",
                "department",
                "class"
            ]
        ]
        .drop_duplicates()
        .rename(columns={
            "sku_id": "recommended_sku",
            "department": "recommended_department",
            "class": "recommended_class"
        })
    )

    recommendation_candidates_df = (
        recommendation_candidates_df
        .merge(
            sku_lookup,
            on="recommended_sku",
            how="left"
        )
    )

    # --------------------------------------------------
    # Remove already purchased recommendations
    # --------------------------------------------------

    purchased = (
        transaction_df[
            [
                "customer_id",
                "sku_id"
            ]
        ]
        .drop_duplicates()
        .rename(columns={
            "sku_id": "recommended_sku"
        })
        .assign(already_purchased=True)
    )

    recommendation_candidates_df = (
        recommendation_candidates_df
        .merge(
            purchased,
            on=[
                "customer_id",
                "recommended_sku"
            ],
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

    # --------------------------------------------------
    # Final formatting
    # --------------------------------------------------

    recommendation_candidates_df = (
        recommendation_candidates_df[
            [
                "customer_id",
                "triggering_department",
                "triggering_class",
                "triggering_sku",
                "recommended_department",
                "recommended_class",
                "recommended_sku",
                "support",
                "confidence",
                "lift"
            ]
        ]
        .drop_duplicates()
        .sort_values(
            by=[
                "customer_id",
                "lift",
                "confidence"
            ],
            ascending=[
                True,
                False,
                False
            ]
        )
        .reset_index(drop=True)
    )

    print(
        f"Recommendation Candidates : {len(recommendation_candidates_df):,}"
    )

    recommendation_candidates_df.to_excel(
        "recommendation_candidates.xlsx",
        index=False
    )

    save_parquet(
        recommendation_candidates_df,
        "recommendation_candidates"
    )

    return recommendation_candidates_df



@log_lifecycle
def rank_recommendations(
    recommendation_candidates_df
):

    #Rank recommendation candidates using association rule strength.

    required_columns =  [
        "customer_id",
        "triggering_department",
        "triggering_class",
        "triggering_sku",
        "recommended_department",
        "recommended_class",
        "recommended_sku",
        "support",
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
    ranked_recommendations_df.to_excel('ranked_recommendation.xlsx', index=False)

    return ranked_recommendations_df

@log_lifecycle
def filter_recommendations(
    ranked_recommendations_df,
    top_n=RECOMMENDATION_BUNDLE_CUTOFF
):

    required_columns = [
        "customer_id",
        "triggering_department",
        "triggering_class",
        "triggering_sku",
        "recommended_department",
        "recommended_class",
        "recommended_sku",
        "support",
        "confidence",
        "lift",
        "recommendation_score",
        "recommendation_rank"
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in ranked_recommendations_df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    filtered_recommendations_df = (
        ranked_recommendations_df.copy()
    )

    # Keep Top N recommendations per customer
    filtered_recommendations_df = (
        filtered_recommendations_df[
            filtered_recommendations_df[
                "recommendation_rank"
            ] <= top_n
        ]
    )

    # Remove duplicate recommendations
    # Keep the highest ranked recommendation

    filtered_recommendations_df = (
        filtered_recommendations_df
        .sort_values(
            [
                "customer_id",
                "recommendation_rank"
            ]
        )
        .drop_duplicates(
            subset=[
                "customer_id",
                "recommended_sku"
            ],
            keep="first"
        )
    )


    # Final Sort
    filtered_recommendations_df = (
        filtered_recommendations_df
        .sort_values(
            [
                "customer_id",
                "recommendation_rank"
            ]
        )
        .reset_index(drop=True)
    )

    print(
        f"Filtered Recommendations : "
        f"{len(filtered_recommendations_df):,}"
    )

    filtered_recommendations_df.to_excel('filtered_recommendations.xlsx', index=False)
    save_parquet(
        filtered_recommendations_df,
        "filtered_recommendations"
    )

    return filtered_recommendations_df


@log_lifecycle
def publish_recommendations(
    filtered_recommendations_df
):


    required_columns = [
        "customer_id",
        "triggering_department",
        "triggering_class",
        "triggering_sku",
        "recommended_department",
        "recommended_class",
        "recommended_sku",
        "support",
        "confidence",
        "lift",
        "recommendation_score",
        "recommendation_rank"
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in filtered_recommendations_df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    recommendation_df = (
        filtered_recommendations_df[
            required_columns
        ]
        .copy()
        .sort_values(
            [
                "customer_id",
                "recommendation_rank"
            ]
        )
        .reset_index(drop=True)
    )

    print(
        f"Published Recommendations : "
        f"{len(recommendation_df):,}"
    )

    save_parquet(
        recommendation_df,
        "customer_recommendations"
    )

    if USE_BIGQUERY:

        write_to_bigquery(
            recommendation_df,
            table_name="customer_recommendations",
            write_disposition="WRITE_TRUNCATE"
        )

    return recommendation_df


@log_lifecycle
def build_customer_persona_features():
    #Build customer feature matrix for persona clustering.


    transaction_df = load_campaign_customer_orders()


    # Department Spend
    customer_department = (
        transaction_df
        .groupby(
            [
                "customer_id",
                "department"
            ],
            as_index=False
        )["sales_amount"]
        .sum()
    )

    # Customer x Department Matrix

    customer_features_df = (
        customer_department
        .pivot(
            index="customer_id",
            columns="department",
            values="sales_amount"
        )
        .fillna(0)
    )

    # Convert to Spend %

    customer_features_df = (
        customer_features_df
        .div(
            customer_features_df.sum(axis=1),
            axis=0
        )
        .fillna(0)
    )

    customer_features_df = (
        customer_features_df
        .reset_index()
    )

    print(
        f"Customer Persona Features : "
        f"{len(customer_features_df):,}"
    )

    save_parquet(
        customer_features_df,
        "customer_persona_features"
    )

    return customer_features_df



@log_lifecycle
def cluster_customer_personas(
    customer_features_df,
    n_clusters=CUSTOMER_PERSONA_BUCKETS
):

    customer_persona_df = customer_features_df.copy()

    # Preserve Customer IDs
    customer_ids = customer_persona_df["customer_id"]
    features = customer_persona_df.drop(
        columns="customer_id"
    )

    # Scale Features
    scaler = RobustScaler()
    scaled_features = scaler.fit_transform(
        features
    )

    # KMeans Clustering
    model = KMeans(
        n_clusters=n_clusters,
        random_state=42,
        n_init=20
    )

    clusters = model.fit_predict(
        scaled_features
    )

    # Final Dataset
    customer_persona_df = customer_ids.to_frame()
    customer_persona_df["persona_cluster"] = (
        clusters
    )

    print(
        customer_persona_df["persona_cluster"]
        .value_counts()
        .sort_index()
    )

    save_parquet(
        customer_persona_df,
        "customer_personas"
    )

    save_joblib(model, 'customer_persona_kmean')

    return (
        customer_persona_df,
        model
    )



@log_lifecycle
def build_persona_summary(
    customer_features_df,
    customer_personas_df,
    top_departments=3,
    file_name="persona_summary.json"
):
    """
    Build customer persona metadata from KMeans clusters.
    """

    persona_df = (
        customer_features_df
        .merge(
            customer_personas_df,
            on="customer_id",
            how="inner"
        )
    )

    department_columns = [
        column
        for column in persona_df.columns
        if column not in [
            "customer_id",
            "persona_cluster"
        ]
    ]

    persona_summary = []

    grouped = persona_df.groupby("persona_cluster")

    for cluster_id, group in grouped:

        department_profile = (
            group[department_columns]
            .mean()
            .sort_values(ascending=False)
        )

        dominant_departments = []

        for department, value in (
            department_profile
            .head(top_departments)
            .items()
        ):
            dominant_departments.append({

                "department": department,

                "average_spend_share_pct":
                    round(
                        value * 100,
                        2
                    )
            })

        persona_summary.append({

            "persona_cluster":
                int(cluster_id),

            "customers":
                int(
                    group["customer_id"].nunique()
                ),

            "dominant_departments":
                dominant_departments
        })

    persona_summary = sorted(
        persona_summary,
        key=lambda x: x["customers"],
        reverse=True
    )

    metadata = {

        "context": {

            "purpose":
                "Customer purchasing personas.",

            "audience":
                "Chief Marketing Officer",

            "objective":
                (
                    "Summarize customer purchasing "
                    "behaviours into interpretable personas."
                )
        },

        "persona_summary":
            persona_summary
    }

    update_json_file(
        metadata,
        file_name
    )

    return metadata


@log_lifecycle
def build_recommendation_evidence(
    filtered_recommendations_df,
    file_name="recommendation_evidence.json"
):

    #Summarises why recommendation classes were suggested by aggregating customer impact and recommendation quality.

    grouped = (
        filtered_recommendations_df
        .groupby(
            [
                "recommended_department",
                "recommended_class"
            ]
        )
    )

    recommendation_evidence = []

    for (
        recommended_department,
        recommended_class
    ), group in grouped:

        recommendation_evidence.append({

            "recommended_department":
                recommended_department,

            "recommended_class":
                recommended_class,

            "customers_impacted":
                int(
                    group["customer_id"].nunique()
                ),

            "recommendations_generated":
                int(
                    len(group)
                ),

            "average_confidence":
                round(
                    group["confidence"].mean(),
                    4
                ),

            "average_lift":
                round(
                    group["lift"].mean(),
                    4
                ),

            "top_triggering_department":
                (
                    group["triggering_department"]
                    .mode()
                    .iloc[0]
                ),

            "top_triggering_class":
                (
                    group["triggering_class"]
                    .mode()
                    .iloc[0]
                )
        })

    recommendation_evidence = sorted(
        recommendation_evidence,
        key=lambda x: (
            x["customers_impacted"],
            x["average_lift"]
        ),
        reverse=True
    )

    metadata = {

        "context": {

            "purpose":
                "Evidence supporting recommendation decisions.",

            "audience":
                "Chief Marketing Officer",

            "objective":
                (
                    "Summarize the strongest purchasing "
                    "relationships that resulted in "
                    "recommended product classes."
                )
        },

        "recommendation_evidence":
            recommendation_evidence
    }

    update_json_file(
        metadata,
        file_name
    )

    return metadata