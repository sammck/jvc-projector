from __future__ import annotations

from ..internal_types import *
from .packet import Packet

from abc import ABC, abstractmethod

class JvcProjectorTransport(ABC):
    @abstractmethod
    async def transact(
            self,
            command_packet: Packet,
          ) -> Tuple[Packet, Optional[Packet]]:
        """Sends a command packet and reads the response packets"""
        raise NotImplementedError()
