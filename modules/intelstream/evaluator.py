import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from core.llm_client import GeminiClient
from core.database import get_db_connection, insert_article

logger = logging.getLogger(__name__)

# Schema dictionary to enforce structure on the Gemini API response
EVALUATION_SCHEMA = {
    "type": "object",
    "properties": {
        "threat_detected": {
            "type": "boolean",
            "description": "True if an AI-biosecurity threat is detected in the article."
        },
        "confidence_score": {
            "type": "number",
            "description": "Confidence score of the evaluation between 0.0 and 1.0."
        },
        "risk_category": {
            "type": "string",
            "enum": ["Dual-use hardware", "AI-EngBio integration", "Policy gap", "Data sovereignty risk", "None"],
            "description": "Category of threat identified."
        },
        "justification": {
            "type": "string",
            "description": "Brief justification for the evaluation, strictly maximum 200 characters."
        },
        "entities_mentioned": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Key entities, models, organizations, or bio-agents mentioned."
        },
        "severity": {
            "type": "string",
            "enum": ["Critical", "High", "Medium", "Low"],
            "description": "Severity of the threat if detected."
        },
        "translation": {
            "type": "string",
            "description": "English translation of the input text if it is not in English. If it is in English, set it to the original text."
        }
    },
    "required": [
        "threat_detected",
        "confidence_score",
        "risk_category",
        "justification",
        "entities_mentioned",
        "severity",
        "translation"
    ]
}

class ThreatEvaluator:
    """
    A class that evaluates news articles and reports for AI-biosecurity threats
    using structured outputs from Gemini Flash API and caches evaluation results in SQLite.
    """
    
    EVALUATION_PROMPT_TEMPLATE = (
        "You are an expert AI biosecurity analyst. Evaluate the following article title and text "
        "to classify and extract safety threat assessments. "
        "If the input text is not in English, translate it to English and populate the 'translation' field with the English translation. "
        "Otherwise, populate 'translation' with the original English text.\n\n"
        "Article Title: {title}\n"
        "Article Text:\n{text}\n\n"
        "Conform your response strictly to the output schema. Ensure justification is concise and "
        "does not exceed 200 characters."
    )

    def __init__(self) -> None:
        """Initializes the ThreatEvaluator with a GeminiClient instance."""
        self.client = GeminiClient()

    def evaluate(self, article_text: str, article_title: str = "") -> Dict[str, Any]:
        """Evaluates a single article for biosecurity threats, caches/updates the result in SQLite,
        and returns the structured JSON report.
        
        Args:
            article_text: The main text content of the article.
            article_title: The optional title of the article.
            
        Returns:
            A dictionary containing the structured threat evaluation.
        """
        prompt = self.EVALUATION_PROMPT_TEMPLATE.format(
            title=article_title or "Untitled",
            text=article_text
        )
        
        try:
            # Query Gemini using response schema
            result = self.client.generate_structured(prompt, schema=EVALUATION_SCHEMA, temperature=0.2)
        except Exception as exc:
            logger.exception("Failed to evaluate article with Gemini: %s", exc)
            # Safe fallback if Gemini call fails completely
            result = {
                "threat_detected": False,
                "confidence_score": 0.0,
                "risk_category": "None",
                "justification": f"Evaluation failed: {str(exc)[:100]}",
                "entities_mentioned": [],
                "severity": "Low"
            }

        # Cache or update in database
        try:
            # Check if there is an article with matching original_text or translated_text in SQLite
            article_id = None
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id FROM articles WHERE original_text = ? OR translated_text = ? LIMIT 1",
                    (article_text, article_text)
                )
                row = cursor.fetchone()
                if row:
                    article_id = row["id"]

            if article_id is not None:
                # Update threat assessment columns on existing article
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        UPDATE articles
                        SET threat_detected = ?, confidence_score = ?, risk_category = ?, justification = ?
                        WHERE id = ?
                        """,
                        (
                            1 if result.get("threat_detected") else 0,
                            result.get("confidence_score"),
                            result.get("risk_category"),
                            result.get("justification"),
                            article_id
                        )
                    )
                    conn.commit()
            else:
                # Insert a new record
                insert_article({
                    "title": article_title or "Evaluated Article",
                    "source_url": "",
                    "source_country": "",
                    "language": "en",
                    "original_text": article_text,
                    "translated_text": article_text,
                    "threat_detected": result.get("threat_detected"),
                    "confidence_score": result.get("confidence_score"),
                    "risk_category": result.get("risk_category"),
                    "justification": result.get("justification")
                })
        except Exception as exc:
            logger.error("Failed to cache evaluation result in SQLite: %s", exc)

        return result

    def batch_evaluate(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Evaluates a batch of articles and returns list of threat evaluations.
        
        Args:
            articles: List of articles, where each article is a dictionary.
            
        Returns:
            A list of threat evaluation dictionaries.
        """
        results = []
        for article in articles:
            title = article.get("title", "")
            # Try to get text, original_text, or summary
            text = article.get("text") or article.get("original_text") or article.get("summary") or ""
            assessment = self.evaluate(text, article_title=title)
            results.append(assessment)
        return results

    def get_threat_summary(self, days: int = 7) -> Dict[str, Any]:
        """Aggregates threat statistics by source country and risk category.
        
        Args:
            days: Number of trailing days to look back.
            
        Returns:
            A dictionary containing threat aggregation statistics.
        """
        cutoff_time = (datetime.now() - timedelta(days=days)).isoformat()
        
        by_country = {}
        by_category = {}
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Group by country
                cursor.execute(
                    """
                    SELECT source_country, COUNT(*) as cnt
                    FROM articles
                    WHERE threat_detected = 1 AND created_at >= ?
                    GROUP BY source_country
                    """,
                    (cutoff_time,)
                )
                for row in cursor.fetchall():
                    country = row["source_country"] or "Unknown"
                    by_country[country] = row["cnt"]
                
                # Group by risk category
                cursor.execute(
                    """
                    SELECT risk_category, COUNT(*) as cnt
                    FROM articles
                    WHERE threat_detected = 1 AND created_at >= ?
                    GROUP BY risk_category
                    """,
                    (cutoff_time,)
                )
                for row in cursor.fetchall():
                    category = row["risk_category"] or "None"
                    by_category[category] = row["cnt"]
        except Exception as exc:
            logger.error("Failed to aggregate threat summary from database: %s", exc)
            
        return {
            "by_country": by_country,
            "by_category": by_category,
            "total_threats": sum(by_category.values())
        }
