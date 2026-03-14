# app/agent/nodes/reasoner.py
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage
from app.agent.state import AgentState
from app.agent.tools import AGENT_TOOLS
from app.agent.prompts.system import AGENT_SYSTEM_PROMPT
from app.core.config import settings
from app.core.llm_factory import get_reasoning_llm

# 1. Initialize Gemini
# We use temperature=0.2 so it remains factual and doesn't get overly creative with technical manuals.
llm = get_reasoning_llm()

# 2. Equip the LLM with our tools
llm_with_tools = llm.bind_tools(AGENT_TOOLS)

async def reasoner_node(state: AgentState):
    """
    The brain of the agent. It reads the chat history, looks at the tools,
    and decides whether to answer directly or call a tool.
    """
    messages = state["messages"]

    # If this is the very first message in the loop, inject the System Prompt to set the rules.
    if not any(isinstance(msg, SystemMessage) for msg in messages):
        messages = [SystemMessage(content=AGENT_SYSTEM_PROMPT)] + messages

    # 3. Call Gemini
    response = await llm_with_tools.ainvoke(messages)

    # 4. Return the response to be appended to the state's message list
    return {"messages": [response]}