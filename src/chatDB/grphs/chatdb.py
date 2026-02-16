
from sqlalchemy.engine import Engine
from src.utils.logging_config import get_logger
from ..tools.toolkit import AgentToolKit

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage

from typing import TypedDict, Annotated, Sequence, Literal
from langgraph.graph import add_messages, END, START, StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.graph.state import CompiledStateGraph


logger = get_logger(module_name="chat", DIR="queryAgent")



def create_chat_agent(llm : BaseChatModel, engine : Engine) -> CompiledStateGraph:
    
    toolkit = AgentToolKit(engine=engine)
    tools = toolkit.get_tools()
    logger.info(f"Hay {len(tools)} tools en el toolkit\n")

    llm_with_tools = llm.bind_tools(tools)

    class State(TypedDict):
        messages : Annotated[Sequence[BaseMessage], add_messages]
    
    tool_node = ToolNode(messages_key="messages", tools=tools)
    
    def ReAct_node(state : State) -> State:
        logger.info("---"*4 + " ReAct_node \n")
        messages = state["messages"]
        ai_message = llm_with_tools.invoke(messages)
        logger.info(f"\n {ai_message.pretty_repr()} \n\n")
        return {"messages":ai_message}
    
    def tool_node_wrapper(state : State) -> State:
        logger.info("---"*4 + " tool_node_wrapper\n")
        # tool_response será un dict como {"messages": [ToolMessage, ToolMessage, ...]}
        tool_responses = tool_node.invoke(state)
        for tool_response in tool_responses["messages"]:
            logger.info(f"{tool_response.pretty_repr()}\n")
        logger.info("\n")
        return tool_responses
    
    def should_end(state : State) -> Literal["tool_node_wrapper",END]: # type: ignore
        logger.info("---"*4 + " tool_node_wrapper")
        last_message = state["messages"][-1]
        if last_message.tool_calls:
            logger.info(f"tool_node_wrapper")
            return "tool_node_wrapper"
        logger.info("END")
        return END
    

    builder = StateGraph(State)

    builder.add_node("ReAct_node", ReAct_node)
    builder.add_node("tool_node_wrapper", tool_node_wrapper)

    builder.add_edge(START, "ReAct_node")
    builder.add_conditional_edges("ReAct_node", should_end)
    builder.add_edge("tool_node_wrapper", "ReAct_node")

    graph = builder.compile()

    return graph



if __name__=="__main__":
    from src.utils.settings import GOOGLE_API_KEY
    from langchain_core.messages import SystemMessage, HumanMessage
    from ..prompts.chatPrompts import SYSTEM_PROMPT_1
    from langchain_google_genai import ChatGoogleGenerativeAI
    from sqlalchemy import create_engine
    
    model = "gemini-2.0-flash"
    llm = ChatGoogleGenerativeAI(model=model, temperature=0.5, api_key=GOOGLE_API_KEY)

    conn_string = "postgresql+psycopg2://postgres:postgres@localhost:5434/northwind"
    engine = create_engine(conn_string)

    chat = create_chat_agent(llm=llm, engine=engine)

    messages = [SystemMessage(content=SYSTEM_PROMPT_1)]
    while True:
        print("========================= Human Message =============================\n")
        human_message = input()
        if human_message=="exit":
            break
        human_message = HumanMessage(content=human_message)
        messages.append(human_message)
        response = chat.invoke({"messages":messages})
        messages = response["messages"]
    print("\n Fin del chat")



