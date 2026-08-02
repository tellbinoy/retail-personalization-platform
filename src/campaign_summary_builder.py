

import json
from datetime import datetime

from src.common_functions import log_lifecycle, update_json_file
from src.data_loader import load_campaign_customers


@log_lifecycle
def build_campaign_summary(
    filtered_recommendations_df,
    file_name="campaign_summary.json",
    campaign_customer_df = load_campaign_customers()
):

    total_customers = campaign_customer_df["customer_id"].nunique()

    customers_with_recommendations = (
        filtered_recommendations_df["customer_id"]
        .nunique()
    )

    recommendations_generated = len(filtered_recommendations_df)

    campaign_summary = {

        "campaign": {

            "generated_timestamp": datetime.utcnow().isoformat(),

            "campaign_customers": total_customers,

            "customers_with_recommendations":
                customers_with_recommendations,

            "recommendation_coverage_pct":
                round(
                    100 *
                    customers_with_recommendations /
                    total_customers,
                    2
                ),

            "recommendations_generated":
                recommendations_generated,

            "average_recommendations_per_customer":
                round(
                    recommendations_generated /
                    customers_with_recommendations,
                    2
                )
        },

        "catalog": {

            "triggering_departments":
                int(
                    filtered_recommendations_df[
                        "triggering_department"
                    ].nunique()
                ),

            "recommended_departments":
                int(
                    filtered_recommendations_df[
                        "recommended_department"
                    ].nunique()
                ),

            "triggering_classes":
                int(
                    filtered_recommendations_df[
                        "triggering_class"
                    ].nunique()
                ),

            "recommended_classes":
                int(
                    filtered_recommendations_df[
                        "recommended_class"
                    ].nunique()
                )
        },

        "recommendation_quality": {

            "average_support":
                round(
                    filtered_recommendations_df[
                        "support"
                    ].mean(),
                    4
                ),

            "average_confidence":
                round(
                    filtered_recommendations_df[
                        "confidence"
                    ].mean(),
                    4
                ),

            "average_lift":
                round(
                    filtered_recommendations_df[
                        "lift"
                    ].mean(),
                    4
                )
        }
    }

    update_json_file(campaign_summary, file_name)

    return campaign_summary



@log_lifecycle
def build_department_summary(
    filtered_recommendations_df,
    file_name="department_summary.json"
):
    department_summary = []

    grouped = (
        filtered_recommendations_df
        .groupby("recommended_department")
    )

    for department, group in grouped:

        top_trigger = (
            group["triggering_department"]
            .value_counts()
            .idxmax()
        )

        department_summary.append({

            "department": department,

            "customers_recommended":
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
                top_trigger,

            "top_triggering_class":
                (
                    group[
                        "triggering_class"
                    ]
                    .value_counts()
                    .idxmax()
                ),

            "top_recommended_class":
                (
                    group[
                        "recommended_class"
                    ]
                    .value_counts()
                    .idxmax()
                )
        })

    department_summary = sorted(
        department_summary,
        key=lambda x:
            x["recommendations_generated"],
        reverse=True
    )

    dept_metadata = {

        "context": {

            "purpose":
                "Department level recommendation summary.",

            "audience":
                "Chief Marketing Officer",

            "objective":
                (
                    "Identify departments generating the "
                    "largest recommendation opportunities."
                )
        },

        "department_summary":
            department_summary
    }

    update_json_file(dept_metadata, file_name)

    return dept_metadata


@log_lifecycle
def build_cross_department_summary(
    filtered_recommendations_df,
    file_name="cross_department_summary.json"
):

    grouped = (
        filtered_recommendations_df
        .groupby(
            [
                "triggering_department",
                "recommended_department"
            ]
        )
    )

    cross_department_summary = []

    for (
        triggering_department,
        recommended_department
    ), group in grouped:

        cross_department_summary.append({

            "triggering_department":
                triggering_department,

            "recommended_department":
                recommended_department,

            "customers":
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

            "top_triggering_class":
                (
                    group["triggering_class"]
                    .value_counts()
                    .idxmax()
                ),

            "top_recommended_class":
                (
                    group["recommended_class"]
                    .value_counts()
                    .idxmax()
                )
        })

    cross_department_summary = sorted(
        cross_department_summary,
        key=lambda x: x["recommendations_generated"],
        reverse=True
    )

    metadata = {

        "context": {

            "purpose":
                "Cross-department recommendation summary.",

            "audience":
                "Chief Marketing Officer",

            "objective":
                (
                    "Identify department-to-department "
                    "cross-sell opportunities."
                )
        },

        "cross_department_summary":
            cross_department_summary
    }

    update_json_file(
        metadata,
        file_name
    )

    return metadata