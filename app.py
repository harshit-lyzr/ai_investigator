import streamlit as st
from pathlib import Path
import logging
import pandas as pd
import asyncio
from typing import Dict, List
from src.processors.agentapi_processor import AgentAPIProcessor
from src.scrapers.web_loader import WebLoader
from src.scrapers.website_crawler import WebsiteCrawler
from src.config import (
    INPUT_DIR,
    RAW_DIR,
    LOGS_DIR,
    LOG_FORMAT,
    SECTIONS_DIR,
    REPORTS_DIR
)
from rich.progress import Progress, SpinnerColumn, TextColumn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler(Path(LOGS_DIR) / "processing_log.json"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

st.set_page_config(
    page_title="AI Investigator",
    layout="wide",  # Set the layout to wide for better use of space
    initial_sidebar_state="expanded"
)

async def process_case_study(web_loader: WebLoader, claude_processor: AgentAPIProcessor, url: str, index: int, progress=None):
    with st.spinner(f"Processing Case Study #{index + 1}"):
        st.markdown(f"URL: {url}")

        try:
            if progress:
                progress.update(progress.task_ids[0], description="📥 Extracting content...")
            content = await web_loader.extract_case_study(url)

            if not content:
                st.markdown("❌ Failed to extract content")
                return
            if progress:
                progress.update(progress.task_ids[0], description="💾 Saving raw content...")
            await web_loader.save_raw_content(index, content)


            if progress:
                progress.update(progress.task_ids[0], description="🔍 Analyzing enterprise AI relevance...")
            analysis = await claude_processor.analyze_enterprise_relevance(content['content'])

            if analysis.get('is_enterprise_ai'):
                st.write("## ✅ Qualified as Enterprise AI Case Study")
                data = {
                    "Attribute": ["Company", "Industry", "Technologies", "Confidence"],
                    "Value": [
                        analysis.get('company_details', {}).get('name', 'Unknown'),
                        analysis.get('company_details', {}).get('industry', 'Unknown'),
                        ', '.join(analysis.get('ai_implementation', {}).get('technologies', [])),
                        f"{analysis.get('confidence_score', 0.0):.2f}"
                    ]
                }

                # Create a DataFrame
                df = pd.DataFrame(data)

                # Display the table in Streamlit
                st.table(df)

                if progress:
                    progress.update(progress.task_ids[0], description="📝 Generating executive report...")
                executive_report = await claude_processor.generate_executive_report(
                    content['content'],
                    analysis
                )

                if executive_report:
                    st.write("💾 Saving reports...")
                    if await claude_processor.save_reports(index, content, analysis, executive_report):
                        st.success("Reports saved")
                    else:
                        st.error("❌ Failed to save some reports")
                else:
                    st.error("❌ Failed to generate executive report")
            else:
                st.error("\n⚠️ Not an Enterprise AI Case Study")
                st.error(f"Reason: {analysis.get('disqualification_reason')}")

            await asyncio.sleep(2)

        except Exception as e:
            logger.error(f"Error processing case study #{index + 1}: {str(e)}")
            st.warning(f"❌ Error: {str(e)}")

async def process_website(website_url: str, web_loader: WebLoader, claude_processor: AgentAPIProcessor, website_crawler: WebsiteCrawler):
    try:
        with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}")
        ) as progress:
            task = progress.add_task("🔍 Crawling website...", total=None)
            case_studies = await website_crawler.find_case_study_links(website_url, claude_processor)
            if not case_studies:
                st.warning("❌ No case studies found on website")
                return
            st.markdown(f"\n📊 Found {len(case_studies)} potential case studies:")
            data = {
                "Index": list(range(1, len(case_studies) + 1)),
                "Title": [case['title'] for case in case_studies],
                "URL": [case['url'] for case in case_studies]
            }
            df = pd.DataFrame(data)

            # Display the table in Streamlit
            st.write("## Case Studies")
            st.table(df)
            with st.spinner("\n🔄 Starting analysis of case studies..."):
                for index, case in enumerate(case_studies):
                    await process_case_study(web_loader, claude_processor, case['url'], index, progress)
    except Exception as e:
        logger.error(f"Error processing website {website_url}: {str(e)}")
        st.warning(f"❌ Error: {str(e)}")

async def main():
    """Main entry point for the case study analyzer"""
    try:
        # Initialize components
        web_loader = WebLoader()
        website_crawler = WebsiteCrawler()
        claude_processor = AgentAPIProcessor()

        website_url = st.text_input("Enter company website URL: ").strip()
        if st.button("Analysis"):
            await process_website(website_url, web_loader, claude_processor, website_crawler)
        else:
            st.warning("❌ Invalid mode selected")
            return
        st.markdown("\n✅ Analysis complete!")
    except KeyboardInterrupt:
        st.warning("\n\n⚠️ Process interrupted by user")
    except Exception as e:
        logger.error(f"An error occurred in main: {str(e)}")
        st.warning(f"❌ Error: {str(e)}")

# Ensure this is properly aligned
if __name__ == "__main__":
    asyncio.run(main())
