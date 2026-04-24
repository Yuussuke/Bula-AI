from app.modules.chat.service import ChatService


def get_chat_service() -> ChatService:
    return ChatService()
