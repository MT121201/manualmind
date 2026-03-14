# app/agent/tools/web_tool.py
from langchain_core.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun
from app.core.logger import get_logger

logger = get_logger(__name__)
web_search = DuckDuckGoSearchRun()

@tool
def web_search_tool(query: str) -> str:
    """
    Use this tool to search the internet for current events, news, weather,
    or general knowledge that is NOT found in the company's internal manuals.
    """
    logger.info(f"🌐 Agent triggered Web Search for: '{query}'")
    try:
        return web_search.run(query)
    except Exception as e:
        logger.error(f"Web search failed: {e}")
        return "I encountered an error while trying to search the web."