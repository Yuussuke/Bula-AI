from langchain_core.prompts import ChatPromptTemplate
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.rag.llm import get_maritalk_llm

router = APIRouter(prefix="/chat", tags=["chat"])


class DirectAskRequest(BaseModel):
    question: str


class DirectAskResponse(BaseModel):
    answer: str


@router.post("/direct-ask")
async def direct_ask(
    req: DirectAskRequest,
    current_user: User = Depends(get_current_user),
) -> DirectAskResponse:
    # current_user is used for authentication verification
    _ = current_user
    llm = get_maritalk_llm()

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are Bula AI, a virtual assistant specialized in Brazilian medication leaflets."
                " Answer in Brazilian Portuguese, be clear, objective, and friendly, and always remind"
                " the user to consult a physician.",
            ),
            ("human", "{input}"),
        ]
    )

    chain = prompt | llm

    response = await chain.ainvoke({"input": req.question})

    return DirectAskResponse(answer=str(response.content))
