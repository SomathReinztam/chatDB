from fastapi import FastAPI
from pydantic import BaseModel
from src.database.crud.crud import CrudHelper
from src.database.crud.run_chat import run_chat
from src.analystagent.get_data_analysis import get_data_analysis
from pydantic import BaseModel
from typing import List, Dict, Any, Union, Literal, Optional
from src.utils import settings

from src.utils.logging_config import setup_base_logging

setup_base_logging()
app = FastAPI()

crud_helper = CrudHelper(db_host=settings.DB_HOST, db_pass=settings.DB_PASS, db_user=settings.DB_USER, db_name=settings.DB_NAME, db_port=settings.DB_PORT)


class MessageResponse(BaseModel):
    message : str


class PostNewUser(BaseModel):
    name : str
    db_credentials : Dict[str, Any]

@app.post("/newuser/", response_model=MessageResponse)
async def new_user_api(body : PostNewUser):
    crud_helper.post_new_user(name=body.name, db_credentials=body.db_credentials)
    return MessageResponse(message="Usuario creado exitosamente.")


# ------------------------

# class ToolCall(BaseModel):
#     name: str
#     args: Dict[str, Any]
#     id: str
#     type: str

# class UsageMetadata(BaseModel):
#     input_tokens: int
#     output_tokens: int
#     total_tokens: int
#     input_token_details: Dict[str, Any]

# class ChatItemAI(BaseModel):
#     type: Literal["Ai"]
#     content: Any
#     tool_calls: List[ToolCall] = []
#     usage_metadata: Optional[UsageMetadata] = None



# class ChatItemTool(BaseModel):
#     type: Literal["Tool"]
#     content: str
#     tool_call_id: str
#     name: str



# ChatItem = Union[ChatItemAI, ChatItemTool]

# class RunChatResponse(BaseModel):
#     chat_response: List[ChatItem]


class RunChatResponse(BaseModel):
    chat_response: List[Dict[str, Any]]


class RunChat(BaseModel): 
    user_id : int 
    chat_id : int 
    human_message : str


@app.post("/runchat", response_model=RunChatResponse)
async def run_chat_api(body: RunChat):
    return run_chat(
        user_id=body.user_id,
        chat_id=body.chat_id,
        human_message=body.human_message
    )


# -----------------------

class GetAnalysisResponse(BaseModel):
    final_analysis : str

class GetAnalysis(BaseModel):
    db_user : str
    db_pass : str
    db_host : str
    db_port : str
    db_name : str
    query : str

@app.post("/getanalysis", response_model=GetAnalysisResponse)
async def get_data_analysis_api(body : GetAnalysis):
    return get_data_analysis(
        db_user=body.db_user,
        db_pass=body.db_pass,
        db_host=body.db_host,
        db_port=body.db_port,
        db_name=body.db_name,
        query=body.query
    )
    



# -----------------------


"""
En la raiz:
uvicorn src.api.main:app --reload

"""