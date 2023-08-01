# Copyright (c) 2023 Samuel J. McKelvie
#
# MIT License - See LICENSE file accompanying this package.
#

"""
JVC Projector client abstract transport interface.

Provides a low-level abstract interface for sending opaque command packets
to a JVC projector and receiving opaque response packets. Does not provide session
establishment, handshake or authentication. Does not provide any higher-level
abstractions such as semantic commands or responses.

This abstraction allows for the implementation of proxies and alternate network
transports (e.g., HTTP).
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod

from ..internal_types import *
from ..pkg_logging import logger
from ..protocol import Packet


class JvcProjectorClientTransport(ABC):
    @abstractmethod
    async def transact(
            self,
            command_packet: Packet,
          ) -> Tuple[Packet, Optional[Packet]]:
        """Sends a command packet and reads the response packet(s).

        The first response packet is the basic response. The second response
        packet is the advanced response, if any.

        Must be implemented by subclasses.
        """
        raise NotImplementedError()

    @abstractmethod
    async def shutdown(self, exc: Optional[BaseException] = None) -> None:
        """Shuts the transport down. Does not wait for the transport to finish
           closing. Safe to call from a callback.

        If exc is not None, sets the final status of the transport.

        Has no effect if the transport is already shutting down or closed.

        Does not raise an exception based on final status.

        Must be implemented by subclasses.
        """
        raise NotImplementedError()

    @abstractmethod
    async def wait(self) -> None:
        """Waits for complete shutdown/cleanup. Does not initiate shutdown
        Not safe to call from a callback.

        Returns immediately if the transport is already closed.
        Raises an exception if the final status of the transport is an exception.

        Must be implemented by a subclass.
        """
        raise NotImplementedError()

    # @abstractmethod
    async def aclose(self, exc: Optional[BaseException] = None) -> None:
        """Closes the transport and waits for complete shutdown/cleanup.
        Not safe to call from a callback.

        If exc is not None, sets the final status of the transport.

        Has no effect if the transport is already closed.

        Raises an exception if the final status of the transport is an exception.

        May be overridden by subclasses. The default implementation simply calls
        shutdown() and then wait().
        """
        await self.shutdown(exc)
        await self.wait()

    async def __aenter__(self) -> JvcProjectorClientTransport:
        """Enters a context that will close the transport on exit."""
        return self

    async def __aexit__(
            self,
            exc_type: Optional[Type[BaseException]],
            exc: Optional[BaseException],
            tb: Optional[TracebackType],
          ) -> None:
        """Exits the context, closes the transport, and waits for complete shutdown/cleanup."""
        # Close the transport without raising an exception
        closer: asyncio.Task[None] = asyncio.ensure_future(self.aclose(exc))
        assert isinstance(closer, asyncio.Task)
        done, pending = await asyncio.wait([closer])
        assert len(done) == 1 and len(pending) == 0
        if exc is None:
            # raise the exception from the transport if there is one
            closer.result()

