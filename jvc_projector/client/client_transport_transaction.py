# Copyright (c) 2023 Samuel J. McKelvie
#
# MIT License - See LICENSE file accompanying this package.
#

"""
JVC Projector client transport transaction context manager.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod

from ..internal_types import *
from ..pkg_logging import logger
from ..protocol import Packet
from .multi_response_packets import MultiResponsePackets
if TYPE_CHECKING:
    from .client_transport import (
        JvcProjectorClientTransport,
        ResponsePackets,
    )

class JvcProjectorClientTransportTransaction():
    """A context manager that holds a transaction lock on a transport and allows one or
       more transact() calls to be made with the lock held."""
    transport: JvcProjectorClientTransport
    context_entered: bool = False

    def __init__(self, transport: JvcProjectorClientTransport) -> None:
        self.transport = transport

    async def __aenter__(self) -> JvcProjectorClientTransportTransaction:
        """Enters a context that will release the transaction lock on exit."""
        assert not self.context_entered
        await self.transport.begin_transaction()
        self.context_entered = True
        return self

    async def __aexit__(
            self,
            exc_type: Optional[Type[BaseException]],
            exc: Optional[BaseException],
            tb: Optional[TracebackType],
          ) -> None:
        """Exits the context, releases the transaction lock."""
        assert self.context_entered
        self.context_entered = False
        await self.transport.end_transaction()

    async def transact(
            self,
            command_packet: Packet,
          ) -> ResponsePackets:
        """Sends a command packet and reads the response packet(s).

        The first response packet is the basic response. The second response
        packet is the advanced response, if any.

        A transaction lock is held during the transaction to ensure that only one transaction
        is in progress at a time.
        """
        if not self.context_entered:
            async with self:
                return await self.transport.transact_no_lock(command_packet)
        else:
            return await self.transport.transact_no_lock(command_packet)

    async def multi_transact(
            self,
            command_packets: Iterable[Packet],
          ) -> MultiResponsePackets:
        """Sends multiple command packets and reads all response packet(s),
           encapsulating them in MultiResponsePackets.

        Does not raise an exception if some commands fail. Instead, the
        exception is stored in the MultiResponsePackets object. The caller
        should call wait() on the MultiResponsePackets object to rethrow
        the exception. Any commands that succeeded before the
        failure will have their responses available in the responses list.

        example:
            async with transport.transaction() as transaction:
                responses = await transaction.multi_transact(command_packets)
                for response in await responses.wait():
                    ...
        """
        if not self.context_entered:
            async with self:
                return await self.transport.multi_transact_no_lock(command_packets)
        else:
            return await self.transport.multi_transact_no_lock(command_packets)
