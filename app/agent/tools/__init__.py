# app/agent/tools/__init__.py
from .web_tool import web_search_tool
from .rag_tool import internal_manuals_tool

AGENT_TOOLS = [internal_manuals_tool, web_search_tool]