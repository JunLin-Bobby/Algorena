"""Inbound WebSocket event names accepted by Room.handle()."""

from typing import Literal

InboundEvent = Literal["join", "start", "submit", "violation"]

JOIN: InboundEvent = "join"
START: InboundEvent = "start"
SUBMIT: InboundEvent = "submit"
VIOLATION: InboundEvent = "violation"
