from langchain_postgres.vectorstores import PGVector
from langchain_ollama import OllamaEmbeddings
from src.utils import settings

model = "bge-m3:latest"
embedding = OllamaEmbeddings(model=model, base_url=settings.SERVER_AI_URL)
connection = f"postgresql+psycopg2://{settings.DB_USER}:{settings.DB_PASS}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"


vector_store = PGVector(
    embeddings=embedding,
    collection_name="mi_coleccion",
    connection=connection,
    embedding_length=1024
)

docs = vector_store.similarity_search(query="ventas", k=4)
print("\n")
for doc in docs:
    print(doc.page_content)
    print("\n\n")
    print("=="*40)
    print("\n\n")


"""
python3 -m src.test.pg_retrive

"""