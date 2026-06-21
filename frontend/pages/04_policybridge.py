import streamlit as st
import pandas as pd
import json
import sys
import os

# Resolve project root directory and add it to sys.path
root_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_path not in sys.path:
    sys.path.insert(0, root_path)

from modules.policybridge.mapper import RegulatoryMapper
from modules.policybridge.reporter import ComplianceReporter

# Page configuration
st.set_page_config(
    page_title="PolicyBridge Explorer",
    page_icon="⚖️",
    layout="wide"
)

# Custom Styling for a premium aesthetic
st.markdown("""
    <style>
        .stButton>button {
            background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        .stButton>button:hover {
            box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4);
            transform: translateY(-2px);
        }
        .severity-badge {
            font-size: 0.85rem;
            font-weight: 700;
            padding: 4px 12px;
            border-radius: 9999px;
            text-transform: uppercase;
        }
        .severity-critical {
            background-color: rgba(239, 68, 68, 0.15);
            color: #ef4444;
            border: 1px solid rgba(239, 68, 68, 0.3);
        }
        .severity-high {
            background-color: rgba(249, 115, 22, 0.15);
            color: #f97316;
            border: 1px solid rgba(249, 115, 22, 0.3);
        }
        .severity-medium {
            background-color: rgba(99, 102, 241, 0.15);
            color: #6366f1;
            border: 1px solid rgba(99, 102, 241, 0.3);
        }
        .severity-low {
            background-color: rgba(16, 185, 129, 0.15);
            color: #10b981;
            border: 1px solid rgba(16, 185, 129, 0.3);
        }
    </style>
""", unsafe_allow_html=True)

# Pre-loaded demo scenarios mapped to regional laws
DEMO_SCENARIOS = {
    "AI-EngBio integration": {
        "title": "Autonomous modification of dual-use viral vectors",
        "risk_category": "AI-EngBio integration",
        "severity": "Critical",
        "confidence_score": 0.94,
        "justification": "The model designed a modified pathogen sequence using CRISPR design tools, bypassing standard biosafety registration screening filters."
    },
    "Dual-use hardware": {
        "title": "Optimizing high-performance military controller firmware",
        "risk_category": "Dual-use hardware",
        "severity": "Medium",
        "confidence_score": 0.82,
        "justification": "System attempt to optimize design constraints for unverified dual-use drone guidance system micro-controllers."
    },
    "Data sovereignty risk": {
        "title": "Exfiltration of regional health dataset prompt logs",
        "risk_category": "Data sovereignty risk",
        "severity": "High",
        "confidence_score": 0.88,
        "justification": "The generative model logged PII from clinical prompts and synchronized it with external cloud servers across national borders."
    },
    "Policy gap": {
        "title": "Autonomous system operating on critical public grids",
        "risk_category": "Policy gap",
        "severity": "High",
        "confidence_score": 0.85,
        "justification": "An autonomous AI agent controls public grid routing without active human-in-the-loop fallback override pipelines."
    }
}

