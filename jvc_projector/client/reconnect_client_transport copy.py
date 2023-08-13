# Copyright (c) 2023 Samuel J. McKelvie
#
# MIT License - See LICENSE file accompanying this package.
#

"""
Auto-reconnect JVC Projector TCP/IP client transport.

Provides an implementation of JvcProjectorClientTransport
that dynamically connects/disconnects/reconnects to another transport.
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

from .connector import JvcProjectorConnector
from .client_config import JvcProjectorClientConfig
from .client_transport import (
    JvcProjectorClientTransport,
    ResponsePackets
  )

from .resolve_host import resolve_projector_tcp_host

class ReconnectJvcProjectorClientTransport(JvcProjectorClientTransport):
    """JVC Projector client transport that automatically
       connects/disconnects/reconnects to another transport."""

    config: JvcProjectorClientConfig

    connector: JvcProjectorConnector
    """The connector to use to connect to the projector."""

    current_transport: Optional[JvcProjectorClientTransport] = None
    """The current transport, or None if not connected."""

    final_status: Future[None]
    """A future that will be set when the transport is closed."""

    _transaction_lock: asyncio.Lock
    """A mutex to ensure that only one transaction is in progress at a time;
    this allows multiple callers to use the same transport without worrying
    about mixing up response packets."""

    idle_timer: Optional[asyncio.TimerHandle] = None
    timing_out: bool = False
    timeout_task: Optional[asyncio.Task[None]] = None

    def __init__(
            self,
            connector: JvcProjectorConnector,
            config: Optional[JvcProjectorClientConfig]=None,
          ) -> None:
        """Initializes the transport."""
        super().__init__()
        self.config = JvcProjectorClientConfig(base_config=config)
        self.connector = connector
        self.final_status = asyncio.get_event_loop().create_future()
        self._transaction_lock = asyncio.Lock()

    # @abstractmethod
    def is_shutting_down(self) -> bool:
        """Returns True if the transport is shutting down or closed."""
        return self.final_status.done()

    async def get_connected_transport(self) -> JvcProjectorClientTransport:
        """Returns the current transport, or connects if not connected.
        """
        if self.is_shutting_down():
            raise JvcProjectorError("Transport is shutting down")
        if self.current_transport is not None and self.current_transport.is_shutting_down():
            self.cancel_idle_timer()
            try:
                await self.current_transport.wait()
            except BaseException:
                pass
            self.current_transport = None

        if self.current_transport is None:
            self.current_transport = await self.connector.connect()
            self.restart_idle_timer()

        return self.current_transport

    def cancel_idle_timer(self) -> None:
        """Cancels the idle timer on the current transport."""
        if self.idle_timer is not None:
            self.idle_timer.cancel()
            self.idle_timer = None
        self.timing_out = False
        if self.timeout_task is not None:
            self.timeout_task.cancel()
            self.timeout_task = None

    def restart_idle_timer(self) -> None:
        """Restarts the idle timer on the current transport."""
        self.cancel_idle_timer()
        if self.current_transport is not None:
            self.timing_out = True
            self.idle_timer = asyncio.get_event_loop().call_later(
                self.config.idle_disconnect_secs,
                lambda: self.idle_timeout_callback()
            )

    def idle_timeout_callback(self) -> None:
        """Called when the idle timer expires."""
        self.idle_timer = None
        if self.timeout_task is None:
            self.timeout_task = asyncio.get_event_loop().create_task(self.on_idle_timeout())

    async def on_idle_timeout(self) -> None:
        """Called when the idle timeout expires."""
        if self.timing_out:
            self.timing_out = False
            if self.current_transport is not None:
                logger.debug("Idle timeout; closing projector transport")
                await self.current_transport.shutdown()

    # @abstractmethod
    async def begin_transaction(self) -> None:
        """Acquires the transaction lock.
        """
        await self._transaction_lock.acquire()

    # @abstractmethod
    async def end_transaction(self) -> None:
        """Releases the transaction lock.
        """
        self._transaction_lock.release()

    # @abstractmethod
    async def transact_no_lock(
            self,
            command_packet: Packet,
          ) -> ResponsePackets:
        """Sends a command packet and reads the response packet(s).

        The first response packet is the basic response. The second response
        packet is the advanced response, if any.

        The caller must be holding the transaction lock. Ordinary users
        should use the transaction() context manager or call transact()
        instead.
        """
        transport = await self.get_connected_transport()
        try:
            self.cancel_idle_timer()
            result = await transport.transact(command_packet)
        finally:
            self.restart_idle_timer()

        return result

    # @abstractmethod
    async def shutdown(self, exc: Optional[BaseException] = None) -> None:
        """Shuts the transport down. Does not wait for the transport to finish
           closing. Safe to call from a callback or with transaction lock.

        If exc is not None, sets the final status of the transport.

        Has no effect if the transport is already shutting down or closed.

        Does not raise an exception based on final status.
        """
        if not self.final_status.done():
            if exc is not None:
                self.final_status.set_exception(exc)
            else:
                self.final_status.set_result(None)
        self.cancel_idle_timer()
        if self.current_transport is not None:
            await self.current_transport.shutdown()

    # @abstractmethod
    async def wait(self) -> None:
        """Waits for complete shutdown/cleanup. Does not initiate shutdown.
        Not safe to call from a callback.

        Returns immediately if the transport is already closed.
        Raises an exception if the final status of the transport is an exception.
        """
        try:
            await self.final_status
        finally:
            if self.current_transport is not None:
                await self.current_transport.wait()
                self.current_transport = None

    # @override
    async def __aenter__(self) -> ReconnectJvcProjectorClientTransport:
        """Enters a context that will close the transport on exit."""
        return self


    def __str__(self) -> str:
        return f"ReconnectJvcProjectorClientTransport({self.connector})"

    def __repr__(self) -> str:
        return str(self)
