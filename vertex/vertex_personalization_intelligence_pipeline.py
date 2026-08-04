from kfp import dsl
from kfp import compiler
from kfp.dsl import Input, Output, Dataset, Model
from pathlib import Path



compiled_dir = Path(__file__).parent / "compiled" #This finds the compiled folder relative to the current file's path
compiled_dir.mkdir(parents=True, exist_ok=True) #If the directory is not present, then it makes it

#IMPORTANT: Ensure every component imports the package it needs inside the component to not fail during runtime

#@dsl.component tells this function is a stand alone component
# Used a light weight component, easier to read and develop initially, generates wrapper code
# Move to container_component in production
@dsl.component(base_image="asia-south1-docker.pkg.dev/retailmarketing-123/ml-repo/retail-personalization-platform:latest")
def preprocessing_component(preprocessed_data_folder: Output[Dataset]):
    # Import the function inside the component definition to get this defined and compiled prior execution from the docker image
    from pipelines.right_bundles._01_preprocessing_pipeline import run as preprocessing
    from src.common_functions import open_parquet
    from src.config import ARTIFACT_ROOT

    from pathlib import Path

    customer_order_history, transaction_baskets = preprocessing()

    #customer_order_history = open_parquet('customer_order_history')
    #transaction_baskets = open_parquet('transaction_baskets')

    # create the folder in the dedicated Vertex Bucket space (idempotent)
    Path(preprocessed_data_folder.path).mkdir(
        parents=True,
        exist_ok=True
    )

    # save these to output folders
    customer_order_history.to_parquet(
        preprocessed_data_folder.path + "/customer_order_history.parquet"
    )

    transaction_baskets.to_parquet(
        preprocessed_data_folder.path + "/transaction_baskets.parquet"
    )





# Used a light weight component, easier to read and develop initially, generates wrapper code
# Move to container_component in production
@dsl.component(base_image="asia-south1-docker.pkg.dev/retailmarketing-123/ml-repo/retail-personalization-platform:latest")
def association_mining_component(input_data_folder:Input[Dataset], association_mining_folder: Output[Dataset]):
    # Import the function inside the component definition to get this defined and compiled prior execution from the docker image
    from pipelines.right_bundles._02_association_mining import run as association_mining
    import pandas as pd
    from pathlib import Path
    transaction_baskets = pd.read_parquet(
        input_data_folder.path + "/transaction_baskets.parquet"
    )
    association_rules_df = association_mining(transaction_baskets)
    # create the folder in the dedicated Vertex Bucket space (idempotent)
    Path(association_mining_folder.path).mkdir(
        parents=True,
        exist_ok=True
    )

    # save these to output folders
    association_rules_df.to_parquet(
        association_mining_folder.path + "/association_rules.parquet"
    )


# Used a light weight component, easier to read and develop initially, generates wrapper code
# Move to container_component in production
@dsl.component(base_image="asia-south1-docker.pkg.dev/retailmarketing-123/ml-repo/retail-personalization-platform:latest")
def purchase_pattern_identification_component(input_data_folder:Input[Dataset], purchase_pattern_folder: Output[Dataset]):
    # Import the function inside the component definition to get this defined and compiled prior execution from the docker image
    from pipelines.right_bundles._03a_purchase_pattern_identification import run as purchase_pattern_identification
    import pandas as pd
    from pathlib import Path
    association_rules = pd.read_parquet(
        input_data_folder.path + "/association_rules.parquet"
    )
    recommendation_candidates_df = purchase_pattern_identification(association_rules)
    # create the folder in the dedicated Vertex Bucket space (idempotent)
    Path(purchase_pattern_folder.path).mkdir(
        parents=True,
        exist_ok=True
    )

    # save these to output folders
    recommendation_candidates_df.to_parquet(
        purchase_pattern_folder.path + "/recommendation_candidates.parquet"
    )


@dsl.component(base_image="asia-south1-docker.pkg.dev/retailmarketing-123/ml-repo/retail-personalization-platform:latest")
def customer_persona_component():
    from pipelines.right_bundles._03b_customer_persona import run as customer_persona_identification
    import pandas as pd
    from pathlib import Path

    customer_persona_identification()


#@dsl.pipeline tells this function name is the master plan for the whole workflow
@dsl.pipeline(
    name="retail-personalization-intelligence-pipeline"
)
#this is the master plan function's definition
def personalization_intelligence_pipeline():

    preprocessing_task = preprocessing_component()
    preprocessing_task.set_caching_options(True) #Disable cache to flush out old results on VertexAI

    # Run only after preprocessing completes
    association_mining_task = association_mining_component(input_data_folder=preprocessing_task.outputs["preprocessed_data_folder"])
    association_mining_task.set_caching_options(True) #Disable cache to flush out old results on VertexAI

    purchase_pattern_identification_task = purchase_pattern_identification_component(input_data_folder = association_mining_task.outputs["association_mining_folder"] )
    purchase_pattern_identification_task.set_caching_options(True) #Disable cache to flush out old results on VertexAI

    customer_persona_component_task = customer_persona_component()
    customer_persona_component_task.after(association_mining_task)
    customer_persona_component_task.set_caching_options(True)


if __name__ == "__main__":
    compiler.Compiler().compile(
        pipeline_func=personalization_intelligence_pipeline,
        package_path=str(
            compiled_dir / "personalization-intelligence-plan.yaml"
        )
    )