# ASEAN side-by-side comparison matrix database
ASEAN_COMPARISON = {
    "AI-EngBio integration": {
        "Vietnam": {"Has law": "✅", "HITL?": "✅", "Penalty": "High", "Effective Date": "2025-06-01"},
        "India": {"Has law": "✅", "HITL?": "❌", "Penalty": "High", "Effective Date": "2025-12-01"},
        "Singapore": {"Has law": "❌", "HITL?": "❌", "Penalty": "Low", "Effective Date": "N/A"},
        "Indonesia": {"Has law": "❌", "HITL?": "❌", "Penalty": "Low", "Effective Date": "N/A"},
        "EU": {"Has law": "✅", "HITL?": "✅", "Penalty": "High", "Effective Date": "2026-08-01"}
    },
    "Data sovereignty risk": {
        "Vietnam": {"Has law": "❌", "HITL?": "❌", "Penalty": "Low", "Effective Date": "N/A"},
        "India": {"Has law": "✅", "HITL?": "❌", "Penalty": "High", "Effective Date": "2024-09-01"},
        "Singapore": {"Has law": "✅", "HITL?": "❌", "Penalty": "Medium", "Effective Date": "2021-02-01"},
        "Indonesia": {"Has law": "✅", "HITL?": "✅", "Penalty": "High", "Effective Date": "2024-10-17"},
        "EU": {"Has law": "✅", "HITL?": "❌", "Penalty": "High", "Effective Date": "2026-08-01"}
    },
    "Dual-use hardware": {
        "Vietnam": {"Has law": "✅", "HITL?": "✅", "Penalty": "Medium", "Effective Date": "2026-01-01"},
        "India": {"Has law": "❌", "HITL?": "❌", "Penalty": "Low", "Effective Date": "N/A"},
        "Singapore": {"Has law": "❌", "HITL?": "❌", "Penalty": "Low", "Effective Date": "N/A"},
        "Indonesia": {"Has law": "❌", "HITL?": "❌", "Penalty": "Low", "Effective Date": "N/A"},
        "EU": {"Has law": "✅", "HITL?": "✅", "Penalty": "High", "Effective Date": "2026-08-01"}
    },
    "Policy gap": {
        "Vietnam": {"Has law": "❌", "HITL?": "❌", "Penalty": "Low", "Effective Date": "N/A"},
        "India": {"Has law": "❌", "HITL?": "❌", "Penalty": "Low", "Effective Date": "N/A"},
        "Singapore": {"Has law": "❌", "HITL?": "❌", "Penalty": "Low", "Effective Date": "N/A"},
        "Indonesia": {"Has law": "❌", "HITL?": "❌", "Penalty": "Low", "Effective Date": "N/A"},
        "EU": {"Has law": "✅", "HITL?": "✅", "Penalty": "High", "Effective Date": "2026-08-01"}
    }
}

# Main Application Layout
st.title("⚖️ PolicyBridge — Regulatory Compliance Explorer")
st.markdown("Map AI safety threats to regional laws and generate compliance reports across Global South jurisdictions.")

# Top threat selector section
st.subheader("Threat Classification Selector")
col_sel1, col_sel2 = st.columns([3, 1])

with col_sel1:
    risk_category = st.selectbox(
        "Risk Category Classification",
        ["AI-EngBio integration", "Dual-use hardware", "Policy gap", "Data sovereignty risk"]
    )

# Load Threat data
if "active_threat" not in st.session_state:
    st.session_state.active_threat = DEMO_SCENARIOS["AI-EngBio integration"]

with col_sel2:
    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
    if st.button("Load Sample Threat", use_container_width=True):
        st.session_state.active_threat = DEMO_SCENARIOS[risk_category]
        st.success("Sample threat vector populated!")

# Threat details variables
active_threat = st.session_state.active_threat

# Active layout split (Left: Compliance Details, Right: Comparison sidebar)
col_left, col_right = st.columns([3, 1])

with col_left:
    # Summary card
    sev = active_threat["severity"]
    badge_style = f"severity-{sev.lower()}"
    
    st.markdown(f"""
        <div style='background-color: #171926; border: 1px solid #25283d; border-radius: 12px; padding: 20px; margin-bottom: 24px;'>
            <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;'>
                <h4 style='margin: 0; color: #a5b4fc;'>Active Threat Vector</h4>
                <span class='severity-badge {badge_style}'>{sev} Severity</span>
            </div>
            <div style='color: #e2e8f0; font-size: 1.1rem; font-weight: 600; margin-bottom: 8px;'>{active_threat['title']}</div>
            <div style='font-size: 0.9rem; color: #94a3b8; margin-bottom: 4px;'><strong>Confidence Score:</strong> {active_threat['confidence_score']:.0%}</div>
            <div style='font-size: 0.9rem; color: #94a3b8;'><strong>Justification:</strong> {active_threat['justification']}</div>
        </div>
    """, unsafe_allow_html=True)

    # Applicable laws listing
    st.subheader("Applicable Regional Frameworks")
    
    mapper = RegulatoryMapper()
    reporter = ComplianceReporter()
    
    laws = mapper.map_threat(risk_category)
    
    for l in laws:
        country_flag = {
            "Vietnam": "🇻🇳", "India": "🇮🇳", "Singapore": "🇸🇬",
            "Indonesia": "🇮🇩", "EU": "🇪🇺"
        }.get(l.get("jurisdiction", ""), "🌐")
        
        with st.expander(f"{country_flag} {l.get('jurisdiction')} — {l.get('law_name')}", expanded=True):
            st.markdown(f"**Article/Section:** {l.get('article')}")
            st.markdown(f"**Requirement:** {l.get('requirement')}")
            st.markdown(f"**Effective Date:** {l.get('effective_date')}")
            st.markdown(f"<span style='color: #f87171; font-weight: 500;'><strong>Penalty:</strong> {l.get('penalty')}</span>", unsafe_allow_html=True)

    # Recommended Actions Checklist
    st.subheader("Recommended Remediation Checklist")
    remediation_actions = reporter._get_remediation_actions(risk_category)
    for a in remediation_actions:
        st.checkbox(a, value=False)

