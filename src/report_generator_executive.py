#!/usr/bin/env python3
"""
generate_report.py

Turns a "Retail Personalization Platform" context JSON (campaign_summary,
department_summary, cross_department_summary, persona_summary,
recommendation_evidence) into a polished, standalone CMO-facing HTML report.

Usage:
    python3 generate_report.py <path_to_json> <path_to_output_html>
"""

import json
import sys
from datetime import datetime

from src.common_functions import use_cloud_artifacts, save_text_file
from src.config import ARTIFACT_ROOT
from src.gemini_integration import build_gemini_context


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def fmt_int(n):
    return f"{n:,}"


def fmt_pct(n, decimals=2):
    return f"{n:.{decimals}f}%"


def fmt_x(n, decimals=2):
    return f"{n:.{decimals}f}x"


def safe_div(a, b):
    return a / b if b else 0


# --------------------------------------------------------------------------
# Data loading + derived metrics
# --------------------------------------------------------------------------

def load_data(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def build_model(data):
    platform = data["platform"]
    camp = data["campaign_summary"]["campaign"]
    catalog = data["campaign_summary"]["catalog"]
    quality = data["campaign_summary"]["recommendation_quality"]

    departments = data["department_summary"]["department_summary"]
    cross = data["cross_department_summary"]["cross_department_summary"]
    personas = data["persona_summary"]["persona_summary"]
    evidence = data["recommendation_evidence"]["recommendation_evidence"]

    total_customers = camp["campaign_customers"]

    # Departments ranked by volume (recommendations generated) and by quality (lift)
    dept_by_volume = sorted(departments, key=lambda d: d["recommendations_generated"], reverse=True)
    dept_by_lift = sorted(departments, key=lambda d: d["average_lift"], reverse=True)
    dept_by_confidence = sorted(departments, key=lambda d: d["average_confidence"], reverse=True)

    # Cross-department pairs: separate genuine cross-sell (different departments) from
    # within-department (self) recommendations
    cross_pairs = [c for c in cross if c["triggering_department"] != c["recommended_department"]]
    cross_self = [c for c in cross if c["triggering_department"] == c["recommended_department"]]
    cross_pairs_by_lift = sorted(cross_pairs, key=lambda c: c["average_lift"], reverse=True)
    cross_pairs_by_volume = sorted(cross_pairs, key=lambda c: c["customers"], reverse=True)

    # Personas ranked by size, with computed share of the total campaign
    personas_ranked = sorted(personas, key=lambda p: p["customers"], reverse=True)
    for p in personas_ranked:
        p["_share_pct"] = 100.0 * safe_div(p["customers"], total_customers)
        p["_top_dept"] = p["dominant_departments"][0] if p["dominant_departments"] else None
        # a persona is "concentrated" if its #1 department captures most of its spend
        p["_concentrated"] = bool(p["_top_dept"] and p["_top_dept"]["average_spend_share_pct"] >= 60)

    concentrated_personas = [p for p in personas_ranked if p["_concentrated"]]
    diversified_personas = [p for p in personas_ranked if not p["_concentrated"]]

    # Recommendation evidence: best by volume and by commercial quality (lift)
    evidence_by_volume = sorted(evidence, key=lambda e: e["recommendations_generated"], reverse=True)
    evidence_by_lift = sorted(evidence, key=lambda e: e["average_lift"], reverse=True)

    return {
        "platform": platform,
        "camp": camp,
        "catalog": catalog,
        "quality": quality,
        "total_customers": total_customers,
        "departments": departments,
        "dept_by_volume": dept_by_volume,
        "dept_by_lift": dept_by_lift,
        "dept_by_confidence": dept_by_confidence,
        "cross_pairs_by_lift": cross_pairs_by_lift,
        "cross_pairs_by_volume": cross_pairs_by_volume,
        "cross_self": cross_self,
        "personas_ranked": personas_ranked,
        "concentrated_personas": concentrated_personas,
        "diversified_personas": diversified_personas,
        "evidence_by_volume": evidence_by_volume,
        "evidence_by_lift": evidence_by_lift,
    }


def persona_label(p):
    """Generate a short, human persona name from its dominant department(s)."""
    top = p["_top_dept"]["department"]
    share = p["_top_dept"]["average_spend_share_pct"]
    if share >= 85:
        return f"{top} Specialists"
    if share >= 60:
        return f"{top} Project Buyers"
    # diversified persona -> name after its top two departments
    if len(p["dominant_departments"]) >= 2:
        second = p["dominant_departments"][1]["department"]
        return f"{top} & {second} Shoppers"
    return f"{top} Shoppers"


# --------------------------------------------------------------------------
# HTML rendering
# --------------------------------------------------------------------------

def render(model, generated_ts):
    platform = model["platform"]
    camp = model["camp"]
    catalog = model["catalog"]
    quality = model["quality"]
    total_customers = model["total_customers"]

    top3_volume = model["dept_by_volume"][:3]
    top2_quality = model["dept_by_lift"][:2]
    top_pairs = model["cross_pairs_by_lift"][:4] if model["cross_pairs_by_lift"] else model["cross_self"][:4]
    top_ev_volume = model["evidence_by_volume"][:3]
    top_ev_lift = model["evidence_by_lift"][:3]
    personas = model["personas_ranked"]

    # ---- Executive summary bullets --------------------------------------
    biggest_dept = top3_volume[0]["department"] if top3_volume else "N/A"
    second_dept = top3_volume[1]["department"] if len(top3_volume) > 1 else ""
    best_pair = top_pairs[0] if top_pairs else None

    # ---- Section: KPI cards ---------------------------------------------
    kpi_cards = f"""
    <div class="kpi-grid">
      <div class="kpi-card">
        <span class="kpi-tag">01</span>
        <div class="kpi-value">{fmt_int(camp['campaign_customers'])}</div>
        <div class="kpi-label">Customers in campaign scope</div>
      </div>
      <div class="kpi-card">
        <span class="kpi-tag">02</span>
        <div class="kpi-value">{fmt_pct(camp['recommendation_coverage_pct'])}</div>
        <div class="kpi-label">Recommendation coverage &mdash; {fmt_int(camp['customers_with_recommendations'])} customers reached</div>
      </div>
      <div class="kpi-card">
        <span class="kpi-tag">03</span>
        <div class="kpi-value">{fmt_int(camp['recommendations_generated'])}</div>
        <div class="kpi-label">Recommendations generated &mdash; {camp['average_recommendations_per_customer']:.2f} per customer</div>
      </div>
      <div class="kpi-card">
        <span class="kpi-tag">04</span>
        <div class="kpi-value">{fmt_x(quality['average_lift'])}</div>
        <div class="kpi-label">Average lift &mdash; {fmt_pct(quality['average_confidence']*100)} avg. confidence</div>
      </div>
    </div>
    """

    # ---- Section: Department table --------------------------------------
    def dept_row(d, rank):
        return f"""
        <tr>
          <td class="rank">{rank:02d}</td>
          <td><strong>{d['department']}</strong></td>
          <td>{fmt_int(d['customers_recommended'])}</td>
          <td>{fmt_int(d['recommendations_generated'])}</td>
          <td>{fmt_pct(d['average_confidence']*100)}</td>
          <td>{fmt_x(d['average_lift'])}</td>
          <td>{d['top_triggering_class']} &rarr; {d['top_recommended_class']}</td>
        </tr>"""

    dept_rows_volume = "\n".join(dept_row(d, i + 1) for i, d in enumerate(top3_volume))
    dept_rows_quality = "\n".join(dept_row(d, i + 1) for i, d in enumerate(top2_quality))

    # ---- Section: Cross-department opportunities -------------------------
    def cross_card(c):
        same = c["triggering_department"] == c["recommended_department"]
        arrow = "within" if same else "to"
        return f"""
        <div class="pair-card">
          <div class="pair-route">{c['triggering_department']} <span class="pair-arrow">&rarr;</span> {c['recommended_department']}</div>
          <div class="pair-classes">{c['top_triggering_class']} <span class="pair-arrow">&rarr;</span> {c['top_recommended_class']}</div>
          <div class="pair-metrics">
            <span><strong>{fmt_int(c['customers'])}</strong> customers</span>
            <span><strong>{fmt_pct(c['average_confidence']*100)}</strong> confidence</span>
            <span><strong>{fmt_x(c['average_lift'])}</strong> lift</span>
          </div>
        </div>"""

    cross_cards = "\n".join(cross_card(c) for c in top_pairs)

    # ---- Section: Personas -------------------------------------------------
    def persona_card(p):
        depts = p["dominant_departments"]
        dept_chips = "".join(
            f'<span class="chip">{d["department"]} &middot; {fmt_pct(d["average_spend_share_pct"], 1)}</span>'
            for d in depts
        )
        tag = "Concentrated" if p["_concentrated"] else "Diversified"
        return f"""
        <div class="persona-card">
          <div class="persona-head">
            <h4>{persona_label(p)}</h4>
            <span class="persona-badge {'badge-concentrated' if p['_concentrated'] else 'badge-diversified'}">{tag}</span>
          </div>
          <div class="persona-meta">Cluster {p['persona_cluster']} &middot; {fmt_int(p['customers'])} customers &middot; {fmt_pct(p['_share_pct'], 1)} of campaign</div>
          <div class="chip-row">{dept_chips}</div>
        </div>"""

    persona_cards = "\n".join(persona_card(p) for p in personas)

    # ---- Section: Recommendation evidence ---------------------------------
    def evidence_row(e, rank):
        return f"""
        <tr>
          <td class="rank">{rank:02d}</td>
          <td><strong>{e['recommended_department']}</strong></td>
          <td>{e['recommended_class']}</td>
          <td>{fmt_int(e['customers_impacted'])}</td>
          <td>{fmt_int(e['recommendations_generated'])}</td>
          <td>{fmt_pct(e['average_confidence']*100)}</td>
          <td>{fmt_x(e['average_lift'])}</td>
          <td>{e['top_triggering_department']}: {e['top_triggering_class']}</td>
        </tr>"""

    evidence_rows_volume = "\n".join(evidence_row(e, i + 1) for i, e in enumerate(top_ev_volume))
    evidence_rows_lift = "\n".join(evidence_row(e, i + 1) for i, e in enumerate(top_ev_lift))

    # ---- Section: Recommendations / priorities (derived) -------------------
    reco_items = []
    if best_pair:
        reco_items.append(f"""
        <div class="reco-card">
          <div class="reco-head">
            <strong>Scale the {best_pair['triggering_department']} &rarr; {best_pair['recommended_department']} bundle</strong>
            <span class="conf-tag conf-high">High confidence</span>
          </div>
          <p>The <em>{best_pair['top_triggering_class']}</em> &rarr; <em>{best_pair['top_recommended_class']}</em> pairing shows
          the strongest lift in the catalog at {fmt_x(best_pair['average_lift'])}, with {fmt_pct(best_pair['average_confidence']*100)} confidence
          across {fmt_int(best_pair['customers'])} customers. This is the single highest-value pattern in the data and merits
          dedicated bundle offers and placement.</p>
        </div>""")

    if top_ev_lift:
        e = top_ev_lift[0]
        reco_items.append(f"""
        <div class="reco-card">
          <div class="reco-head">
            <strong>Prioritize {e['recommended_class']} ({e['recommended_department']}) recommendations</strong>
            <span class="conf-tag conf-high">High confidence</span>
          </div>
          <p>{e['recommended_class']} recommendations convert at {fmt_pct(e['average_confidence']*100)} confidence with
          {fmt_x(e['average_lift'])} lift, reaching {fmt_int(e['customers_impacted'])} customers &mdash; the strongest
          single product-class opportunity by commercial quality.</p>
        </div>""")

    if top3_volume:
        d = top3_volume[0]
        reco_items.append(f"""
        <div class="reco-card">
          <div class="reco-head">
            <strong>Protect the {d['department']} recommendation engine</strong>
            <span class="conf-tag conf-high">High confidence</span>
          </div>
          <p>{d['department']} is the largest single driver of volume, reaching {fmt_int(d['customers_recommended'])} customers
          and generating {fmt_int(d['recommendations_generated'])} recommendations. Even modest efficiency gains here move
          the broadest share of the campaign.</p>
        </div>""")

    if concentrated_p := model["concentrated_personas"][:2]:
        names = " and ".join(f'&ldquo;{persona_label(p)}&rdquo;' for p in concentrated_p)
        combined = sum(p["customers"] for p in concentrated_p)
        reco_items.append(f"""
        <div class="reco-card">
          <div class="reco-head">
            <strong>Build dedicated pathways for {names}</strong>
            <span class="conf-tag conf-medium">Medium confidence</span>
          </div>
          <p>These personas concentrate the large majority of their spend in a single department
          ({fmt_int(combined)} customers combined). Tailored, single-category messaging will land better than
          general cross-department campaigns for this group.</p>
        </div>""")

    if len(top3_volume) > 1:
        d2 = top3_volume[1]
        reco_items.append(f"""
        <div class="reco-card">
          <div class="reco-head">
            <strong>Bundle {d2['department']} with adjacent categories</strong>
            <span class="conf-tag conf-medium">Medium confidence</span>
          </div>
          <p>{d2['department']} is the second-largest volume driver ({fmt_int(d2['customers_recommended'])} customers,
          {fmt_int(d2['recommendations_generated'])} recommendations) at {fmt_pct(d2['average_confidence']*100)} confidence.
          Project-based bundling can lift both reach and basket size here.</p>
        </div>""")

    reco_html = "\n".join(reco_items)

    # ---- Section: Budget allocation (derived proportionally) ---------------
    total_dept_recs = sum(d["recommendations_generated"] for d in model["departments"]) or 1
    high_value_pct = min(40, max(20, round(100 * safe_div(
        sum(c["customers"] for c in top_pairs), total_customers))))
    volume_pct = min(45, max(25, round(100 * safe_div(
        sum(d["customers_recommended"] for d in top3_volume), total_customers))))
    persona_pct = min(20, max(10, round(100 * safe_div(
        sum(p["customers"] for p in model["concentrated_personas"]), total_customers))))
    remainder_pct = max(5, 100 - high_value_pct - volume_pct - persona_pct)

    budget_html = f"""
    <div class="budget-grid">
      <div class="budget-bar">
        <div class="budget-fill" style="width:{high_value_pct}%"></div>
        <div class="budget-label"><strong>{high_value_pct}%</strong> High-lift cross-sell ({', '.join(sorted(set([c['triggering_department'] for c in top_pairs] + [c['recommended_department'] for c in top_pairs])))})</div>
      </div>
      <div class="budget-bar">
        <div class="budget-fill" style="width:{volume_pct}%"></div>
        <div class="budget-label"><strong>{volume_pct}%</strong> High-volume engagement ({', '.join(d['department'] for d in top3_volume)})</div>
      </div>
      <div class="budget-bar">
        <div class="budget-fill" style="width:{persona_pct}%"></div>
        <div class="budget-label"><strong>{persona_pct}%</strong> Persona-specific nurturing (concentrated segments)</div>
      </div>
      <div class="budget-bar">
        <div class="budget-fill" style="width:{remainder_pct}%"></div>
        <div class="budget-label"><strong>{remainder_pct}%</strong> Emerging &amp; test-and-scale opportunities</div>
      </div>
    </div>
    """

    # ---- Executive priorities ----------------------------------------------
    priority_blocks = []
    if best_pair:
        priority_blocks.append(
            f"Maximize revenue from the {best_pair['triggering_department']} &rarr; {best_pair['recommended_department']} "
            f"pairing, the highest-lift relationship in the catalog at {fmt_x(best_pair['average_lift'])}."
        )
    if top3_volume:
        priority_blocks.append(
            f"Leverage high-volume engagement in {', '.join(d['department'] for d in top3_volume)} to broaden "
            f"reach and basket size through enhanced personalization."
        )
    if model["concentrated_personas"]:
        names = ", ".join(f'&ldquo;{persona_label(p)}&rdquo;' for p in model["concentrated_personas"][:2])
        priority_blocks.append(
            f"Deepen loyalty through persona-centric campaigns for concentrated segments such as {names}."
        )

    priorities_html = "\n".join(
        f"""<blockquote><strong>High Priority</strong><br/>{b}</blockquote>""" for b in priority_blocks
    )

    generated_date = datetime.fromisoformat(camp["generated_timestamp"]).strftime("%B %d, %Y")

    # ------------------------------------------------------------------------
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{platform['project_name']} &mdash; Campaign Brief</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Zilla+Slab:wght@400;500;600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@500&display=swap" rel="stylesheet">
<style>
  :root {{
    --navy: #182634;
    --navy-soft: #24384a;
    --paper: #eef1f0;
    --paper-card: #ffffff;
    --orange: #d9530f;
    --orange-soft: #f7ded0;
    --brass: #9c7a3c;
    --line: #d7dcd8;
    --ink: #182634;
    --ink-soft: #55636d;
    --good: #2f6b4f;
    --good-bg: #e2eee6;
    --med-bg: #f2ecd9;
    --med-text: #8a6a1f;
  }}

  * {{ box-sizing: border-box; }}

  body {{
    margin: 0;
    background: var(--paper);
    background-image:
      linear-gradient(var(--line) 1px, transparent 1px),
      linear-gradient(90deg, var(--line) 1px, transparent 1px);
    background-size: 32px 32px;
    color: var(--ink);
    font-family: 'IBM Plex Sans', sans-serif;
    line-height: 1.6;
  }}

  .sheet {{
    max-width: 980px;
    margin: 48px auto;
    background: var(--paper-card);
    border: 1px solid var(--line);
    box-shadow: 0 30px 60px -30px rgba(24,38,52,0.35);
  }}

  header.cover {{
    background: var(--navy);
    color: #fff;
    padding: 56px 56px 40px;
    position: relative;
    overflow: hidden;
  }}
  header.cover::after {{
    content: "";
    position: absolute;
    right: -60px; top: -60px;
    width: 220px; height: 220px;
    border: 2px solid rgba(255,255,255,0.12);
    border-radius: 50%;
  }}
  .eyebrow {{
    font-family: 'IBM Plex Mono', monospace;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    font-size: 12px;
    color: var(--orange);
    margin-bottom: 14px;
  }}
  header.cover h1 {{
    font-family: 'Zilla Slab', serif;
    font-weight: 700;
    font-size: 40px;
    line-height: 1.15;
    margin: 0 0 10px;
    max-width: 620px;
  }}
  .cover-sub {{
    color: #c7d2da;
    max-width: 560px;
    font-size: 15px;
  }}
  .cover-meta {{
    display: flex;
    gap: 28px;
    margin-top: 28px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12px;
    color: #93a4b2;
  }}

  main {{ padding: 48px 56px 64px; }}

  h2 {{
    font-family: 'Zilla Slab', serif;
    font-size: 26px;
    font-weight: 700;
    color: var(--navy);
    margin: 56px 0 8px;
    padding-bottom: 10px;
    border-bottom: 2px solid var(--navy);
    display: flex;
    align-items: baseline;
    gap: 10px;
  }}
  h2:first-of-type {{ margin-top: 0; }}
  h2 .num {{
    font-family: 'IBM Plex Mono', monospace;
    color: var(--orange);
    font-size: 16px;
  }}
  h3 {{
    font-family: 'Zilla Slab', serif;
    font-size: 19px;
    color: var(--navy-soft);
    margin: 28px 0 10px;
  }}
  h4 {{ margin: 0; font-family: 'Zilla Slab', serif; font-size: 16px; color: var(--navy); }}

  p {{ color: var(--ink-soft); margin: 10px 0; }}
  strong {{ color: var(--ink); }}

  .kpi-grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 14px;
    margin: 20px 0 8px;
  }}
  .kpi-card {{
    border: 1px solid var(--line);
    border-top: 3px solid var(--orange);
    padding: 16px 14px;
    position: relative;
    background: #fbfbfa;
  }}
  .kpi-tag {{
    position: absolute; top: 10px; right: 12px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px; color: #b7bfb9;
  }}
  .kpi-value {{
    font-family: 'Zilla Slab', serif;
    font-size: 28px;
    font-weight: 700;
    color: var(--navy);
  }}
  .kpi-label {{
    font-size: 12.5px;
    color: var(--ink-soft);
    margin-top: 4px;
  }}

  table {{
    width: 100%;
    border-collapse: collapse;
    margin: 14px 0 8px;
    font-size: 13.5px;
  }}
  th {{
    text-align: left;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: var(--ink-soft);
    border-bottom: 1px solid var(--navy);
    padding: 8px 10px;
  }}
  td {{
    padding: 9px 10px;
    border-bottom: 1px solid var(--line);
    vertical-align: top;
  }}
  td.rank, th:first-child {{
    font-family: 'IBM Plex Mono', monospace;
    color: var(--orange);
    width: 30px;
  }}
  tr:hover td {{ background: #f7f8f6; }}

  .pair-grid {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 14px;
    margin: 16px 0;
  }}
  .pair-card {{
    border: 1px solid var(--line);
    padding: 16px;
    background: #fbfbfa;
  }}
  .pair-route {{
    font-family: 'Zilla Slab', serif;
    font-weight: 600;
    font-size: 16px;
    color: var(--navy);
  }}
  .pair-classes {{
    font-size: 13px;
    color: var(--ink-soft);
    margin-top: 4px;
    font-style: italic;
  }}
  .pair-arrow {{ color: var(--orange); font-style: normal; }}
  .pair-metrics {{
    display: flex;
    gap: 16px;
    margin-top: 12px;
    font-size: 12.5px;
    color: var(--ink-soft);
    border-top: 1px dashed var(--line);
    padding-top: 10px;
  }}
  .pair-metrics strong {{ color: var(--navy); }}

  .persona-grid {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
    margin: 16px 0;
  }}
  .persona-card {{
    border: 1px solid var(--line);
    padding: 14px 16px;
    background: #fff;
  }}
  .persona-head {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
  }}
  .persona-badge {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px;
    padding: 3px 8px;
    border-radius: 20px;
    white-space: nowrap;
  }}
  .badge-concentrated {{ background: var(--orange-soft); color: var(--orange); }}
  .badge-diversified {{ background: #e5e9ec; color: var(--navy-soft); }}
  .persona-meta {{
    font-size: 11.5px;
    color: var(--ink-soft);
    margin: 4px 0 10px;
    font-family: 'IBM Plex Mono', monospace;
  }}
  .chip-row {{ display: flex; flex-wrap: wrap; gap: 6px; }}
  .chip {{
    font-size: 11.5px;
    border: 1px solid var(--line);
    padding: 3px 8px;
    color: var(--ink-soft);
  }}

  .reco-card {{
    border-left: 3px solid var(--orange);
    background: #fbfbfa;
    padding: 14px 18px;
    margin: 14px 0;
  }}
  .reco-head {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
  }}
  .reco-head strong {{ font-family: 'Zilla Slab', serif; font-size: 16px; }}
  .conf-tag {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10.5px;
    padding: 3px 9px;
    white-space: nowrap;
  }}
  .conf-high {{ background: var(--good-bg); color: var(--good); }}
  .conf-medium {{ background: var(--med-bg); color: var(--med-text); }}

  .budget-grid {{ margin: 18px 0; display: flex; flex-direction: column; gap: 14px; }}
  .budget-bar {{
    background: #e9ece9;
    height: 34px;
    position: relative;
    border: 1px solid var(--line);
  }}
  .budget-fill {{
    position: absolute; left: 0; top: 0; bottom: 0;
    background: linear-gradient(90deg, var(--navy), var(--orange));
    opacity: 0.9;
  }}
  .budget-label {{
    position: absolute; left: 10px; top: 0; bottom: 0;
    display: flex; align-items: center;
    font-size: 12.5px;
    color: var(--navy);
    mix-blend-mode: normal;
  }}

  blockquote {{
    margin: 14px 0;
    padding: 14px 18px;
    border-left: 3px solid var(--navy);
    background: #f4f6f5;
    font-size: 14px;
    color: var(--navy-soft);
  }}

  footer {{
    padding: 24px 56px 40px;
    font-size: 11.5px;
    color: var(--ink-soft);
    border-top: 1px solid var(--line);
    font-family: 'IBM Plex Mono', monospace;
    display: flex;
    justify-content: space-between;
  }}

  @media (max-width: 720px) {{
    .kpi-grid, .pair-grid, .persona-grid {{ grid-template-columns: 1fr; }}
    header.cover, main {{ padding-left: 24px; padding-right: 24px; }}
  }}
