from typing import List, Dict, Any
from src.utils import settings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from ..models import models as chat_models
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage, ToolCall
from  ...chatDB.prompts.chatPrompts import SYSTEM_PROMPT_4
from langchain_google_genai import ChatGoogleGenerativeAI
from ...chatDB.grphs.chatdb import create_chat_agent
from sqlalchemy.engine import URL



from src.utils.logging_config import get_logger
logger = get_logger(module_name="run_chat", DIR="crud")


def run_chat(user_id : int, chat_id : int, human_message : str) -> List[Dict[str, Any]]:

    database_url = f"postgresql+psycopg2://{settings.DB_USER}:{settings.DB_PASS}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()


    messages_model_record = chat_models.MessageModel(
    user_id=user_id,
    chat_id=chat_id,
    role="Human",
    content={"content" : human_message}
    )
    session.add(messages_model_record)
    session.flush()

    logger.info(f"user message añadido a el orm de la db \n")

    message_history = session.query(chat_models.MessageModel).filter_by(user_id=user_id, chat_id=chat_id).order_by(chat_models.MessageModel.date.asc()).all()
    logger.info("historial de conversacion recuperado de la db\n")

    database_analysis_records = session.query(chat_models.AnalystModel).filter_by(user_id=user_id, chat_id=chat_id).all()
    data_analysis = database_analysis_records[0].final_analysis

    logger.info(f"====== Recuperando el estado del agente \n")
    messages = []
    messages.append(SystemMessage(content=SYSTEM_PROMPT_4.format(data_analysis=data_analysis)))

    for msg in message_history:
        if msg.role == "Human":
            logger.info("Human")
            messages.append(HumanMessage(content=msg.content['content']))
        elif msg.role == "Ai":
            logger.info(f"Ai")
            tool_calls = msg.content['tool_calls']
            langchain_tool_calls = [
                ToolCall(
                    name=y['name'],
                    args=y['args'],
                    id=y['id'],
                    type=y['type']
                ) for y in tool_calls
            ]
            #logger.debug(f"type: \n {type(langchain_tool_calls)} \n {langchain_tool_calls}")
            messages.append(
                AIMessage(
                    content=msg.content['content'],
                    tool_calls=langchain_tool_calls,
                    usage_metadata=msg.content["usage_metadata"]
                )
            )
        elif msg.role == "Tool":
            logger.info("Tool")
            messages.append(
                ToolMessage(
                    content=msg.content['content'],
                    tool_call_id=msg.content['tool_call_id']
                )
            )

    #   user_model_records = session.query(chat_models.UserModel).filter_by(user_id=user_id).all()
    #   user_db_credentials = user_model_records[0].db_credentials
    #   user_conn_string = f"postgresql+psycopg2://{user_db_credentials["db_user"]}:{user_db_credentials["db_pass"]}@{user_db_credentials["db_host"]}:{user_db_credentials["db_port"]}/{user_db_credentials["db_name"]}"
    #   logger.info(f"user_conn_string: {user_conn_string} \n")
    #   user_engine = create_engine(user_conn_string)


    user_model_records = session.query(chat_models.UserModel).filter_by(user_id=user_id).all()
    user_db_credentials = user_model_records[0].db_credentials

    user_url = URL.create(
        drivername="postgresql+psycopg2",
        username=user_db_credentials["db_user"],
        password=user_db_credentials["db_pass"],  # SIN encode manual
        host=user_db_credentials["db_host"],
        port=user_db_credentials["db_port"],
        database=user_db_credentials["db_name"],
    )

    user_engine = create_engine(user_url)


    model = "gemini-2.0-flash"
    llm = ChatGoogleGenerativeAI(model=model, temperature=0.5, api_key=settings.GOOGLE_API_KEY)
    chatagent = create_chat_agent(llm=llm, engine=user_engine)
    logger.info("Agente creado \n")

    agent_response = chatagent.invoke({"messages":messages})
    logger.info(f"Agente invokado con exito, estados: {agent_response.keys()} \n\n\n")

    api_response = []
    messages = agent_response["messages"]
    logger.info(f"Hay {len(messages)} mensages")
    N = len(messages) - 1
    for i in range(N):
        message = messages[N-i]
        if isinstance(message, HumanMessage):
            logger.info(f"\n{message.pretty_repr()}\n")
            break
        elif isinstance(message, AIMessage):
            logger.info(f"\n{message.pretty_repr()}\n")
            content = message.content
            toolcalls = [{
                'name':x["name"],
                'args':x["args"],
                'id':x["id"],
                'type':x["type"]
            } for x in (message.tool_calls or [])] # Por si message.tool_calls es None
            usagemetadata = message.usage_metadata
            data = {"content":content, "tool_calls":toolcalls, "usage_metadata":usagemetadata}
            messages_model_record = chat_models.MessageModel(
                user_id=user_id,
                chat_id=chat_id,
                role="Ai",
                content=data
            )
            session.add(messages_model_record)
            session.flush()
            data['type'] = 'Ai'
            api_response.append(data)
        elif isinstance(message, ToolMessage):
            logger.info(f"\n{message.pretty_repr()}\n")
            content = message.content
            tool_call_id = message.tool_call_id
            name = message.name
            data = {"content":content, "tool_call_id":tool_call_id, "name":name}
            messages_model_record = chat_models.MessageModel(
                user_id=user_id,
                chat_id=chat_id,
                role="Tool",
                content=data
            )
            session.add(messages_model_record)
            session.flush()
            data['type'] = 'Tool'
            api_response.append(data)

    session.commit()
    session.close()
    api_response = list(reversed(api_response))    
    return {'chat_response':api_response}





  
