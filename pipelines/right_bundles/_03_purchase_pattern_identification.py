
from src.common_functions import log_lifecycle
from src.purchase_patterns import identify_customer_domains


@log_lifecycle
def run():
    # Vertex AI - Inputs
    # ----------------
    # artifacts/data/transaction_baskets.parquet
    #
    # Vertex AI - Outputs
    # ----------------
    # artifacts/data/customer_domain.parquet
    identify_customer_domains()



if __name__ == "__main__":
    run()