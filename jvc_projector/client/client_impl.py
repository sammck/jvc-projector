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
import time

from ..internal_types import *
from ..exceptions import JvcProjectorError
from ..constants import DEFAULT_TIMEOUT, DEFAULT_PORT, STABLE_POWER_TIMEOUT
from ..pkg_logging import logger
from ..protocol import (
    Packet,
    JvcModel,
    JvcCommand,
    JvcResponse,
    CommandMeta,
    models,
    name_to_command_meta,
    model_status_list_map,
  )

from .client_transport import JvcProjectorClientTransport
from .tcp_client_transport import TcpJvcProjectorClientTransport

POWER_POLL_INTERVAL = 0.5
"""Seconds between power status pools while waiting for power to stabilize (e.g.,
   waiting for warmup or cooldown)."""
class JvcProjectorClient:
    """JVC Projector TCP/IP client."""

    transport: JvcProjectorClientTransport
    final_status: Future[None]

    model: Optional[JvcModel] = None
    stable_power_timeout: float

    model_status_query_command_meta = name_to_command_meta("model_status.query")


    def __init__(
            self,
            transport: JvcProjectorClientTransport,
            model: Optional[JvcModel]=None,
            stable_power_timeout: float=STABLE_POWER_TIMEOUT,
          ):
        self.transport = transport
        self.final_status = asyncio.get_event_loop().create_future()
        self.model = model
        self.stable_power_timeout = stable_power_timeout

    async def transact(
            self,
            command: JvcCommand,
          ) -> JvcResponse:
        """Sends a command and reads the response."""
        command_packet = command.command_packet
        basic_response_packet, advanced_response_packet = await self.transport.transact(command_packet)
        response = command.create_response_from_packets(
            basic_response_packet, advanced_response_packet)
        if self.model is None and command.name == "model_status.query":
            # if we don't know the projector model, and we just got a model_status.query response,
            # then we can use the response to determine the model
            _, default_model = model_status_list_map[response.payload]
            self.model = default_model
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
            model: Optional[JvcModel]=None,
          ) -> Self:
        transport = await TcpJvcProjectorClientTransport.create(
                host,
                password=password,
                port=port,
                timeout_secs=timeout_secs
              )
        try:
            self = cls(transport, model=model)
        except BaseException as e:
            await transport.aclose()
            raise
        return self

    async def cmd_null(self) -> JvcResponse:
        """Send a null command."""
        return await self.transact_by_name("test_command.null_command")

    async def cmd_power_status(self) -> JvcResponse:
        """Send a power status query command and returns the response.

        The friendly power status name is available with response.response_str().
        """
        return await self.transact_by_name("power_status.query")

    async def power_status_wait(self, stable_power_timeout: Optional[float]=None) -> JvcResponse:
        """Waits for power to stabilize (e.g., not warming up or cooling down) and returns
           the final stable power status response.

           raises JvcProjectorError if the power status does not stabilize within
              stable_power_timeout seconds. If stable_power_timeout is None, then
              the timeout provided at construction is used.

           The friendly power status name is available with response.response_str().
        """
        if stable_power_timeout is None:
            stable_power_timeout = self.stable_power_timeout
        first = True
        start_time = time.monotonic()
        while True:
            response = await self.cmd_power_status()
            if response.response_str() == "Warming":
                # warming up
                if first:
                    logger.debug(f"{self}: Waiting for projector to warm up")
                    first = False
            elif response.response_str() == "Cooling":
                # cooling down
                if first:
                    logger.debug(f"{self}: Waiting for projector to cool down")
                    first = False
            else:
                # stable power status
                return response
            remaining_timeout = stable_power_timeout - (time.monotonic() - start_time)
            if remaining_timeout <= 0:
                raise JvcProjectorError(f"{self}: Power status did not stabilize within {stable_power_timeout} seconds")
            await asyncio.sleep(min(POWER_POLL_INTERVAL, remaining_timeout))

    async def cmd_power_on(self) -> JvcResponse:
        """Send a power on command.

        Does not wait for the power to stabilize either before or after sending the command.

        NOTE: For some or all projectors (at least DLA-NZ8), this command will fail
              (the projector will not send any response) if the projector is not in "Standby" state.
              For a safe, reliable power-on command, use power_on_wait().
        """
        return await self.transact_by_name("power.on")

    async def power_on_wait(
            self,
            wait_for_final: bool=True,
            stable_power_timeout: Optional[float]=None
        ) -> JvcResponse:
        """Turns the projector on if it is not already on.

        If the projector is cooling down, waits for it to finish cooling down before turning it on.
        If wait_for_final is True, waits for the projector to finish warming up before returning.
        If wait_for_final is False, returns as soon as the projector is either on or warming up.

        If the projector is in "Emergency" mode, raises an exception.

        The friendly power status name at return time (either "On" or "Warming") is available
        with response.response_str().
        """
        response = await self.cmd_power_status()
        response_str = response.response_str()
        if response_str == "Cooling" or (response_str == "Warming" and wait_for_final):
            response = await self.power_status_wait(stable_power_timeout=stable_power_timeout)
            response_str = response.response_str()
        if response_str == "Standby":
            await self.cmd_power_on()
            if wait_for_final:
                response = await self.power_status_wait(stable_power_timeout=stable_power_timeout)
            else:
                response = await self.cmd_power_status()
            response_str = response.response_str()

        if response_str == "Emergency":
            raise JvcProjectorError(f"{self}: Projector is in Emergency mode")
        elif response_str not in ("On", "Warming"):
            raise JvcProjectorError(f"{self}: Unexpected power status: {response_str}")

        return response

    async def cmd_power_off(self) -> JvcResponse:
        """Send a power off command.

        Does not wait for the power to stabilize either before or after sending the command.

        NOTE: For some or all projectors (at least DLA-NZ8), this command will fail
              (the projector will not send any response) if the projector is not in "On" state.
              For a safe, reliable power-off command, use power_off_wait().
        """
        return await self.transact_by_name("power.off")

    async def power_off_wait(
            self,
            wait_for_final: bool=True,
            stable_power_timeout: Optional[float]=None
          ) -> JvcResponse:
        """Turns the projector off (Standby) if it is not already in "Standby".

        If the projector is warming up, waits for it to finish warming up before turning it off.
        If wait_for_final is True, waits for the projector to finish cooling down before returning.
        If wait_for_final is False, returns as soon as the projector is either in Standby or cooling down.

        If the projector is in "Emergency" mode, raises an exception.

        The friendly power status name at return time (either "On" or "Warming") is available
        with response.response_str().
        """
        response = await self.cmd_power_status()
        response_str = response.response_str()
        if response_str == "Warming" or (response_str == "Cooling" and wait_for_final):
            response = await self.power_status_wait(stable_power_timeout=stable_power_timeout)
            response_str = response.response_str()
        if response_str == "On":
            await self.cmd_power_off()
            if wait_for_final:
                response = await self.power_status_wait(stable_power_timeout=stable_power_timeout)
            else:
                response = await self.cmd_power_status()
            response_str = response.response_str()

        if response_str == "Emergency":
            raise JvcProjectorError(f"{self}: Projector is in Emergency mode")
        elif response_str not in ("Standby", "Cooling"):
            raise JvcProjectorError(f"{self}: Unexpected power status: {response_str}")

        return response

    async def cmd_model_status(self) -> JvcResponse:
        return await self.transact_by_name("model_status.query")

    def __str__(self) -> str:
        return f"JvcProjectorClient(transport={self.transport})"

    def __repr__(self) -> str:
       return str(self)

    async def aclose(self) -> None:
       await self._async_dispose()
