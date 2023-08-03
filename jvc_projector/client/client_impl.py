# Copyright (c) 2023 Samuel J. McKelvie
#
# MIT License - See LICENSE file accompanying this package.
#

"""
JVC Projector TCP/IP client transport.

Provides an implementation of JvcProjectorClientTransport over a TCP/IP
socket.
"""

from __future__ import annotations

import asyncio
from asyncio import Future
from abc import ABC, abstractmethod

from ..internal_types import *
from ..exceptions import JvcProjectorError
from ..constants import DEFAULT_TIMEOUT, DEFAULT_PORT
from ..pkg_logging import logger
from ..protocol import Packet, PJ_OK, PJREQ, PJACK, PJNAK

from .client_transport import JvcProjectorClientTransport
from .tcp_client_transport import TcpJvcProjectorClientTransport
from ..protocol import ( JvcCommand, JvcResponse, )

class JvcProjectorClient:
    """JVC Projector TCP/IP client."""

    transport: JvcProjectorClientTransport
    final_status: Future[None]

    def __init__(self, transport: JvcProjectorClientTransport):
        self.transport = transport
        self.final_status = Future()

    async def transact(
            self,
            command: JvcCommand,
          ) -> JvcResponse:
        """Sends a command and reads the response."""
        command_packet = command.command_packet
        basic_response_packet, advanced_response_packet = await self.transport.transact(command_packet)
        response = command.create_response_from_packets(
            basic_response_packet, advanced_response_packet)
        return response

    async def transact_by_name(
            self,
            command_name: str,
            payload: Optional[bytes]=None,
          ) -> JvcResponse:
        """Sends a command and reads the response."""
        command = JvcCommand.create_from_name(command_name, payload=payload)
        return await self.transact(command)


    async def _async_dispose(self) -> None:
        await self.transport.aclose()

    async def __aenter__(self) -> JvcProjectorClient:
        logger.debug(f"{self}: Entering async context manager")
        return self

    async def __aexit__(
            self,
            exc_type: type[BaseException],
            exc_val: Optional[BaseException],
            exc_tb: TracebackType
          ) -> None:
        logger.debug(f"{self}: Exiting async context manager, exc={exc_val}")
        await self._async_dispose()

    @classmethod
    async def create(
            cls,
            host: str,
            password: Optional[str]=None,
            port: int=DEFAULT_PORT,
            timeout_secs: float=DEFAULT_TIMEOUT,
          ) -> Self:
        transport = await TcpJvcProjectorClientTransport.create(
                host,
                password=password,
                port=port,
                timeout_secs=timeout_secs
              )
        try:
            self = cls(transport)
        except BaseException as e:
            await transport.aclose()
            raise
        return self

    async def cmd_null(self) -> JvcResponse:
        return await self.transact_by_name("test_command.null_command")

    async def cmd_power_status(self) -> JvcResponse:
        return await self.transact_by_name("power_status.query")

    async def cmd_power_on(self) -> JvcResponse:
        return await self.transact_by_name("power.on")

    async def cmd_power_off(self) -> JvcResponse:
        return await self.transact_by_name("power.off")

    def __str__(self) -> str:
        return f"JvcProjectorClient(transport={self.transport})"

    def __repr__(self) -> str:
       return str(self)

    async def aclose(self) -> None:
       await self._async_dispose()
