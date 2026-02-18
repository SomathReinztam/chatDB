from sqlalchemy.engine import Engine
from ..prompts.analystprompts import SQL_AGENT_SYSTEM_PROMPT_3, SHOULD_END_PROMPT_1, SUMMARY_PROMPT_1
import time
from src.utils.logging_config import get_logger
from groq import GroqError

from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI

from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.messages import RemoveMessage

from langgraph.types import RetryPolicy
from langgraph.graph.state import CompiledStateGraph
from typing import TypedDict, Literal, Annotated, Sequence
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
#from langchain_core.rate_limiters import InMemoryRateLimiter

from src.utils import settings

from ..tools.toolkit import PostgresToolKit

# rate_limiter = InMemoryRateLimiter(
#     requests_per_second=0.1,  # <-- Super slow! We can only make a request once every 10 seconds!!
#     check_every_n_seconds=0.1,  # Wake up every 100 ms to check whether allowed to make a request,
#     max_bucket_size=10,  # Controls the maximum burst size.
# )


logger = get_logger(module_name="deep_query", DIR="analyst")
logger_ReAct = get_logger(module_name="thinking_react", DIR="analyst")


#system_prompt = SQL_AGENT_SYSTEM_PROMPT_1.format(dialect="PostgreSQL", top_k=10)
system_prompt = SQL_AGENT_SYSTEM_PROMPT_3
parser = JsonOutputParser()


SERVER_AI_URL = settings.SERVER_AI_URL
GOOGLE_API_KEY = settings.GOOGLE_API_KEY
GROQ_API_KEY = settings.GROQ_API_KEY

# ollama_base_url = f"http://{SERVER_AI_URL}:{settings.OLLAMA_PORT}"
# model_1 = "gpt-oss:20b"
# llm = ChatOllama(model=model_1, temperature=0.35, base_url=ollama_base_url)

model = "openai/gpt-oss-120b"
llm = ChatGroq(model=model, temperature=0.1, api_key=GROQ_API_KEY)

model_2 = "gemini-2.0-flash"
#llm_analyst = ChatGoogleGenerativeAI(model=model_2, temperature=0.7, google_api_key=GOOGLE_API_KEY, rate_limiter=rate_limiter, max_retries=4, timeout=60)
llm_analyst = ChatGoogleGenerativeAI(model=model_2, temperature=0.7, google_api_key=GOOGLE_API_KEY)


