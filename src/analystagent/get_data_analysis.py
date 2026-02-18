
from sqlalchemy.engine import URL
from sqlalchemy import create_engine
from .graphs.planner import planner_agent
from .graphs.analyst import create_analyst_agent
from langchain_core.messages import SystemMessage, HumanMessage
from .prompts.analystprompts import SYSTEM_DEEP_QUERIES_PROMPT_3, HUMAN_DEEP_QUERIES_PROMPT_2
from sqlalchemy.orm import sessionmaker
from src.utils import settings
from src.database.models import models

from src.utils.logging_config import get_logger



logger = get_logger(module_name='main', DIR="analyst")

def get_data_analysis(db_user : str, db_pass : str, db_host : str, db_port : str, db_name : str, query : str):
    user_url = URL.create(
        drivername="postgresql+psycopg2",
        username=db_user,
        password=db_pass,
        host=db_host,
        port=db_port,
        database=db_name
    )
    user_engine = create_engine(user_url)

    initial_state = {'engine': user_engine, 'topic':query}
    response = planner_agent.invoke(initial_state)

    plan = response['plan']
    input_tokens = response['input_tokens']
    output_tokens = response['output_tokens']
    api_calls = response['api_calls']




    analyst_agent = create_analyst_agent(engine=user_engine)
    messages = [SystemMessage(content=SYSTEM_DEEP_QUERIES_PROMPT_3.format(topic=query, plan=plan)), HumanMessage(content=HUMAN_DEEP_QUERIES_PROMPT_2.format(topic=query))]
    initial_state = {'messages':messages}
    response = analyst_agent.invoke(initial_state)

    analysis = response['analysis']
    final_analysis = response['final_analysis']
    input_tokens += response['input_tokens']
    output_tokens += response['output_tokens']
    api_calls += response['api_calls']

    database_url = f"postgresql+psycopg2://{settings.DB_USER}:{settings.DB_PASS}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    # TODO: por el momento el usuario y el chat id estan quemados
    analyst_model_record = models.AnalystModel(
        user_id=1,
        chat_id=1,
        final_analysis=final_analysis,
        analysis=analysis
    )
    session.add(analyst_model_record)
    session.flush()
    session.commit()
    session.close()

    return {'final_analysis':final_analysis}




