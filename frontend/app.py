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

# Try importing tornado; make it optional to support environments where it is missing
HAS_TORNADO = False
try:
    import tornado.web
    HAS_TORNADO = True
except ImportError:
    pass

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

# Determine the API root endpoint for the frontend
api_root_env = os.environ.get("AIS_API_ROOT")
if api_root_env:
    api_root = api_root_env
elif not HAS_TORNADO:
    # Fallback to direct local FastAPI server URL if Tornado is not available
    api_root = "http://localhost:8000"
else:
    api_root = "/api"

inlined_js = f"""
<script>
// ── Pre-loaded page fragments (injected by app.py) ──────────────────────────
window.__preloadedFragments = {fragment_json};
window.__apiRoot = "{api_root}";

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

# ---------------------------------------------------------------------------
if HAS_TORNADO:
    TornadoRequestHandler = tornado.web.RequestHandler
else:
    class TornadoRequestHandler:
        pass

class TornadoAPIHandler(TornadoRequestHandler):
    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "Content-Type, Access-Control-Allow-Headers, Authorization, X-Requested-With")
        self.set_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')

    def options(self, *args, **kwargs):
        self.set_status(204)
        self.finish()

    def get(self, endpoint):
        try:
            if endpoint.startswith("intelstream/articles"):
                limit = int(self.get_argument("limit", 50))
                from core.database import get_articles
                articles = get_articles(limit=limit)
                self.write({"articles": articles, "count": len(articles)})
            elif endpoint.startswith("intelstream/brief"):
                region = self.get_argument("region", "Asia")
                days = int(self.get_argument("days", 7))
                from modules.intelstream.brief_generator import BriefGenerator
                gen = BriefGenerator()
                html = gen.generate_brief(days=days, region=region)
                self.write({"html": html})
            elif endpoint.startswith("safetybench/leaderboard"):
                from modules.safetybench.leaderboard import LeaderboardGenerator
                gen = LeaderboardGenerator()
                df = gen.generate_table()
                self.write({"leaderboard": df.to_dict(orient="records")})
            elif endpoint.startswith("safetybench/summary"):
                model_name = self.get_argument("model_name", None)
                from modules.safetybench.test_runner import BenchmarkRunner
                runner = BenchmarkRunner(model_name=model_name or "unknown", model_path="dummy")
                summary = runner.get_summary(model_name=model_name)
                self.write(summary)
            elif endpoint.startswith("agentguard/logs"):
                detected_only = self.get_argument("detected_only", "false").lower() == "true"
                from core.database import get_agent_logs
                logs = get_agent_logs(detected_only=detected_only)
                self.write({"logs": logs, "count": len(logs)})
            else:
                self.set_status(404)
                self.write({"detail": "Endpoint not found"})
        except Exception as e:
            self.set_status(500)
            self.write({"detail": str(e)})

    def post(self, endpoint):
        try:
            body = json.loads(self.request.body) if self.request.body else {}
            if endpoint.startswith("agentguard/design"):
                from core.llm_client import GeminiClient
                from modules.agentguard.agent import CreativeAgent
                from core.database import insert_agent_log

                client = GeminiClient()
                agent = CreativeAgent(model_client=client)

                attack_type = body.get("attack_type")
                covert_task = agent.get_attack_scenario(attack_type) if attack_type else None
                result = agent.design_slide(task=body.get("task", ""), covert_task=covert_task)

                try:
                    scan_score = max((s.get("suspicion_score", 0) for s in result.get("steps", [])), default=0)
                    insert_agent_log({
                        "task_description": body.get("task", ""),
                        "attack_type": attack_type or "none",
                        "slide_json": result.get("slide_json", "{}"),
                        "monitor_suspicion_score": scan_score,
                        "detected": result.get("covert_injected", False),
                    })
                except Exception as log_err:
                    pass

                self.write(result)
            elif endpoint.startswith("agentguard/scan"):
                from modules.agentguard.monitor import SlideMonitor
                use_llm = body.get("use_llm", True)
                llm_client = None
                if use_llm:
                    try:
                        from core.llm_client import GeminiClient
                        llm_client = GeminiClient()
                    except:
                        pass
                monitor = SlideMonitor(llm_client=llm_client)
                slide_json = body.get("slide_json", {})
                result = monitor.scan(slide_json, use_llm=use_llm)
                result["pareto_data"] = monitor.generate_pareto_data(slide_json)
                result["explanation"] = monitor.explain_flags(result.get("flagged_elements", []))
                self.write(result)
            elif endpoint.startswith("policybridge/map"):
                from modules.policybridge.mapper import RegulatoryMapper
                mapper = RegulatoryMapper()
                laws = mapper.map_threat(body.get("risk_category"), jurisdiction=body.get("jurisdiction"))
                self.write({"laws": laws, "count": len(laws)})
            elif endpoint.startswith("policybridge/compare"):
                from modules.policybridge.mapper import RegulatoryMapper
                mapper = RegulatoryMapper()
                df = mapper.compare_jurisdictions(body.get("risk_category"))
                self.write({"comparison": df.to_dict(orient="records")})
            elif endpoint.startswith("policybridge/report/html"):
                from modules.policybridge.reporter import ComplianceReporter
                reporter = ComplianceReporter()
                html = reporter.generate_report(body)
                self.write({"html": html})
            elif endpoint.startswith("policybridge/report/markdown"):
                from modules.policybridge.reporter import ComplianceReporter
                reporter = ComplianceReporter()
                markdown = reporter.generate_markdown(body)
                self.write({"markdown": markdown})
            else:
                self.set_status(404)
                self.write({"detail": "Endpoint not found"})
        except Exception as e:
            self.set_status(500)
            self.write({"detail": str(e)})

def register_tornado_api():
    if not HAS_TORNADO:
        st.warning("Tornado API registration skipped: Tornado module is not available. Please run the backend API separately (e.g. uvicorn api.main:app) or use standard mock fallback mode.")
        return
    try:
        import gc
        from streamlit.web.server.server import Server
        server = None
        for obj in gc.get_objects():
            if isinstance(obj, Server):
                server = obj
                break
        if server and not hasattr(server, "_api_handler_registered"):
            import tornado.web
            server._tornado_app.add_handlers(r".*", [
                (r"/api/(.*)", TornadoAPIHandler)
            ])
            server._api_handler_registered = True
    except Exception as e:
        st.warning(f"Tornado API registration warning: {e}")

# Register handler
register_tornado_api()

# Render the SPA using direct components.html call to avoid st-level metrics/telemetry wrapper TypeErrors
components.html(
    html_shell,
    height=900,
    scrolling=True,
)