# engine = create_engine(f"postgresql+psycopg2://{db_user}:{db_pass}@{db_host}/{db_name}")
def create_analyst_agent(engine : Engine) -> CompiledStateGraph:
    toolkit = PostgresToolKit(engine=engine)
    tools = toolkit.get_tools()

    # llm querier
    llm_with_tools = llm.bind_tools(tools)

    class State(TypedDict):
        # Estado inicial
        messages : Annotated[Sequence[BaseMessage], add_messages]

        messages_react : Annotated[Sequence[BaseMessage], add_messages]
        response_query : str | None
        should_end : dict
        analysis : str
        final_analysis : str

        input_tokens : int
        output_tokens : int
        api_calls : int


    tool_node = ToolNode(tools, messages_key="messages_react")



    def initial_deep_query_node(state : State) -> State:
        logger.info("---"*4 + " initial_deep_query_node")
        initial_message = state["messages"]
        human_message = state["messages"][-1]
        logger.debug(f"{human_message.pretty_repr()}")
        response = llm_analyst.invoke(initial_message)
        pretty_msg = response.pretty_repr()
        logger.debug(f"\n{pretty_msg}")
        print(f"\n\n {pretty_msg}" + "\n\n"*2)

        input_tokens = response.usage_metadata['input_tokens']
        output_tokens = response.usage_metadata['output_tokens']
        api_calls = 1

        logger.info(f"input_tokens: {input_tokens}--output_tokens: {output_tokens}--api_calls: {api_calls}")

        return {"messages":response, "input_tokens":input_tokens, "output_tokens":output_tokens, "api_calls":api_calls}


    def set_ReAct_messages_node(state : State) -> State:
        query_ai_message = state["messages"][-1]
        messages_react = [SystemMessage(content=system_prompt), HumanMessage(content=query_ai_message.content)]
        logger_ReAct.info("---"*4 + " set_ReAct_messages_node")
        logger_ReAct.info(f"len messages_react: {len(messages_react)}")
        human_msg = messages_react[-1]
        logger_ReAct.debug(f"\n{human_msg.pretty_repr()}")
        print(human_msg.pretty_repr())
        logger.info("---"*4 + " set_ReAct_messages_node")
        print("\n\n")
        return {"messages_react":messages_react}
        


    def ReAct_node(state : State) -> State:
        logger_ReAct.info("---"*4 + " ReAct_node")
        logger.info("---"*4 + " ReAct_node")
        messages_react = state['messages_react']
        
        input_tokens = state["input_tokens"]
        output_tokens = state["output_tokens"]
        api_calls = state["api_calls"]

        response = llm_with_tools.invoke(messages_react)
        response_query = response.content
        ai_msg = response.pretty_repr()
        print("\n\n")
        logger_ReAct.debug(f"\n{ai_msg}")
        print(f"{ai_msg}\n\n")
        
        input_tokens += response.usage_metadata['input_tokens']
        output_tokens += response.usage_metadata['output_tokens']
        api_calls += 1

        logger_ReAct.info(f"input_tokens: {input_tokens}--output_tokens: {output_tokens}--api_calls: {api_calls}")

        return {"messages_react":response, "response_query":response_query, "input_tokens":input_tokens, "output_tokens":output_tokens, "api_calls":api_calls}




    def should_continue_with_sql(state : State) -> Literal["tool_node_wrapper", "clear_ReAct_messages_node"]: # type: ignore
        logger_ReAct.info("---"*4 + " should_continue_with_sql")
        logger.info("---"*4 + " should_continue_with_sql")
        print("\n\n")
        last_message = state['messages_react'][-1]
        if last_message.tool_calls:
            logger_ReAct.info("tool_node_wrapper")
            return "tool_node_wrapper"
        logger_ReAct.info("clear_ReAct_messages_node")
        logger_ReAct.info(f"\n\n {'=='*40} \n {'=='*40} \n {'=='*40}\n")
        return "clear_ReAct_messages_node"



    def tool_node_wrapper(state: State) -> State:
        logger_ReAct.info("---"*4 + " tool_node_wrapper")
        logger.info("---"*4 + " tool_node_wrapper")
        print("\n\n")
        # tool_response será un dict como {"messages_react": [ToolMessage, ToolMessage, ...]}
        tool_response = tool_node.invoke(state)
        tool_messages = tool_response["messages_react"]
        for message in tool_messages:
            tool_msg = message.pretty_repr()
            logger_ReAct.debug(f"\n{tool_msg}")
            message.pretty_print()
            print("\n")
        print("\n\n"*3)
        return {"messages_react":tool_messages}




    def clear_ReAct_messages_node(state : State) -> State:
        logger.info("---"*4 + " clear_ReAct_messages_node")
        messages = state["messages_react"]
        response_query = state["response_query"]
        response_query_human_message = HumanMessage(content=response_query)
        # Crear una lista de RemoveMessage para eliminar todos los mensajes actuales
        return {"messages_react": [RemoveMessage(id=m.id) for m in messages], "messages":response_query_human_message}



    def deep_query_node(state : State) -> State:
        messages = state["messages"]
        logger.info("---"*4 + " deep_query_node")
        print("\n\n")
        human_msg = messages[-1].pretty_repr()
        logger.debug(f"\n{human_msg}")
        input_tokens = state["input_tokens"]
        output_tokens = state["output_tokens"]
        api_calls = state["api_calls"]

        #time.sleep(4)
        response = llm_analyst.invoke(messages)
        ai_msg = response.pretty_repr()
        logger.debug(f"\n{ai_msg}")
        lista = state["messages"] + [response]
        lista = lista[2:]
        for message in lista:
            message.pretty_print()
            print("\n")
        print("\n"*5)

        # Creo que estoy contando menos api calls de las que debería contar
        if (response.usage_metadata['input_tokens'] is None) or (response.usage_metadata['output_tokens']) is None:
            input_tokens += 0
            output_tokens += 0
            api_calls += 1
        else:
            input_tokens += response.usage_metadata['input_tokens']
            output_tokens += response.usage_metadata['output_tokens']
            api_calls += 1

        logger.info(f"input_tokens: {input_tokens}--output_tokens: {output_tokens}--api_calls: {api_calls}")

        return {"messages":response, "input_tokens":input_tokens, "output_tokens":output_tokens, "api_calls":api_calls}

    def should_end_node(state : State) -> State:
        logger.info("---"*4 + " should_end_node")
        tex = state["messages"][-1].content

        input_tokens = state["input_tokens"]
        output_tokens = state["output_tokens"]
        api_calls = state["api_calls"]

        # TODO: Hay veces que el llm analista responde vacío, para ser que esto es consecuencia de que el llm de queries también responde vacío. Hay que pensar por que pasa esto y como evitarlo
        if (len(tex) <= 5) or (tex is None):
            logger.error(f"\n {tex} \n")
            json = {'analysis':False, 'query': False, 'other':True}
            return {"should_end":json, "input_tokens":input_tokens, "output_tokens":output_tokens, "api_calls":api_calls}


        prompt = SHOULD_END_PROMPT_1.format(tex=tex)
        response = llm.invoke(prompt)
        json = parser.parse(response.content)
        logger.debug(f"\n{json}\n\n")
        print(json)
        print("\n"*5)

        input_tokens += response.usage_metadata['input_tokens']
        output_tokens += response.usage_metadata['output_tokens']
        api_calls += 1

        logger.info(f"input_tokens: {input_tokens}--output_tokens: {output_tokens}--api_calls: {api_calls}")

        
        return {"should_end":json, "input_tokens":input_tokens, "output_tokens":output_tokens, "api_calls":api_calls}



    def should_end(state : State) -> Literal["set_ReAct_messages_node", "final_analysis_node"]: # type: ignore
        logger.info("---"*4 + " should_end")
        json = state["should_end"]
        if (json['analysis']):
            logger.info("---"*4 + " charts_node \n\n\n\n\n")
            return "final_analysis_node"
        elif (json["query"]):
            logger.info("---"*4 + " set_ReAct_messages_node \n\n\n")
            return "set_ReAct_messages_node"
        else:
            logger.error("Mensaje del analista no es una consulta o un informe \n\n\n")
            return "final_analysis_node"
            # Sin miedo
            #raise ValueError("ERROR: Mensaje del analista no es una consulta o un informe")
    

    def final_analysis_node(state : State) -> State:
        logger.info("\n"*10 + "---"*4 + " final_analysis_node")

        messages = state["messages"]
        input_tokens = state["input_tokens"]
        output_tokens = state["output_tokens"]
        api_calls = state["api_calls"]

        analysis = ""
        N = len(messages) 
        for i in range(2, N):
            if i % 2 == 0:
                analysis += f"--- \n\n Mensaje del analista: \n\n\n\n {messages[i].content} \n\n"
            else:
                analysis += f"--- \n\n Mensaje del asistente del analista: \n\n\n\n {messages[i].content} \n\n"
        logger.debug(f"\n analysis: {analysis}" + "\n"*5)
        
        prompt = SUMMARY_PROMPT_1.format(history=analysis)
        ai_response = llm_analyst.invoke(prompt)
        logger.debug(f"\n {ai_response.pretty_repr()} \n")


        input_tokens += ai_response.usage_metadata['input_tokens']
        output_tokens += ai_response.usage_metadata['output_tokens']
        api_calls += 1

        logger.info(f"input_tokens: {input_tokens}--output_tokens: {output_tokens}--api_calls: {api_calls}")
        return {'analysis':analysis, "final_analysis":ai_response.content, "input_tokens":input_tokens, "output_tokens":output_tokens, "api_calls":api_calls}

        



    builder = StateGraph(State)

    builder.add_node("initial_deep_query_node", initial_deep_query_node)
    builder.add_node("set_ReAct_messages_node", set_ReAct_messages_node)
    builder.add_node("ReAct_node", ReAct_node, retry_policy=RetryPolicy(max_attempts=3, initial_interval=1.0, backoff_factor=2.0, retry_on=GroqError))
    builder.add_node("tool_node_wrapper", tool_node_wrapper)
    builder.add_node("clear_ReAct_messages_node", clear_ReAct_messages_node)
    builder.add_node("deep_query_node", deep_query_node)
    builder.add_node("should_end_node", should_end_node, retry_policy=RetryPolicy(max_attempts=3, initial_interval=1.0, backoff_factor=2.0, retry_on=GroqError))
    builder.add_node("final_analysis_node", final_analysis_node)

    builder.add_edge(START, "initial_deep_query_node")
    builder.add_edge("initial_deep_query_node", "set_ReAct_messages_node")
    builder.add_edge("set_ReAct_messages_node", "ReAct_node")
    builder.add_conditional_edges("ReAct_node", should_continue_with_sql)
    builder.add_edge("tool_node_wrapper", "ReAct_node")
    builder.add_edge("clear_ReAct_messages_node", "deep_query_node")
    builder.add_edge("deep_query_node", "should_end_node")
    builder.add_conditional_edges("should_end_node", should_end)

    graph = builder.compile()

    return graph


if __name__=="__main__":
    pass