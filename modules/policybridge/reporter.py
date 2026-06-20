import os
from typing import Dict, Any, List, Optional
from modules.policybridge.mapper import RegulatoryMapper

class ComplianceReporter:
    """
    Generates structured HTML and Markdown compliance reports from threat evaluation data,
    mapping detected threats to regional frameworks and recommended actions.
    """

    def __init__(self, policies_file: str = "config/policies.json") -> None:
        self.mapper = RegulatoryMapper(policies_file=policies_file)

    def _get_remediation_actions(self, risk_category: str) -> List[str]:
        """Provides 3-5 specific remediation actions based on the threat's risk category."""
        cat_lower = risk_category.lower()
        if any(w in cat_lower for w in ["bio", "gene", "pathogen", "crispr", "dual-use", "weapon", "biosecurity"]):
            return [
                "Isolate the system and block active endpoint access for unverified or external client IPs.",
                "Audit prompt inputs and logs to isolate dual-use biological sequence generation attempts.",
                "Implement boundary constraints and strict sequence filters on all biological design requests.",
                "Prepare and file a biosecurity alignment compliance report for digital safety authorities."
            ]
        elif any(w in cat_lower for w in ["privacy", "leak", "personal", "data", "dpdp", "pdpa"]):
            return [
                "Purge exposed data and personally identifiable information (PII) from active logs and database cache.",
                "Deploy client-side data scrubbing and PII masking libraries in front of the model prompt pipeline.",
                "Enforce encryption for downstream logs and storage of all interactive conversation histories.",
                "Notify the Data Protection Officer (DPO) and review local breach disclosure regulations."
            ]
        elif any(w in cat_lower for w in ["jailbreak", "sycophancy", "hallucination", "adversarial", "safety", "layout", "attack"]):
            return [
                "Integrate structural input/output guardrail classifiers (e.g. safety filters) to block adversarial prompts.",
                "Establish human-in-the-loop review mechanisms for safety-critical automatic design responses.",
                "Implement multilingual test suites to periodically test model alignment behavior across local languages."
            ]
        else:
            return [
                "Conduct an internal audit to analyze threat vectors and trigger conditions.",
                "Configure basic keyword-based filters on input prompts and output responses.",
                "Establish standard logging protocols to capture anomalous model state transitions."
            ]

    def _get_deadline(self, severity: str) -> Optional[str]:
        """Calculates remediation deadlines based on severity rating."""
        sev = severity.lower()
        if sev == "critical":
            return "Immediate: within 24 hours"
        elif sev == "high":
            return "Within 7 days of detection"
        elif sev == "medium":
            return "Within 30 days of detection"
        elif sev == "low":
            return "Within 90 days of detection"
        return None

    def generate_report(self, threat_data: Dict[str, Any]) -> str:
        """
        Generates a premium styled HTML compliance report.

        Args:
            threat_data: A dictionary containing threat information.

        Returns:
            The HTML report string.
        """
        title = threat_data.get("title") or threat_data.get("headline") or "Anomalous AI Activity Detected"
        risk_category = threat_data.get("risk_category", "Default")
        severity = threat_data.get("severity", "Medium")
        justification = threat_data.get("justification", "No justification provided.")
        
        # Get laws mapping
        laws = self.mapper.map_threat(risk_category)
        
        # Format severity classes
        severity_class = severity.lower()
        if severity_class not in ["critical", "high", "medium", "low"]:
            severity_class = "medium"

        # Format laws into premium cards
        laws_html_list = []
        if laws:
            for l in laws:
                card = f"""
        <div class="law-card">
            <div class="law-header">
                <span class="law-jurisdiction">{l.get('jurisdiction')}</span>
                <span>{l.get('law_name')}</span>
            </div>
            <div class="law-detail"><strong>Article/Section:</strong> {l.get('article')}</div>
            <div class="law-detail"><strong>Requirement:</strong> {l.get('requirement')}</div>
            <div class="law-detail"><strong>Effective Date:</strong> {l.get('effective_date')}</div>
            <div class="law-penalty"><strong>Penalty:</strong> {l.get('penalty')}</div>
        </div>"""
                laws_html_list.append(card)
        else:
            laws_html_list.append('<div class="text-content">No specific regional regulations found for this risk category. Check general compliance frameworks.</div>')
        
        laws_html = "\n".join(laws_html_list)

        # Format remediation actions
        actions = self._get_remediation_actions(risk_category)
        actions_html = "\n".join(f'            <li class="action-item">{a}</li>' for a in actions)

        # Deadline
        deadline = self._get_deadline(severity)
        deadline_html = ""
        if deadline:
            deadline_html = f"""
        <div class="deadline-box">
            <span>&#9888; Compliance Deadline: {deadline}</span>
        </div>"""

        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Compliance & Regulatory Report</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        body {{
            font-family: 'Outfit', sans-serif;
            background-color: #0b0c10;
            color: #c9d1d9;
            margin: 0;
            padding: 40px 20px;
            display: flex;
            justify-content: center;
        }}
        .report-card {{
            background-color: #12131c;
            border: 1px solid #222533;
            border-radius: 16px;
            padding: 32px;
            max-width: 800px;
            width: 100%;
            box-shadow: 0 12px 36px rgba(0, 0, 0, 0.5);
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #222533;
            padding-bottom: 20px;
            margin-bottom: 24px;
        }}
        .title {{
            font-size: 1.8rem;
            font-weight: 700;
            background: linear-gradient(135deg, #a78bfa 0%, #818cf8 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin: 0;
        }}
        .badge {{
            font-size: 0.85rem;
            font-weight: 700;
            padding: 6px 16px;
            border-radius: 9999px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        .badge-critical {{
            background: linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(249, 115, 22, 0.15) 100%);
            color: #f87171;
            border: 1px solid rgba(239, 68, 68, 0.4);
        }}
        .badge-high {{
            background: linear-gradient(135deg, rgba(249, 115, 22, 0.15) 0%, rgba(234, 179, 8, 0.15) 100%);
            color: #fb923c;
            border: 1px solid rgba(249, 115, 22, 0.4);
        }}
        .badge-medium {{
            background: linear-gradient(135deg, rgba(99, 102, 241, 0.15) 0%, rgba(168, 85, 247, 0.15) 100%);
            color: #818cf8;
            border: 1px solid rgba(99, 102, 241, 0.4);
        }}
        .badge-low {{
            background: linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(6, 182, 212, 0.15) 100%);
            color: #34d399;
            border: 1px solid rgba(16, 185, 129, 0.4);
        }}
        .section-title {{
            font-size: 1.2rem;
            font-weight: 600;
            color: #a5b4fc;
            margin-top: 28px;
            margin-bottom: 12px;
            border-bottom: 1px solid #1e202f;
            padding-bottom: 6px;
        }}
        .text-content {{
            font-size: 0.95rem;
            line-height: 1.6;
            color: #94a3b8;
            margin-bottom: 16px;
        }}
        .law-card {{
            background: #171926;
            border: 1px solid #25283d;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 16px;
        }}
        .law-header {{
            display: flex;
            justify-content: space-between;
            font-weight: 600;
            color: #e2e8f0;
            font-size: 0.95rem;
            margin-bottom: 8px;
        }}
        .law-jurisdiction {{
            color: #a78bfa;
        }}
        .law-detail {{
            font-size: 0.88rem;
            color: #94a3b8;
            margin-bottom: 4px;
        }}
        .law-penalty {{
            font-size: 0.88rem;
            color: #f87171;
            margin-top: 6px;
            font-weight: 500;
        }}
        .action-list {{
            margin: 0;
            padding-left: 20px;
        }}
        .action-item {{
            font-size: 0.95rem;
            color: #94a3b8;
            margin-bottom: 8px;
            line-height: 1.5;
        }}
        .deadline-box {{
            background: rgba(239, 68, 68, 0.05);
            border: 1px solid rgba(239, 68, 68, 0.2);
            border-radius: 8px;
            padding: 12px 16px;
            color: #f87171;
            font-weight: 600;
            font-size: 0.95rem;
            margin-top: 24px;
            display: flex;
            align-items: center;
        }}
        .footer {{
            margin-top: 40px;
            text-align: center;
            font-size: 0.8rem;
            color: #4b5563;
        }}
    </style>
</head>
<body>
    <div class="report-card">
        <div class="header">
            <h1 class="title">Compliance & Regulatory Report</h1>
            <span class="badge badge-{severity_class}">{severity}</span>
        </div>
        
        <div class="section-title">What Was Found</div>
        <div class="text-content"><strong>Risk Category:</strong> {risk_category}</div>
        <div class="text-content"><strong>Summary:</strong> {title}</div>
        
        <div class="section-title">Why It Matters</div>
        <div class="text-content">{justification}</div>
        
        <div class="section-title">Applicable Regulatory Frameworks</div>
        {laws_html}
        
        <div class="section-title">Recommended Remediation Actions</div>
        <ul class="action-list">
            {actions_html}
        </ul>
        
        {deadline_html}
        
        <div class="footer">
            Generated by AIS-Sentinel PolicyBridge Engine &copy; 2026
        </div>
    </div>
</body>
</html>"""
        return html_content

    def generate_markdown(self, threat_data: Dict[str, Any]) -> str:
        """
        Generates a clean Markdown compliance report.

        Args:
            threat_data: A dictionary containing threat information.

        Returns:
            The Markdown report string.
        """
        title = threat_data.get("title") or threat_data.get("headline") or "Anomalous AI Activity Detected"
        risk_category = threat_data.get("risk_category", "Default")
        severity = threat_data.get("severity", "Medium")
        justification = threat_data.get("justification", "No justification provided.")
        
        laws = self.mapper.map_threat(risk_category)
        
        laws_markdown_list = []
        if laws:
            for l in laws:
                item = (
                    f"### {l.get('jurisdiction')} — {l.get('law_name')}\n"
                    f"- **Article/Section**: {l.get('article')}\n"
                    f"- **Requirement**: {l.get('requirement')}\n"
                    f"- **Effective Date**: {l.get('effective_date')}\n"
                    f"- **Penalty**: *{l.get('penalty')}*"
                )
                laws_markdown_list.append(item)
        else:
            laws_markdown_list.append("No specific regional regulations found for this risk category.")

        laws_markdown = "\n\n".join(laws_markdown_list)

        actions = self._get_remediation_actions(risk_category)
        actions_markdown = "\n".join(f"- {a}" for a in actions)

        deadline = self._get_deadline(severity)
        deadline_markdown = f"⚠️ **Compliance Deadline**: {deadline}" if deadline else ""

        markdown_content = f"""# AIS-Sentinel Compliance & Policy Report

### Severity: {severity.upper()}

## What Was Found
- **Risk Category**: {risk_category}
- **Threat Summary**: {title}

## Why It Matters
{justification}

## Applicable Regulatory Frameworks
{laws_markdown}

## Recommended Remediation Actions
{actions_markdown}

{deadline_markdown}

---
*Generated by AIS-Sentinel PolicyBridge Engine (Global South AI Safety Framework)*"""
        return markdown_content

    def send_email_report(self, recipient: str, risk_category: str, content: str, fmt: str) -> tuple[bool, str]:
        """
        Sends the generated compliance report to the specified recipient.
        Uses SMTP environment variables if configured; otherwise, falls back to simulated mode.
        """
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        smtp_server = os.environ.get("SMTP_SERVER")
        smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        smtp_user = os.environ.get("SMTP_USERNAME")
        smtp_password = os.environ.get("SMTP_PASSWORD")
        sender_email = os.environ.get("SMTP_SENDER", "noreply@ais-sentinel.org")

        subject = f"AIS-Sentinel Regulatory & Compliance Report: {risk_category}"

        # If not fully configured, run simulated delivery
        if not (smtp_server and smtp_user and smtp_password):
            print(f"\n--- [SIMULATED EMAIL DELIVERY] ---")
            print(f"To: {recipient}")
            print(f"Subject: {subject}")
            print(f"Format: {fmt}")
            print(f"Content Length: {len(content)} chars")
            print(f"-----------------------------------\n")
            return True, "Simulated Dev Mode success"

        try:
            msg = MIMEMultipart()
            msg["From"] = sender_email
            msg["To"] = recipient
            msg["Subject"] = subject

            mime_type = "html" if fmt == "HTML" else "plain"
            msg.attach(MIMEText(content, mime_type))

            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.sendmail(sender_email, recipient, msg.as_string())
            
            return True, "Email sent successfully"
        except Exception as e:
            return False, str(e)
