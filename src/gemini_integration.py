import os

from google import genai
from google.cloud import storage

from src.common_functions import (
    open_json_file,
    log_lifecycle,
    update_json_file,
    use_cloud_artifacts, save_text_file
)

from src.config import (
    PROJECT_ID,
    GEMINI_MODEL,
    ARTIFACT_ROOT,
    BUCKET_NAME
)

from src.gemini_prompts_cxo import prompt_CMO_campaign
from src.gemini_prompts_operations import prompt_marketing_manager_campaign


# Test Gemini

@log_lifecycle
def test_gemini():
    client = genai.Client(
        vertexai=True,
        project=PROJECT_ID,
        location="asia-south1"
    )
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents="Reply only with SUCCESS."
    )
    print(response.text)


# Gemini Client

@log_lifecycle
def get_gemini_client():
    client = genai.Client(
        vertexai=True,
        project=PROJECT_ID,
        location="asia-south1"
    )
    return client


# Gemini Call
@log_lifecycle
def call_gemini(prompt,model_used=GEMINI_MODEL):
    client = get_gemini_client()
    response = client.models.generate_content(
        model=model_used,
        contents=prompt
    )

    if not response.text:
        raise RuntimeError(
            "Gemini returned an empty response."
        )

    return response.text


# Build Context

@log_lifecycle
def build_gemini_context():

    context = {
        "platform": {
            "project_name":
                "Retail Personalization Platform",

            "problem_type":
                "Campaign Intelligence and Product Recommendation"
        },

        "campaign_summary":
            open_json_file(
                "campaign_summary.json"
            ),

        "department_summary":
            open_json_file(
                "department_summary.json"
            ),

        "cross_department_summary":
            open_json_file(
                "cross_department_summary.json"
            ),

        "persona_summary":
            open_json_file(
                "persona_summary.json"
            ),

        "recommendation_evidence":
            open_json_file(
                "recommendation_evidence.json"
            )

    }

    update_json_file(
        context,
        "gemini_context.json"
    )

    return context


# CMO Campaign Brief

@log_lifecycle
def generate_cmo_campaign_brief(
    context=None
):

    if context is None:
        context = build_gemini_context()

    prompt = (
        prompt_CMO_campaign
        + str(context)
    )

    os.makedirs(
        ARTIFACT_ROOT + "/gemini",
        exist_ok=True
    )

    summary = call_gemini(prompt)

    if use_cloud_artifacts():
        save_text_file(
            summary,
            "cmo_campaign_brief.html",
            "gemini"
        )
    else:
        save_text_file(
            summary,
            "cmo_campaign_brief.html",
            ARTIFACT_ROOT + "/gemini"
        )

    return summary



# Marketing Campaign Playbook


@log_lifecycle
def generate_campaign_operations_brief(
    context=None
):

    if context is None:
        context = build_gemini_context()

    prompt = (
        prompt_marketing_manager_campaign
        + str(context)
    )

    os.makedirs(
        ARTIFACT_ROOT + "/gemini",
        exist_ok=True
    )

    summary = call_gemini(prompt)

    output_file = (
        ARTIFACT_ROOT
        + "/gemini/marketing_campaign_playbook.html"
    )

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(summary)

    print(
        f"Results generated in {output_file}"
    )

    if use_cloud_artifacts():

        client = storage.Client()

        bucket = client.bucket(
            BUCKET_NAME
        )

        blob = bucket.blob(
            "gemini/marketing_campaign_playbook.html"
        )

        blob.upload_from_filename(
            output_file,
            content_type="text/html"
        )

        print(
            f"Uploaded to "
            f"gs://{BUCKET_NAME}/gemini/"
            f"marketing_campaign_playbook.html"
        )

    return summary


# Pipeline Entry Point
