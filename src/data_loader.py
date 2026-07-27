from google.cloud import bigquery

from src.common_functions import log_lifecycle
from src.config import USE_BIGQUERY
from src.config import PROJECT_ID

import pandas as pd
# Set to None to show all columns
pd.set_option('display.max_columns', None)

@log_lifecycle
def get_bq_client():
    try:
        client = bigquery.Client(project=PROJECT_ID) #Use Application Default Credential
        return client

    except Exception as e:
        raise Exception(
            "BigQuery authentication failed. \n"
            "Go to terminal and then run the below line\n\n"
            "gcloud auth application-default login\n\n"
        ) from e

@log_lifecycle
def load_campaign_customers():
    if USE_BIGQUERY:
        query = f"""
            SELECT distinct customer_id
            FROM `retailmarketing-123.analytics.campaign_customer`
            """

        df = (
            get_bq_client()
            .query(query)
            .to_dataframe()
        )
        return df.drop_duplicates()

    else:
        print("NO DATA FOUND")




@log_lifecycle
def load_customer_profile():
    if USE_BIGQUERY:
        query = f"""
            SELECT *
            FROM `retailmarketing-123.analytics.customer_profile`
            """

        df = (
            get_bq_client()
            .query(query)
            .to_dataframe()
        )

    else:

        df = pd.read_csv(
            "data/analytics/customer_profile.csv"
        )

    return df.drop_duplicates()
@log_lifecycle
def load_campaign_customer_orders():
    if USE_BIGQUERY:
        query = """
            SELECT orders.*
            FROM `retailmarketing-123.analytics.orders` orders
            INNER JOIN `retailmarketing-123.analytics.campaign_customer` customer
                ON orders.customer_id = customer.customer_id
        """

        df = (
            get_bq_client()
            .query(query)
            .to_dataframe()
        )

    else:
        print("Data NOT FOUND")
        return None

    return df.drop_duplicates()

