from handlers.channels import router as channels_router
from handlers.chats import router as chats_router
from handlers.common import router as common_router
from handlers.info import router as info_router

__all__ = ["common_router", "channels_router", "chats_router", "info_router"]
