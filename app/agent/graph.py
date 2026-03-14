# app/agent/graph.py
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition

from app.agent.state import AgentState
from app.agent.nodes.reasoner import reasoner_node
from app.agent.tools import AGENT_TOOLS
from app.core.logger import get_logger

logger = get_logger(__name__)

# 1. Initialize the Graph with our Memory State
workflow = StateGraph(AgentState)

# 2. Define the Nodes
# LangGraph's pre-built ToolNode handles the actual execution of our Python tool functions
tool_node = ToolNode(AGENT_TOOLS)

workflow.add_node("reasoner", reasoner_node)
workflow.add_node("tools", tool_node)

# 3. Define the Flow (Edges)
workflow.add_edge(START, "reasoner")

# 4. The Conditional Router (The Magic)
# If 'reasoner' outputs a tool call, route to 'tools'.
# If 'reasoner' outputs a normal text response, route to END.
workflow.add_conditional_edges(
    "reasoner",
    tools_condition,
)

# 5. The Feedback Loop
# After the tool executes and gets the data, ALWAYS send it back to the reasoner
# so Gemini can read the data and write a final answer for the user.
workflow.add_edge("tools", "reasoner")

# 6. Compile the Graph
manual_mind_agent = workflow.compile()
logger.info("🧠 ManualMind LangGraph Agent compiled successfully!")