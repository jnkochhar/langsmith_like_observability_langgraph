import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, END
from langgraph.graph import MessagesState
from langchain.messages import SystemMessage, ToolMessage
from typing_extensions import Literal
from langchain.tools import tool
import time
import uuid
from datetime import datetime

class RunCollector:
    def __init__(self):
        self.reset()

    def reset(self):
        self.run_id = str(uuid.uuid4())
        self.start_time = datetime.now()
        self.nodes = []
        self.total_tokens = {}
        self.total_latency = 0
        self.errors = []

    def start_node(self, name, input_data):
        return {
            "node": name,
            "start_time": time.time(),
            "input": input_data,
        }

    def end_node(self, node_trace, output_data, tokens=0, error=None):
        end_time = time.time()
        latency = round(end_time - node_trace["start_time"], 3)

        start_dttime = datetime.fromtimestamp(node_trace["start_time"])
        trace = {
            "node": node_trace["node"],
            "start": start_dttime.strftime("%d %b %Y, %I:%M:%S.") + f"{start_dttime.microsecond // 1000:03d} " + start_dttime.strftime("%p"),
            "latency": latency,
            "input": node_trace["input"],
            "output": output_data,
            "tokens": tokens,
            "error": error,
            "timestamp": datetime.now().isoformat(),
        }

        self.nodes.append(trace)
        self.total_latency += latency
        if tokens:
            for key, value in tokens.items():
                self.total_tokens[key] = (
                    self.total_tokens.get(key, 0) + value
                )

        if error:
            self.errors.append(error)

    def build(self):
        result = {
            "run_id": self.run_id,
            "start_time": self.start_time.strftime("%d %b %Y, %I:%M:%S.") + f"{self.start_time.microsecond // 1000:03d} " + self.start_time.strftime("%p"),
            "nodes": self.nodes,
            "total_tokens": self.total_tokens,
            "total_latency": self.total_latency,
            "errors": self.errors,
        }

        return result
    
def instrument(
    node_name,
    node_fn,
    collector,
    input_extractor=None,
    output_extractor=None,
    token_extractor=None
):

    def wrapper(state, *args, **kwargs):

        trace_ctx = collector.start_node(
            node_name,
            input_data=input_extractor(state) if input_extractor else None
        )

        try:
            result = node_fn(state, *args, **kwargs)

            tokens = token_extractor(result) if token_extractor else 0

            collector.end_node(
                trace_ctx,
                output_data=output_extractor(result) if output_extractor else None,
                tokens=tokens
            )

            return result

        except Exception as e:
            collector.end_node(
                trace_ctx,
                output_data=None,
                tokens=0,
                error=str(e)
            )
            raise

    return wrapper

load_dotenv()

groq_key = os.getenv("groq_api_key")
os.environ["GROQ_API_KEY"] = groq_key

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0
)


# Define tools
@tool
def multiply(a: int, b: int) -> int:
    """Multiply `a` and `b`.

    Args:
        a: First int
        b: Second int
    """
    return a * b


@tool
def add(a: int, b: int) -> int:
    """Adds `a` and `b`.

    Args:
        a: First int
        b: Second int
    """
    return a + b


@tool
def divide(a: int, b: int) -> float:
    """Divide `a` and `b`.

    Args:
        a: First int
        b: Second int
    """
    return a / b


# Augment the LLM with tools
tools = [add, multiply, divide]
tools_by_name = {tool.name: tool for tool in tools}
llm_with_tools = llm.bind_tools(tools)


# Nodes
def llm_call(state: MessagesState):
    """LLM decides whether to call a tool or not"""

    return {
        "messages": [
            llm_with_tools.invoke(
                [
                    SystemMessage(
                        content="You are a helpful assistant tasked with performing arithmetic on a set of inputs."
                    )
                ]
                + state["messages"]
            )
        ]
    }


def tool_node(state: dict):
    """Performs the tool call"""

    result = []
    for tool_call in state["messages"][-1].tool_calls:
        tool = tools_by_name[tool_call["name"]]
        observation = tool.invoke(tool_call["args"])
        result.append(ToolMessage(content=observation, tool_call_id=tool_call["id"]))
    return {"messages": result}


# Conditional edge function to route to the tool node or end based upon whether the LLM made a tool call
def should_continue(state: MessagesState) -> Literal["tool_node", END]:
    """Decide if we should continue the loop or stop based upon whether the LLM made a tool call"""

    messages = state["messages"]
    last_message = messages[-1]

    # If the LLM makes a tool call, then perform an action
    if last_message.tool_calls:
        return "tool_node"

    # Otherwise, we stop (reply to the user)
    return END


# Custom functions for Instrument
def llm_input(state):
    llm_node_input = ""
    for ni in state["messages"]:
        llm_node_input += ni.pretty_repr() + "\n\n"
    return llm_node_input

def llm_output(result):
    msg = result["messages"][-1]
    return msg.pretty_repr()

def llm_tokens(result):
    msg = result["messages"][-1]

    usage = getattr(msg, "usage_metadata", None)

    if not usage:
        return {}

    # Convert to plain dict if needed
    if hasattr(usage, "dict"):
        usage = usage.dict()

    # Ensure it's a standard dictionary
    usage = dict(usage)

    return usage

def tool_input(state):
    msg = state["messages"][-1]
    return msg.pretty_repr()

def tool_output(result):
    tool_node_output = ""
    for ni in result["messages"]:
        tool_node_output += ni.pretty_repr() + "\n\n"
    return tool_node_output


collector = RunCollector()

# Build workflow
agent_builder = StateGraph(MessagesState)

# Add nodes
agent_builder.add_node(
    "llm_call",
    instrument(
        "llm_call",
        llm_call,
        collector,
        input_extractor=llm_input,
        output_extractor=llm_output,
        token_extractor=llm_tokens
    )
)
agent_builder.add_node(
    "tool_node",
    instrument(
        "tool_node",
        tool_node,
        collector,
        input_extractor=tool_input,
        output_extractor=tool_output,
    )
)

# Add edges to connect nodes
agent_builder.add_edge(START, "llm_call")
agent_builder.add_conditional_edges(
    "llm_call",
    should_continue,
    ["tool_node", END]
)
agent_builder.add_edge("tool_node", "llm_call")

# Compile the agent
graph = agent_builder.compile()

