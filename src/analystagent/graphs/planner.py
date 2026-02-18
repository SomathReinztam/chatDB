from ..prompts.plannerprompts import TABLE_SCHEMA_TEMPLATE_3, PLANER_PROMPT_2
from sqlalchemy.engine import Engine
from src.utils.db_utils import PostgresUtils
from src.utils.logging_config import get_logger

from langchain_google_genai import ChatGoogleGenerativeAI

from typing import TypedDict
from langgraph.graph import StateGraph, START, END

import concurrent.futures
from functools import partial
from src.utils import settings


logger = get_logger(module_name="planner_agent", DIR="analyst")

model = "gemini-2.0-flash"
llm_planer = ChatGoogleGenerativeAI(
    model=model,
    temperature=0.7,
    api_key=settings.GOOGLE_API_KEY
)


class State(TypedDict):
    # Estados iniciales
    engine : Engine
    topic : str

    doc : str
    plan : str

    input_tokens : int
    output_tokens : int
    api_calls : int


def documenter_node(state: State) -> State:
    logger.info("---"*4 + " documenter_node (Parallel)\n\n")
    engine = state["engine"]
    url = engine.url
    pg_utils = PostgresUtils(engine=engine)
    tables = pg_utils.get_tables_name(schema_name='public')
    
    logger.info("\n"*2)
    logger.info(tables)
    logger.info(f"\nUsuario: {url.username} | Host: {url.host} | DB: {url.database} | Password: {url.password}")
    logger.info("\n"*2)
    

    documentation = "# Documentación de la base de datos\n\n---\n\n"

    # Definimos una función auxiliar para procesar una sola tabla.
    # Esta es la función que se ejecutará en paralelo.
    def process_single_table(table_name):
        try:
            logger.info(f"Procesando tabla: {table_name}") 
            
            schema = pg_utils.get_table_schema(table_name=table_name)
            
            # relations = describe_table_relationships(
            #     table_name=table_name, 
            #     primary_keys=primary_keys, 
            #     foreign_keys=foreign_keys
            # )

            # doc_table = TABLE_SCHEMA_TEMPLATE_1.format(
            #     table_name=table_name,
            #     schema=schema,
            #     relations=relations
            # )

            doc_table = TABLE_SCHEMA_TEMPLATE_3.format(
                table_name=table_name,
                schema=schema,
            )
            return doc_table
        except Exception as e:
            logger.error(f"Error documentando tabla {table_name}: {e}")
            return f"Error al documentar la tabla {table_name}"

    # Ejecución Paralela usando Threads
    # max_workers define cuántas tablas procesar simultáneamente. 
    # 5 o 10 suele ser un buen número para no saturar el pool de conexiones de la BD.
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # executor.map mantiene el orden de la lista 'tables' en el resultado final
        results = list(executor.map(process_single_table, tables))

    documentation += "\n\n".join(results)
        
    logger.info(f"Se han documentado {len(results)} tablas exitosamente.\n\n")
    return {"doc": documentation}


def planner_node(state : State) -> State:
    logger.info("---"*4 + " planner_node\n\n")
    doc = state["doc"]
    topic = state["topic"]

    prompt = PLANER_PROMPT_2.format(doc=doc, topic=topic)
    ai_response = llm_planer.invoke(prompt)
    plan = ai_response.content
    logger.debug(f"plan: \n\n {plan} \n\n")

    input_tokens = ai_response.usage_metadata['input_tokens']
    output_tokens = ai_response.usage_metadata['output_tokens']
    api_calls = 1
    
    logger.info(f"input_tokens: {input_tokens}--output_tokens: {output_tokens}--api_calls: {api_calls}")
    return {"plan":plan, "input_tokens":input_tokens, "output_tokens":output_tokens, "api_calls":api_calls}


builder = StateGraph(State)

builder.add_node("documenter_node", documenter_node)
builder.add_node("planner_node", planner_node)

builder.add_edge(START, "documenter_node")
builder.add_edge("documenter_node", "planner_node")
builder.add_edge("planner_node", END)

planner_agent = builder.compile()