from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

from core.handle.proposalHandler import reject_pending_proposal
from core.handle.textMessageHandler import TextMessageHandler
from core.handle.textMessageType import TextMessageType


class RejectTextMessageHandler(TextMessageHandler):
    @property
    def message_type(self) -> TextMessageType:
        return TextMessageType.REJECT

    async def handle(self, conn: "ConnectionHandler", msg_json: Dict[str, Any]) -> None:
        await reject_pending_proposal(conn)
