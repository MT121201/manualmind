# app/agent/state.py
from typing import Annotated, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """
    The State represents the memory of our Agent during a single conversation loop.
    """
    # It ensures that when a node returns a new message, it APPENDS to the list
    # instead of overwriting the previous messages.
    messages: Annotated[list[BaseMessage], add_messages]

    # current_user_id: str
    # access_level: str