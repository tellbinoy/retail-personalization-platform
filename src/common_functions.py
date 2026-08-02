from datetime import datetime #for printing time
from zoneinfo import ZoneInfo #for IST timezone
import functools
import pandas as pd
import json
import os
from pathlib import Path
import joblib
from src.config import ARTIFACT_ROOT, BUCKET_NAME, TEST_FOLDER_NAME
from src.gcs_utils import upload_file
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report, roc_auc_score, roc_curve
) #used for scoring the classification
from google.cloud import storage
import google.auth
from google.auth.transport.requests import Request
import io
import inspect

def log_lifecycle(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print(f"Entry - {func.__name__}")
        #Execute the actual function
        result = func(*args, **kwargs)
        print(f"Exit - {func.__name__}")
        return result
    return wrapper


@log_lifecycle
def printRunTime():
    current_ist = datetime.now(ZoneInfo("Asia/Kolkata"))
    print(current_ist.strftime("%Y-%m-%d %H:%M:%S IST"))
@log_lifecycle
def printFileTimeStamp():
    current_ist = datetime.now(ZoneInfo("Asia/Kolkata"))
    print(current_ist.strftime("___%Y%m%d-%H-%M-%S-IST"))
    return current_ist.strftime("___%Y%m%d-%H-%M-%S-IST")

@log_lifecycle
def update_json_file(data_to_save, file_name):
    Path(ARTIFACT_ROOT + "/metadata").mkdir(
        parents=True,
        exist_ok=True
    )
    full_file_path = ARTIFACT_ROOT + "/metadata/" + file_name
    print(f"full_file_path  {full_file_path}")
    metadata = data_to_save
    #file_path = ARTIFACT_ROOT+"/metadata/column_metadata.json"
    #Read existing data if the file exists, otherwise start with an empty dictionary
    if os.path.exists(full_file_path):
        with open(full_file_path, "r") as f:
            try:
                file_data = json.load(f)
            except json.JSONDecodeError:
                file_data = {}  # Handles empty or corrupted files
    else:
        file_data = {}

    #Update the dictionary with your new metadata keys
    file_data.update(metadata)

    #Save the updated dictionary back to the file
    with open(full_file_path, "w") as f:
        json.dump(file_data, f, indent=4)

    upload_file(
        local_file= full_file_path,
        bucket_name=BUCKET_NAME,
        blob_name= "metadata/"+file_name
    )

@log_lifecycle
def use_cloud_artifacts():
    # Running inside Vertex AI
    if (
            os.getenv("CLOUD_ML_JOB_ID") is not None
            or os.getenv("_KFP_RUNTIME") == "true"
    ):
        return True

    # Running from any test under tests/
    for frame in inspect.stack():
        try:
            path = Path(frame.filename).resolve()

            if TEST_FOLDER_NAME in path.parts:
                return True

        except Exception:
            pass

    return False
@log_lifecycle
def print_vertex_environment_variables():

    print("=" * 60)
    print("Environment Variables")
    print("=" * 60)

    for key in sorted(os.environ.keys()):
        if any(word in key.upper() for word in [
            "VERTEX",
            "KFP",
            "PIPELINE",
            "GOOGLE",
            "AIP",
            "CLOUD"
        ]):
            print(f"{key} = {os.environ[key]}")

    print("=" * 60)


def print_runtime_context():
    credentials, project = google.auth.default()

    print("=" * 60)
    print(f"Project            : {project}")
    print(f"Running on Vertex  : {use_cloud_artifacts()}")
    print(f"Credentials Type   : {type(credentials).__name__}")

    # Try to determine the service account email
    service_account = "Unknown"

    # Service Account credentials (Vertex / Cloud Run)
    if hasattr(credentials, "service_account_email"):
        service_account = credentials.service_account_email

    # User credentials (local ADC)
    elif hasattr(credentials, "account"):
        service_account = credentials.account

    # Refresh credentials to populate additional fields if needed
    try:
        credentials.refresh(Request())
    except Exception:
        pass

    print(f"Authenticated As   : {service_account}")
    print("=" * 60)

@log_lifecycle
def open_json_file(file_name):
    running_on_vertex = use_cloud_artifacts() #This tells if the job is on vertex or not
    if running_on_vertex:
        print("Running Inside Vertex")
        client = storage.Client()
        bucket = client.bucket(BUCKET_NAME)
        blob = bucket.blob(f"metadata/{file_name}")
        return json.loads(blob.download_as_text())

    # GCS execution
    else:
        print("Running Outside Vertex")
        full_file_path = ARTIFACT_ROOT + "/metadata/" + file_name
        print(f"full_file_path  {full_file_path}")
        if not os.path.exists(full_file_path):
            raise FileNotFoundError(f"{full_file_path} not found")

        with open(full_file_path) as f:
            return json.load(f)


@log_lifecycle
def save_parquet(dataframe, df_name, file_path = None, index_choice = False):
    if file_path is None:
        # Create folder if it doesn't exist
        Path(ARTIFACT_ROOT+"/data").mkdir(
            parents=True,
            exist_ok=True
        )

        # Save artifacts
        dataframe.to_parquet(
            ARTIFACT_ROOT+"/data/"+df_name+".parquet",
            index=index_choice
        )
        upload_file(
            local_file = ARTIFACT_ROOT+"/data/"+df_name+".parquet",
            bucket_name = BUCKET_NAME,
            blob_name = "data/"+df_name+".parquet"
        )

    else:
        # Create folder if it doesn't exist
        Path(file_path).mkdir(
            parents=True,
            exist_ok=True
        )

        # Save artifacts
        dataframe.to_parquet(
            file_path + df_name + ".parquet",
            index=index_choice
        )
        upload_file(
            local_file=file_path + df_name + ".parquet",
            bucket_name=BUCKET_NAME,
            blob_name= "reports/"+ df_name + ".parquet"
        )

@log_lifecycle
def open_parquet(df_name, file_path=None):
    import io
    from google.cloud import storage

    print(f"ARTIFACT_ROOT = {ARTIFACT_ROOT}")
    print(f"use_cloud_artifacts() = {use_cloud_artifacts()}")

    if use_cloud_artifacts():
        print("Running Inside Vertex")

        client = storage.Client()
        bucket = client.bucket(BUCKET_NAME)

        # Inside Vertex AI runtime, if a custom GCS path is provided
        if file_path is not None:
            print(f"file_path in Vertex: {file_path}")

            # Remove gs://bucket-name/ if present
            blob_path = (
                file_path
                .replace(f"gs://{BUCKET_NAME}/", "")
                .rstrip("/")
            )

            blob = bucket.blob(
                f"{blob_path}/{df_name}.parquet"
            )

        # Default reports/data folders
        else:
            blob = bucket.blob(
                f"data/{df_name}.parquet"
            )

        # Download into memory (no fsspec / gcsfs required)
        parquet_bytes = blob.download_as_bytes()

        return pd.read_parquet(
            io.BytesIO(parquet_bytes)
        )

    elif file_path is not None:
        # Outside Vertex AI, custom local path
        print(f"file_path outside Vertex: {file_path}")

        full_file_path = (
            file_path
            + df_name
            + ".parquet"
        )

        return pd.read_parquet(full_file_path)

    else:
        # Outside Vertex AI, default local artifacts folder
        full_file_path = (
            ARTIFACT_ROOT
            + "/data/"
            + df_name
            + ".parquet"
        )

        if not os.path.exists(full_file_path):
            raise FileNotFoundError(
                f"{full_file_path} not found"
            )

        return pd.read_parquet(full_file_path)

@log_lifecycle
def save_joblib(object_to_save, object_name):
    Path(ARTIFACT_ROOT + "/models").mkdir(
        parents=True,
        exist_ok=True
    )
    full_file_path = ARTIFACT_ROOT+"/models/"+object_name+".joblib"
    joblib.dump(
        object_to_save,
        full_file_path
    )
    upload_file(
        local_file=full_file_path,
        bucket_name=BUCKET_NAME,
        blob_name="models/" + object_name + ".joblib"
    )


@log_lifecycle
def open_joblib(object_name):

    if use_cloud_artifacts():
        print("Running Inside Vertex")
        client = storage.Client()
        bucket = client.bucket(BUCKET_NAME)
        blob = bucket.blob(f"models/{object_name}.joblib")

        # Download the joblib file into memory
        model_bytes = blob.download_as_bytes()

        # Load the model directly from memory
        return joblib.load(io.BytesIO(model_bytes))

    else:
        full_file_path = (ARTIFACT_ROOT +"/models/" +object_name +".joblib")

        if not os.path.exists(full_file_path):
            raise FileNotFoundError(f"{full_file_path} not found")
        return joblib.load(full_file_path)


@log_lifecycle
def model_checker(y_test, y_pred, y_prob, model_name, prev_test_result=None):
    classification_metrics = {
        'Accuracy': accuracy_score(y_test, y_pred),
        'Precision': precision_score(y_test, y_pred),
        'Recall': recall_score(y_test, y_pred),
        'F1 Score': f1_score(y_test, y_pred),
        'ROC-AUC': roc_auc_score(y_test, y_prob)
    }

    test_result = pd.DataFrame(classification_metrics, index=[model_name]).T

    cm_1 = confusion_matrix(y_test, y_pred)

    if prev_test_result is not None:
        test_result = pd.concat([prev_test_result, test_result], axis=1)

    # save test_result
    save_parquet(test_result, "model_evaluation_report - "+model_name, file_path = ARTIFACT_ROOT+"/reports/", index_choice=True)
    return test_result

@log_lifecycle
def should_retrain_model(
    model_path,
    retrain_flag=0,
    retrain_all=0
):
    return (
        retrain_all == 1
        or retrain_flag == 1
        or not os.path.exists(model_path)
    )


@log_lifecycle
def save_text_file(file_content, file_name, folder_path):

    if use_cloud_artifacts():
        from google.cloud import storage
        client = storage.Client()
        bucket = client.bucket(BUCKET_NAME)

        # Remove gs://bucket-name/ if present
        blob_path = (
            folder_path
            .replace(f"gs://{BUCKET_NAME}/", "")
            .rstrip("/")
        )

        blob = bucket.blob(
            f"{blob_path}/{file_name}"
        )

        blob.upload_from_string(
            file_content,
            content_type="text/html"
        )

    else:

        from pathlib import Path
        Path(folder_path).mkdir(
            parents=True,
            exist_ok=True
        )
        with open(
            Path(folder_path) / file_name,
            "w",
            encoding="utf-8"
        ) as f:
            f.write(file_content)

@log_lifecycle
def open_text_file(file_name, folder_path):
    """
    Opens a text file from either the local artifacts folder
    or the GCS bucket.

    Parameters
    ----------
    file_name : str
        Name of the file including extension.
        Example: "executive_business_report.html"

    folder_path : str
        Folder containing the file.
        Example:
            "artifacts/gemini/"
            "gemini/"

    Returns
    -------
    str
        Contents of the text file.
    """

    if use_cloud_artifacts():

        from google.cloud import storage
        bucket_name = ARTIFACT_ROOT.replace("gs://", "")
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(
            folder_path + "/" + file_name
        )
        return blob.download_as_text(
            encoding="utf-8"
        )
    else:
        with open(
                folder_path + "/" + file_name,
                "r",
                encoding="utf-8"
        ) as f:
            return f.read()

from google.cloud import bigquery

from src.config import (
    PROJECT_ID,
    DATASET_ID,
    USE_BIGQUERY
)



