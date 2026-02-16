from sqlalchemy.engine import Engine
from src.utils.db_utils import PostgresUtils
from langchain_core.language_models.chat_models import BaseChatModel
from .utils import procces_single_table_doc
import asyncio
from src.utils import settings
from langchain_core.embeddings.embeddings import Embeddings
from langchain_postgres.vectorstores import PGVector

async def make_vector_collection(engine : Engine, llm_documenter : BaseChatModel, n_semaphore : int, embedding : Embeddings, embedding_length : int):
    pg_utils = PostgresUtils(engine=engine)

    db_tables = pg_utils.get_tables_name()
    print(f"hay {len(db_tables)} tablas en la db \n")

    tasks = [procces_single_table_doc(table_name=table_name, n_semaphore=n_semaphore, engine=engine, llm=llm_documenter) for table_name in db_tables]
    tasks_result = await asyncio.gather(*tasks) # Es una lista donde cada elemento es none o es la documentacion de una tabla en lenguaje natural
    print(f"tasks resueltos exitosamente, primer elemento de tasks_result: \n {tasks_result[0]} \n \nlongitud de tasks_result:{len(tasks_result)}")

    conn_string = f"postgresql+psycopg2://{settings.DB_USER}:{settings.DB_PASS}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"

    vector_store = PGVector(
        embeddings=embedding,
        collection_name="mi_coleccion",
        connection=conn_string,
        embedding_length=embedding_length
    )

    ids = vector_store.add_texts(texts=tasks_result)
    print("fin")




if __name__=="__main__":
    from langchain_groq import ChatGroq
    from sqlalchemy import create_engine
    from langchain_ollama import OllamaEmbeddings

    model = "openai/gpt-oss-20b"
    GROQ_API_KEY = settings.GROQ_API_KEY
    llm = ChatGroq(model=model, temperature=0.2, api_key=GROQ_API_KEY)

    # Para conseguir el esquema de las tablas de northwind
    conn_string = "postgresql+psycopg2://postgres:postgres@localhost:5434/northwind"
    engine = create_engine(conn_string)

    model = "bge-m3:latest"
    embedding = OllamaEmbeddings(model=model, base_url=settings.SERVER_AI_URL)

    # Hacer vector store
    asyncio.run(
        make_vector_collection(
            engine=engine,
            llm_documenter=llm,
            n_semaphore=5,
            embedding=embedding,
            embedding_length=1024
        )
    )



    



"""
python3 -m src.rag.main

"""