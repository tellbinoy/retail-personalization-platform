from src.common_functions import log_lifecycle
from src.config import ARTIFACT_ROOT
from src.report_generator_executive import generate_report


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
    #generate_campaign_operations_brief(context)

    #build_dashboard(context)
    generate_report()

if __name__ == "__main__":
    run()

