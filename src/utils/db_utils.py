from sqlalchemy.engine import Engine
from sqlalchemy import text, MetaData, Table
from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects import postgresql
from typing import List

class PostgresUtils:
    def __init__(self, engine : Engine):
        self.engine = engine

    def get_tables_name(self, schema_name : str = 'public') -> List[str]:
        with self.engine.connect() as conn:
            result = conn.execute(text(f"""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = '{schema_name}'
                ORDER BY table_name;
            """))
            tables = [row[0] for row in result]
        return tables

        
    def get_table_schema(self, table_name : str) -> str:
        try:
            metadata =MetaData()
            table = Table(table_name, metadata, autoload_with=self.engine)
            ddl = CreateTable(table).compile(
                dialect=postgresql.dialect(),
                compile_kwargs={"literal_binds": True}
            )
            return str(ddl)
        except Exception as e:
            raise f"{e}"
        




if __name__=="__main__":
    from sqlalchemy import create_engine
    conn_string = "postgresql+psycopg2://postgres:postgres@localhost:5434/northwind"
    engine = create_engine(conn_string)

    postgrs_utils = PostgresUtils(engine=engine)
    schema = postgrs_utils.get_table_schema(table_name='employee_territories')
    print(schema)
    pass

"""
python3 -m src.utils.db_utils

"""