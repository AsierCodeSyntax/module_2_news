import operator
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage

# Global state shared across the multi-agent workflow
class OverallState(TypedDict):
    # 'messages' stores the conversation history between agents.
    # Annotated with operator.add ensures new messages are appended, not overwritten.
    messages: Annotated[Sequence[BaseMessage], operator.add]
    
    # The name of the next agent that should act, determined by the Supervisor
    next_agent: str
    
    # Global list to keep track of any errors during the workflow
    errors: list[str]