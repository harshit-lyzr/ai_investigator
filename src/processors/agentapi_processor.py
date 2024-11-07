from anthropic import Anthropic
from openai import OpenAI
import json
import logging
from typing import Dict, Optional, List
from pathlib import Path
from src.config import (
    OPENAI_API_KEY,
    SECTIONS_DIR,
    REPORTS_INDIVIDUAL_DIR,
    REPORTS_CROSS_CASE_DIR,
    REPORTS_EXECUTIVE_DIR
)
from lyzr_agent_api.models.chat import ChatRequest
from dotenv import load_dotenv
from lyzr_agent_api.client import AgentAPI
import os

load_dotenv()

client = AgentAPI(x_api_key=os.getenv("LYZR_API_KEY"))

logger = logging.getLogger(__name__)


class AgentAPIProcessor:
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)

    async def analyze_enterprise_relevance(self, content: str) -> Dict:
        """Determine if the case study is relevant for enterprise AI analysis"""

        try:
            print("AGent API: Analyze Enterprise Relevance")
            # Create message with Claude
            response = client.chat_with_agent(
                json_body=ChatRequest(
                    user_id=os.getenv("USER_ID"),
                    agent_id=os.getenv("AGENT_1"),
                    message=f"Content: {content}",
                    session_id="123"
                )
            )

            # Get response text
            response_text = response["response"]
            logger.debug(f"Raw Claude response: {response_text}")

            # Clean up the response text
            if '```json' in response_text:
                response_text = response_text.split('```json')[1].split('```')[0]
            elif '```' in response_text:
                response_text = response_text.split('```')[1]

            # Remove any leading/trailing whitespace and newlines
            response_text = response_text.strip()

            try:
                # Parse JSON
                analysis = json.loads(response_text)

                # Log successful analysis
                logger.info(f"Successfully analyzed content: {json.dumps(analysis, indent=2)}")

                # Validate required fields
                required_fields = ['is_enterprise_ai', 'confidence_score', 'company_details', 'qualification_criteria']
                if not all(field in analysis for field in required_fields):
                    logger.error(f"Missing required fields. Found: {list(analysis.keys())}")
                    raise ValueError("Missing required fields in response")

                return analysis

            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error: {str(e)}")
                logger.error(f"Response text: {response_text}")

                # Return default response for JSON parsing errors
                return {
                    "is_enterprise_ai": False,
                    "confidence_score": 0.0,
                    "company_details": {
                        "name": "Unknown",
                        "industry": "Unknown",
                        "size_category": "Unknown"
                    },
                    "ai_implementation": {
                        "technologies": [],
                        "scale": "Unknown",
                        "business_areas": []
                    },
                    "qualification_criteria": {
                        "established_company": False,
                        "business_focus": False,
                        "enterprise_scale": False,
                        "clear_outcomes": False
                    },
                    "disqualification_reason": "Failed to parse analysis results"
                }

        except Exception as e:
            logger.error(f"Analysis error: {str(e)}")
            return {
                "is_enterprise_ai": False,
                "confidence_score": 0.0,
                "company_details": {
                    "name": "Unknown",
                    "industry": "Unknown",
                    "size_category": "Unknown"
                },
                "ai_implementation": {
                    "technologies": [],
                    "scale": "Unknown",
                    "business_areas": []
                },
                "qualification_criteria": {
                    "established_company": False,
                    "business_focus": False,
                    "enterprise_scale": False,
                    "clear_outcomes": False
                },
                "disqualification_reason": f"Error analyzing content: {str(e)}"
            }

    async def generate_section_analysis(self, content: str, section: str) -> str:
        """Generate detailed analysis for a specific section"""

        try:
            print("AGent API: Generate Section Analysis")
            response = client.chat_with_agent(
                json_body=ChatRequest(
                    user_id=os.getenv("USER_ID"),
                    agent_id=os.getenv("AGENT_2"),
                    message=f"Section: {section} , Content: {content}",
                    session_id="123"
                )
            )
            return response["response"]
        except Exception as e:
            logger.error(f"Error generating {section} analysis: {str(e)}")
            return None

    async def save_section_analysis(self, case_id: int, section: str, content: str) -> bool:
        """Save section analysis to file"""
        try:
            case_dir = Path(SECTIONS_DIR) / f"case_{case_id}"
            case_dir.mkdir(exist_ok=True)

            with open(case_dir / f"{section}.md", "w", encoding="utf-8") as f:
                f.write(content)

            return True
        except Exception as e:
            logger.error(f"Error saving {section} analysis for case {case_id}: {str(e)}")
            return False

    async def generate_executive_report(self, content: str, analysis: Dict) -> str:
        """Generate executive report for a qualified case study"""

        try:
            print("AGent API: Generate Executive Report")
            response = client.chat_with_agent(
                json_body=ChatRequest(
                    user_id=os.getenv("USER_ID"),
                    agent_id=os.getenv("AGENT_3"),
                    message=f"Analysis: {analysis} , Content: {content}",
                    session_id="123"
                )
            )
            return response["response"]
        except Exception as e:
            logger.error(f"Error generating executive report: {str(e)}")
            return None

    async def save_reports(self, case_id: int, content: Dict, analysis: Dict, executive_report: str):
        """Save all reports for a qualified case study"""
        try:
            # Save individual case study report
            individual_report_path = Path(REPORTS_INDIVIDUAL_DIR) / f"case_{case_id}.md"
            with open(individual_report_path, "w", encoding="utf-8") as f:
                f.write(executive_report)

            # Update cross-case analysis
            cross_case_path = Path(REPORTS_CROSS_CASE_DIR) / "cross_case_analysis.json"
            cross_case_data = {}
            if cross_case_path.exists():
                with open(cross_case_path, "r") as f:
                    cross_case_data = json.load(f)

            # Add this case study to cross-case analysis
            cross_case_data[f"case_{case_id}"] = {
                "company": analysis["company_details"],
                "technologies": analysis["ai_implementation"]["technologies"],
                "success_factors": analysis["qualification_criteria"],
                "business_impact": analysis.get("business_impact", {})
            }

            with open(cross_case_path, "w") as f:
                json.dump(cross_case_data, f, indent=2)

            # Update executive dashboard
            dashboard_path = Path(REPORTS_EXECUTIVE_DIR) / "executive_dashboard.json"
            dashboard_data = {}
            if dashboard_path.exists():
                with open(dashboard_path, "r") as f:
                    dashboard_data = json.load(f)

            # Add summary to dashboard
            dashboard_data[f"case_{case_id}"] = {
                "company": analysis["company_details"]["name"],
                "industry": analysis["company_details"]["industry"],
                "confidence_score": analysis["confidence_score"],
                "implementation_scale": analysis["ai_implementation"]["scale"],
                "key_technologies": analysis["ai_implementation"]["technologies"]
            }

            with open(dashboard_path, "w") as f:
                json.dump(dashboard_data, f, indent=2)

            return True

        except Exception as e:
            logger.error(f"Error saving reports for case {case_id}: {str(e)}")
            return False

    async def analyze_links(self,url_data) -> str:
        """Analyze links to identify case studies"""
        try:
            print("AGent API: Analyze Links")
            response = client.chat_with_agent(
                json_body=ChatRequest(
                    user_id=os.getenv("USER_ID"),
                    agent_id=os.getenv("AGENT_4"),
                    message=f"urls: {url_data} ",
                    session_id="123"
                )
            )
            return response["response"]
        except Exception as e:
            logger.error(f"Error analyzing links: {str(e)}")
            return "[]"  # Return empty list on error
