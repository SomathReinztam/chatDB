from sqlalchemy.engine import Engine
from sqlalchemy import text
from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool
from langchain_core.tools.base import BaseTool
from typing import List
from sqlalchemy import text, MetaData, Table
from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects import postgresql
from pathlib import Path
import pandas as pd
from datetime import datetime


root = Path(__file__).resolve().parent.parent.parent.parent

class AgentToolKit:
    def __init__(self, engine : Engine, schema_name : str = 'public'):
        self.engine = engine
        self.schema_name = schema_name
    
    # ---  Helper methods

    def _get_db_tables_names(self) -> str:
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(
                    f"""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = '{self.schema_name}'
                    ORDER BY table_name
                    """
                ))
                rows = result.fetchall()
                response = f"Hay {len(rows)} tablas en la base de datos:\n\n"
                for row in rows:
                    response += f"{row[0]}\n"
                return response
        except Exception as e:
            return f"Error: {e}"
        
    
    def _get_table_schema(self, table_name: str) -> str:
        try:
            metadata = MetaData()
            # Intenta cargar la tabla. Si falla, SQLAlchemy lanzará error.
            table = Table(table_name, metadata, autoload_with=self.engine)
            
            ddl = CreateTable(table).compile(
                dialect=postgresql.dialect(),
                compile_kwargs={"literal_binds": True}
            )
            return str(ddl)
        except Exception as e:
            return f"Error obteniendo esquema de la tabla '{table_name}': {str(e)}"
    
    def _get_tables_schemas(self, tables_names : List[str]) -> str:
        try:
            schemas = ""
            for name in tables_names:
                schemas += f"{self._get_table_schema(name)}"
                schemas += "\n\n"
            return schemas
        except Exception as e:
            return f"- Error: {e} \n\n"
        
    
    def _query_data_base(self, query: str) -> str:
        try:
            # Se recomienda usar bloques try/except para conexiones DB
            with self.engine.connect() as conn:
                result = conn.execute(text(query))
                rows = result.fetchall()
            
            if len(rows) >= 15:
                response = f"Hay {len(rows)} registros en la respuesta de la consulta. Se ha limitado a los primeros 15 registros: \n\n {rows[:15]}"
                return response
            else:
                response = f"Hay {len(rows)} registros en la respuesta de la consulta: \n\n {rows}"
                return response
        except Exception as e:
            return f"Error ejecutando query SQL: {str(e)}"
        
    
            
    def _make_id(self):
        # Corrección: datetime.now() no acepta formato directo, se usa strftime después
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    # --- NUEVO HELPER PARA CSV ---
    def _export_query_to_csv(self, query: str) -> str:
        try:
            # 1. Definir la carpeta de salida (ej: carpeta 'exports' en el root)
            output_dir = root / "exports"
            output_dir.mkdir(parents=True, exist_ok=True) # Crea la carpeta si no existe

            # 2. Generar nombre de archivo único
            filename = f"query_result_{self._make_id()}.csv"
            file_path = output_dir / filename

            # 3. Usar pandas para ejecutar la query y guardar directamente a CSV
            # Pandas maneja automáticamente los encabezados y tipos de datos
            df = pd.read_sql(query, self.engine)
            
            # Guardar archivo
            df.to_csv(file_path, index=False)
            
            return f"Consulta exportada exitosamente. Archivo guardado en: {str(file_path)}"
        
        except Exception as e:
            return f"Error al generar el archivo CSV: {str(e)}"


        

    # --- args_schema

    class TablesSchemas(BaseModel):
        tables_names : List[str] = Field(description="Lista con los nombres de las tablas de la base de datos")
    
    class QueryDataBaseArgs(BaseModel):
        query: str = Field(description="Query SQL válida para PostgreSQL.")


    # --- return

    def get_tools(self) -> List[BaseTool]:
        tools = [
            StructuredTool.from_function(
                name="get_db_tables_names",
                description="Retorna el nombre de todas las tablas de la base de datos del usuario",
                func=self._get_db_tables_names
                # No needs args
            ),
            StructuredTool.from_function(
                name="get_tables_schemas",
                description="Retorna el esquema de una lista de tablas",
                func=self._get_tables_schemas,
                args_schema=self.TablesSchemas
            ),
            StructuredTool.from_function(
                name="query_data_base",
                description="Ejecuta una consulta SQL en PostgreSQL y retorna hasta 15 filas.",
                func=self._query_data_base,
                args_schema=self.QueryDataBaseArgs
            ),
            StructuredTool.from_function(
                name="export_query_to_csv",
                description="Ejecuta una consulta SQL y guarda TODOS los resultados en un archivo CSV local. Útil cuando se necesitan analizar muchos datos o descargar un reporte.",
                func=self._export_query_to_csv,
                args_schema=self.QueryDataBaseArgs 
            )
        ]

        return tools
    

if __name__=="__main__":
    from sqlalchemy import create_engine
    
    schema_name = 'public'
    conn_string = "postgresql+psycopg2://postgres:postgres@localhost:5434/northwind"
    engine = create_engine(conn_string)

    toolkit = AgentToolKit(engine=engine, schema_name=schema_name)
    tools = toolkit.get_tools()
    print(f"\n hay {len(tools)} tools \n")

    for tool in tools:
        print(type(tool))

    print("\n")

    # tables_name = tools[0]
    # tool_response = tables_name.invoke({})
    # print(tool_response)


    # tables_name = tools[1]
    # tool_response = tables_name.invoke({'tables_names':['customers', 'products', 'territories']})
    # print(tool_response)


    
    # query2 = "SELECT * FROM customers LIMIT 5;"


    # tables_name = tools[2]
    # tool_response = tables_name.invoke({'query':query2})
    # print(tool_response)

    # root = Path(__file__).resolve().parent.parent.parent.parent
    # print(root)


    my_tool = tools[3]
    query = "SELECT * FROM categories LIMIT 10;"
    response = my_tool.invoke({"query":query})
    print(response)

    


"""
python3 -m src.chatDB.tools.toolkit

"""