with col_right:
    # Sidebar: ASEAN Comparison
    st.markdown("### 🌐 Regional Comparison Matrix")
    
    # Load comparison row data
    comparison_map = ASEAN_COMPARISON.get(risk_category, {})
    countries = ["Vietnam", "India", "Singapore", "Indonesia", "EU"]
    criteria = [
        ("Has specific law?", "Has law"),
        ("Human-in-the-loop required?", "HITL?"),
        ("Penalty severity", "Penalty"),
        ("Effective date", "Effective Date")
    ]
    
    comp_rows = []
    for crit_display, crit_key in criteria:
        row = {"Criterion": crit_display}
        for country in countries:
            row[country] = comparison_map.get(country, {}).get(crit_key, "N/A")
        comp_rows.append(row)
    
    comp_df = pd.DataFrame(comp_rows)
    
    # Stylized Cell Painting
    def style_dataframe(val_df):
        def color_rules(val):
            if val == "✅":
                return 'background-color: rgba(16, 185, 129, 0.15); color: #10b981; text-align: center;'
            elif val == "❌":
                return 'background-color: rgba(239, 68, 68, 0.15); color: #f87171; text-align: center;'
            elif val == "High":
                return 'background-color: rgba(239, 68, 68, 0.1); color: #f87171;'
            elif val == "Medium":
                return 'background-color: rgba(249, 115, 22, 0.1); color: #fb923c;'
            elif val == "Low":
                return 'background-color: rgba(16, 185, 129, 0.1); color: #34d399;'
            return ''
        
        styler = val_df.style
        if hasattr(styler, "map"):
            return styler.map(color_rules)
        return styler.applymap(color_rules)

    st.dataframe(
        style_dataframe(comp_df),
        use_container_width=True,
        hide_index=True
    )

    # Regulatory Gap analysis warning cards
    st.markdown("### ⚠️ Regulatory Gap Analysis")
    gaps = [country for country, details in comparison_map.items() if details["Has law"] == "❌"]
    
    if gaps:
        st.warning(
            f"The following jurisdictions lack specific regulatory frameworks governing **{risk_category}**: "
            f"**{', '.join(gaps)}**. In these regions, compliance defaults to general guidelines, creating higher liability."
        )
    else:
        st.success("All analyzed jurisdictions have specific laws covering this threat category.")

# Report Generation and Downloads at the Bottom
st.markdown("---")
st.subheader("Report Export Hub")

html_report = reporter.generate_report(active_threat)
markdown_report = reporter.generate_markdown(active_threat)

col_rep1, col_rep2, col_rep3 = st.columns(3)

with col_rep1:
    if st.button("Generate Compliance Report HTML Preview", use_container_width=True):
        st.components.v1.html(html_report, height=600, scrolling=True)

with col_rep2:
    st.download_button(
        label="📥 Download HTML (Print to PDF)",
        data=html_report,
        file_name=f"compliance_report_{risk_category.replace(' ', '_').lower()}.html",
        mime="text/html",
        use_container_width=True
    )

with col_rep3:
    st.download_button(
        label="📥 Download Markdown Report",
        data=markdown_report,
        file_name=f"compliance_report_{risk_category.replace(' ', '_').lower()}.md",
        mime="text/markdown",
        use_container_width=True
    )
