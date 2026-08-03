## Gemini Config
###############################################################

GEMINI_MODEL = "gemini-2.5-flash" #"gemini-2.5-pro"
GEMINI_TEMPERATURE = 0.2
GEMINI_MAX_OUTPUT_TOKENS = 4096
ENABLE_GUARDRAILS = True

## Docker Runtime Cnfig
PROJECT_ID = "retailmarketing-123"
DATASET_ID = "analytics"

## BigQuery Config
###############################################################
USE_BIGQUERY=True #False if data is being pulled from local sample CSV
BUCKET_NAME = "retail-decision-intelligence-artifacts"


## GCS Bucket Config
###############################################################
ARTIFACT_ROOT = "artifacts" #for local execution
#ARTIFACT_ROOT = "gs://retail-decision-intelligence-artifacts"  #for GCP execution


## FP Tree
###############################################################
RANDOM_STATE = 42
TEST_FOLDER_NAME = "test"
MIN_SUPPORT = 0.02
MIN_THRESHOLD = 0.5


## Purchase Pattern Identification
###############################################################
PURCHASE_THRESHOLD = 0.8
CUSTOMER_PERSONA_BUCKETS = 20

## Bundle Recommendation
###############################################################
RECOMMENDATION_BUNDLE_CUTOFF = 3

