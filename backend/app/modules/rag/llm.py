from langchain_community.chat_models import ChatMaritalk

from app.core.config import settings

def get_maritalk_llm() -> ChatMaritalk:
    """Create a ChatMaritalk instance.

    `MARITACA_API_KEY` is optional at app boot time to keep CI/dev flows working.
    This function enforces it when the LLM is actually used.
    """
    if not settings.maritaca_api_key:
        raise RuntimeError("MARITACA_API_KEY is not configured")

    return ChatMaritalk(
        api_key=settings.maritaca_api_key,
        model="sabiazinho-4",
    )
