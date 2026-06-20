"""
frontend/app.py
Thin Streamlit launcher that inlines the full HTML/CSS/JS SPA.

This approach avoids Streamlit Cloud static-file serving issues by reading
all static files at startup and injecting them directly into a single
st.components.v1.html() call — no separate file server required.
"""

import os
import re
import json
import streamlit as st
import streamlit.components.v1 as components

# ---------------------------------------------------------------------------
# Page Config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="AIS-Sentinel",
    layout="wide",
    initial_sidebar_state="collapsed",
    page_icon="🛡️",
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

HERE = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.join(HERE, "static")
PAGES  = os.path.join(STATIC, "pages")


def read(path: str, default: str = "") -> str:
    """Safely read a text file, returning default on any error."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        st.warning(f"[app.py] Could not read {path}: {e}")
        return default


# ---------------------------------------------------------------------------
# Load static assets
# ---------------------------------------------------------------------------

html_shell = read(os.path.join(STATIC, "index.html"))
css        = read(os.path.join(STATIC, "style.css"))
js         = read(os.path.join(STATIC, "app.js"))

page_fragments = {
    "intelstream":  read(os.path.join(PAGES, "intelstream.html")),
    "safetybench":  read(os.path.join(PAGES, "safetybench.html")),
    "agentguard":   read(os.path.join(PAGES, "agentguard.html")),
    "policybridge": read(os.path.join(PAGES, "policybridge.html")),
}

# ---------------------------------------------------------------------------
# Inline assets into the HTML shell
# ---------------------------------------------------------------------------

# 1. Replace <link rel="stylesheet" href="style.css" /> with an inline <style>
css_tag = f"<style>\n{css}\n</style>"
html_shell = re.sub(
    r'<link[^>]+href=["\']style\.css["\'][^>]*/?>',
    css_tag,
    html_shell,
    flags=re.IGNORECASE,
)

# 2. Replace <script src="app.js"></script> with an inline <script>
#    Inject page fragments via window.__preloadedFragments BEFORE app.js runs.
#    app.js reads this global to initialise its pageCache — no fetch() needed,
#    and no const-redeclaration SyntaxError.
fragment_json = json.dumps(page_fragments)

inlined_js = f"""
<script>
// ── Pre-loaded page fragments (injected by app.py) ──────────────────────────
window.__preloadedFragments = {fragment_json};

// ── Application Logic ───────────────────────────────────────────────────────
{js}
</script>
"""

html_shell = re.sub(
    r'<script[^>]+src=["\']app\.js["\'][^>]*></script>',
    lambda m: inlined_js,
    html_shell,
    flags=re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Hide Streamlit chrome via CSS injection
# ---------------------------------------------------------------------------

st.markdown(
    """
    <style>
    /* Hide Streamlit's default header, footer and sidebar toggle */
    header[data-testid="stHeader"]      { display: none !important; }
    footer                              { display: none !important; }
    section[data-testid="stSidebar"]    { display: none !important; }
    .stDeployButton                     { display: none !important; }
    /* Remove default padding around the component iframe area */
    .block-container { padding: 0 !important; max-width: 100% !important; }
    [data-testid="stAppViewContainer"] > .main { padding: 0 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Render the SPA
# ---------------------------------------------------------------------------

components.html(
    html_shell,
    height=900,
    scrolling=True,
)
