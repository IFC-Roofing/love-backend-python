from app.crud.user_crud import user_crud
from app.crud.contact_crud import contact_crud
from app.crud.postcard_crud import postcard_crud
from app.crud.mailing_crud import mailing_crud
from app.crud.chat_room_crud import chat_room_crud
from app.crud.chat_participant_crud import chat_participant_crud
from app.crud.chat_message_crud import chat_message_crud

__all__ = [
    "user_crud",
    "contact_crud",
    "postcard_crud",
    "mailing_crud",
    "chat_room_crud",
    "chat_participant_crud",
    "chat_message_crud",
]
