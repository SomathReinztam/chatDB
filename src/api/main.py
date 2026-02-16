from fastapi import FastAPI
from pydantic import BaseModel
from src.database.crud.crud import CrudHelper
from src.database.crud.run_chat import run_chat
from pydantic import BaseModel
from typing import List, Dict, Any, Union, Literal, Optional
from src.utils import settings


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


"""
En la raiz:
uvicorn src.api.main:app --reload

"""