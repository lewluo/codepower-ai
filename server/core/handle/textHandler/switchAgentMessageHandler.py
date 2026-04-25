from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

from core.handle.proposalHandler import switch_pending_proposal_agent
from core.handle.textMessageHandler import TextMessageHandler
from core.handle.textMessageType import TextMessageType


class SwitchAgentTextMessageHandler(TextMessageHandler):
    @property
    def message_type(self) -> TextMessageType:
        return TextMessageType.SWITCH_AGENT

    async def handle(self, conn: "ConnectionHandler", msg_json: Dict[str, Any]) -> None:
        await switch_pending_proposal_agent(conn, msg_json.get("agent_id"))
