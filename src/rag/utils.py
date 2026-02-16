import asyncio
from src.utils.db_utils import PostgresUtils
from sqlalchemy.engine import Engine
from langchain_core.language_models.chat_models import BaseChatModel
from .prompts import SYSTEM_TABLE_DOCUMENTER_PROMPT_1

async def procces_single_table_doc(table_name : str, n_semaphore : int, engine : Engine, llm : BaseChatModel):

    semaphore = asyncio.Semaphore(n_semaphore)
    pg_utils = PostgresUtils(engine=engine)

    async with semaphore:
        try:
            schema = await asyncio.to_thread(pg_utils.get_table_schema, table_name)
            prompt = SYSTEM_TABLE_DOCUMENTER_PROMPT_1.format(schema=schema)
            ai_response = await llm.ainvoke(prompt)
            return ai_response.content

        except Exception as e:
            print(f"Error en procces_single_table_doc:\n\n {e}")
            return None