</style>
</head>
<body>
<div class="sheet">

  <header class="cover">
    <div class="eyebrow">{platform['problem_type']}</div>
    <h1>{platform['project_name']}<br/>Campaign Brief</h1>
    <p class="cover-sub">Personalization performance, department opportunities and customer personas from the latest recommendation run, prepared for the Chief Marketing Officer.</p>
    <div class="cover-meta">
      <span>GENERATED &middot; {generated_date}</span>
      <span>SCOPE &middot; {fmt_int(total_customers)} CUSTOMERS</span>
    </div>
  </header>

  <main>

    <h2><span class="num">01</span> Executive Summary</h2>
    {kpi_cards}
    <p>The campaign engaged <strong>{fmt_int(camp['campaign_customers'])}</strong> customers, delivering personalized
    recommendations to <strong>{fmt_int(camp['customers_with_recommendations'])}</strong> of them &mdash;
    <strong>{fmt_pct(camp['recommendation_coverage_pct'])}</strong> coverage &mdash; with an average confidence of
    <strong>{fmt_pct(quality['average_confidence']*100)}</strong> and an average lift of <strong>{fmt_x(quality['average_lift'])}</strong>,
    meaning recommended customers are substantially more likely to purchase the suggested product.</p>
    <p>The biggest opportunities sit in two places: broad-reach volume from <strong>{biggest_dept}</strong>{f' and {second_dept}' if second_dept else ''},
    and exceptional cross-sell intent{f" led by the {best_pair['triggering_department']} &rarr; {best_pair['recommended_department']} pairing ({fmt_x(best_pair['average_lift'])} lift)" if best_pair else ''}.
    A long tail of concentrated personas also presents a clear segmentation opportunity for dedicated campaigns.</p>

    <h2><span class="num">02</span> Campaign Overview</h2>
    <p>The platform generated <strong>{fmt_int(camp['recommendations_generated'])}</strong> unique recommendations,
    averaging <strong>{camp['average_recommendations_per_customer']:.2f}</strong> per recommended customer. Activity spanned
    <strong>{catalog['triggering_departments']}</strong> triggering departments and <strong>{catalog['recommended_departments']}</strong>
    recommended departments, across <strong>{catalog['triggering_classes']}</strong> triggering product classes and
    <strong>{catalog['recommended_classes']}</strong> recommended product classes &mdash; evidence of a diverse, catalog-wide
    personalization footprint rather than a narrow set of best-sellers.</p>

    <h2><span class="num">03</span> Department Insights</h2>
    <h3>Largest opportunities by volume</h3>
    <table>
      <tr><th>#</th><th>Department</th><th>Customers</th><th>Recs.</th><th>Confidence</th><th>Lift</th><th>Top pairing</th></tr>
      {dept_rows_volume}
    </table>
    <h3>Highest-impact by recommendation quality</h3>
    <table>
      <tr><th>#</th><th>Department</th><th>Customers</th><th>Recs.</th><th>Confidence</th><th>Lift</th><th>Top pairing</th></tr>
      {dept_rows_quality}
    </table>
    <p><em>Implication:</em> prioritize {', '.join(d['department'] for d in top3_volume)} for broad-reach campaigns, and
    treat {', '.join(d['department'] for d in top2_quality)} as high-value, high-conversion opportunities better suited
    to targeted, bundled promotions than mass reach.</p>

    <h2><span class="num">04</span> Cross-Department Opportunities</h2>
    <p>The strongest department-to-department purchasing relationships in the data:</p>
    <div class="pair-grid">
      {cross_cards}
    </div>

    <h2><span class="num">05</span> Customer Personas</h2>
    <p>{fmt_int(len(personas))} purchasing personas were identified. <strong>{len(model['concentrated_personas'])}</strong>
    are concentrated in a single department (60%+ of spend) and are strong candidates for dedicated, single-category
    campaigns; the remaining <strong>{len(model['diversified_personas'])}</strong> span multiple departments and suit
    cross-category bundles.</p>
    <div class="persona-grid">
      {persona_cards}
    </div>

    <h2><span class="num">06</span> Product Recommendation Insights</h2>
    <h3>Highest volume &amp; broadest impact</h3>
    <table>
      <tr><th>#</th><th>Department</th><th>Class</th><th>Customers</th><th>Recs.</th><th>Confidence</th><th>Lift</th><th>Top trigger</th></tr>
      {evidence_rows_volume}
    </table>
    <h3>Highest commercial value</h3>
    <table>
      <tr><th>#</th><th>Department</th><th>Class</th><th>Customers</th><th>Recs.</th><th>Confidence</th><th>Lift</th><th>Top trigger</th></tr>
      {evidence_rows_lift}
    </table>

    <h2><span class="num">07</span> Campaign Recommendations</h2>
    {reco_html}

    <h2><span class="num">08</span> Budget Allocation Suggestions</h2>
    <p>Suggested allocation weights, derived from each opportunity's share of impacted customers:</p>
    {budget_html}

    <h2><span class="num">09</span> Executive Priorities</h2>
    {priorities_html}

  </main>

  <footer>
    <span>{platform['project_name']}</span>
    <span>Confidential &middot; Prepared for CMO review</span>
  </footer>

</div>
</body>
</html>
"""
    return html


def generate_report():

    data = build_gemini_context()
    print("data is ")
    print(data)
    model = build_model(data)
    print(f"model is {model}")
    html = render(model, data["campaign_summary"]["campaign"]["generated_timestamp"])

    #with open("insights.html", "w", encoding="utf-8") as f:
    #    f.write(html)

    if use_cloud_artifacts():
        save_text_file(
            html,
            "cmo_campaign_brief.html",
            "gemini"
        )
    else:
        save_text_file(
            html,
            "cmo_campaign_brief.html",
            ARTIFACT_ROOT + "/gemini"
        )

    #print(f"Report written to {output_path}")
    return 0


if __name__ == "__main__":
    generate_report()
