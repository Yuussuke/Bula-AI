from langchain_community.chat_models import ChatMaritalk
from app.core.config import settings

def get_maritalk_llm() -> ChatMaritalk:
    """Factory function to create and return a ChatMaritalk instance configured with the API key and model."""
    return ChatMaritalk(
        api_key=settings.maritaca_api_key, 
        model="sabiazinho-4" 
    )