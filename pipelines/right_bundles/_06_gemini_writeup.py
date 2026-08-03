from src.common_functions import log_lifecycle
from src.config import ARTIFACT_ROOT

# Bring the facts regarding customers at risk, action items to be done, how to turn things around
#
# Vertex AI - Inputs
# ----------------
# artifacts/metadata/gemini_context.json
#
# Vertex AI - Outputs
# ----------------
# artifacts/gemini/executive_summary.html
# artifacts/gemini/executive_report.html

@log_lifecycle
def run(context=None):
    from src.gemini_integration import generate_cmo_campaign_brief, generate_campaign_operations_brief, build_gemini_context
    if context is None:
        context = build_gemini_context()

    #generate_cmo_campaign_brief(context)
    generate_campaign_operations_brief(context)

if __name__ == "__main__":
    from src.gemini_integration import build_gemini_context
    run(context = build_gemini_context())

