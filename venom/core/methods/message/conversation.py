# Convo Module by Meliodas
# https://github.com/thedragonsinn/plain-ub/blob/main/app/core/client/conversation.py
# Adjusted for dual clients

import asyncio
import json

from pyrogram import Client, filters
from pyrogram.handlers import EditedMessageHandler, MessageHandler
from pyrogram.types import Message

from venom import Config, venom

# Convo Filter to check incoming messages match chat id in dict
CONVO_FILTER: filters.Filter = filters.create(
    lambda _, __, message: (message.chat.id in Config.CONVO_DICT)
    and (not message.reactions)
)


# Listener for convo filtered messages
async def convo_handler(client: Client, message: Message):
    conv_dict: dict = Config.CONVO_DICT[message.chat.id]

    convo_client: Client = conv_dict["client"]
    # if convo client isn't same dont trigger response
    if client != convo_client:
        message.continue_propagation()

    conv_filters = conv_dict.get("filters")
    if conv_filters:
        # check filter match
        check = await conv_filters(client, message)
        if not check:
            message.continue_propagation()
        conv_dict["response"] = message
        message.continue_propagation()
    conv_dict["response"] = message
    message.continue_propagation()


#venom.add_handler(MessageHandler(callback=convo_handler, filters=CONVO_FILTER), group=0)
venom.add_handler(
    EditedMessageHandler(callback=convo_handler, filters=CONVO_FILTER), group=0
)
#venom.bot.add_handler(
#    MessageHandler(callback=convo_handler, filters=CONVO_FILTER), group=0
#)
venom.bot.add_handler(
    EditedMessageHandler(callback=convo_handler, filters=CONVO_FILTER), group=0
)


class Conversation:
    """
    try:
        async with Conversation(
            chat_id=message.chat.id,
            client=message._client,
            filters=filters,
            timeout=timeout,
        ) as convo:
            response: Message | None = await convo.get_response()
    except Conversation.TimeOutError:
        handle timeout

    or

    x = await venom.send_message(chat,text)
    await x.get_response()

    """

    class DuplicateConvo(Exception):
        def __init__(self, chat: str | int | None = None):
            text = "Conversation already started"
            if chat:
                text += f" with {chat}"
            super().__init__(text)

    class TimeOutError(Exception):
        def __init__(self):
            super().__init__("Conversation Timeout")

    def __init__(
        self,
        chat_id: int,
        client: Client,
        filters: filters.Filter | None = None,
        timeout: int = 10,
    ):
        self.chat_id = chat_id
        self.client = client
        self.filters = filters
        self.timeout = timeout

    def __str__(self):
        return json.dumps(self.__dict__, indent=4, ensure_ascii=False, default=str)

    async def get_response(self, timeout: int | None = None) -> Message | None:
        """wait for message to arrive,
        timeout can be extended in get_response if needed
        """
        try:
            async with asyncio.timeout(timeout or self.timeout):
                while not Config.CONVO_DICT[self.chat_id]["response"]:
                    await asyncio.sleep(0)
            return Config.CONVO_DICT[self.chat_id]["response"]
        except asyncio.TimeoutError:
            raise self.TimeOutError

    async def __aenter__(self) -> "Conversation":
        if self.chat_id in Config.CONVO_DICT:
            raise self.DuplicateConvo(self.chat_id)
        convo_dict = {"client": self.client, "filters": self.filters, "response": None}
        Config.CONVO_DICT[self.chat_id] = convo_dict
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        Config.CONVO_DICT.pop(self.chat_id, "")
