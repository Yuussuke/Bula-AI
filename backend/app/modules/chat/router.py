from fastapi import APIRouter, Depends
from pydantic import BaseModel
from langchain_core.prompts import ChatPromptTemplate
from app.modules.rag.llm import get_maritalk_llm
from app.modules.auth.dependencies import get_current_user

router = APIRouter(prefix="/chat", tags=["chat"])

class DirectAskRequest(BaseModel):
    question: str

@router.post("/direct-ask")
async def direct_ask(
    req: DirectAskRequest, 
    current_user = Depends(get_current_user)
):
    # current_user is used for authentication verification
    llm = get_maritalk_llm()
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Você é o Bula AI, um assistente virtual especialista em bulas de medicamentos no Brasil. Seja claro,"
        "objetivo e amigável. Sempre lembre o usuário de consultar um médico."),
        ("human", "{input}")
    ])
    
    chain = prompt | llm
    
    response = await chain.ainvoke({"input": req.question})
    
    return {"answer": response.content}