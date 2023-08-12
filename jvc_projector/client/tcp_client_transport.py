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

from .client_transport import (
    JvcProjectorClientTransport,
    ResponsePackets
  )

from .resolve_host import resolve_projector_tcp_host

class TcpJvcProjectorClientTransport(JvcProjectorClientTransport):
    """JVC Projector TCP/IP client transport."""

    reader: Optional[asyncio.StreamReader] = None
    writer: Optional[asyncio.StreamWriter] = None
    host: str
    port: int
    password: Optional[str] = None
    timeout_secs: float
    final_status: Future[None]
    reader_closed: bool = False
    writer_closed: bool = False

    _transaction_lock: asyncio.Lock
    """A mutex to ensure that only one transaction is in progress at a time;
    this allows multiple callers to use the same transport without worrying
    about mixing up response packets."""


    def __init__(
            self,
            host: str,
            password: Optional[str]=None,
            port: int=DEFAULT_PORT,
            timeout_secs: float = DEFAULT_TIMEOUT
          ) -> None:
        """Initializes the transport.
        """
        super().__init__()
        self.host = host
        self.port = port
        self.password = password
        self.timeout_secs = timeout_secs
        self.final_status = asyncio.get_event_loop().create_future()
        self._transaction_lock = asyncio.Lock()

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

    async def _read_response_packet(self) -> Packet:
        """Reads a single response packet from the projector, with timeout (nonlocking).

        All packets end in b'\n' (0x0a). Not usable for initial handshake
        and authentication.

        On error, the transport will be shut down, and no further interaction is possible.
        """
        assert self.reader is not None

        try:
            packet_bytes = await asyncio.wait_for(self.reader.readline(), self.timeout_secs)
            logger.debug(f"Read packet bytes: {packet_bytes.hex(' ')}")
            if len(packet_bytes) == 0:
                raise JvcProjectorError("Connection closed by projector while waiting for response")
            if packet_bytes[-1] != 0x0a:
                raise JvcProjectorError(f"Connection closed by projector with partial response packet: {packet_bytes.hex(' ')}")
            try:
                result = Packet(packet_bytes)
                result.validate()
            except Exception as e:
                raise JvcProjectorError(f"Invalid response packet received from projector: {packet_bytes.hex(' ')}") from e
            if not result.is_response:
                raise JvcProjectorError(f"Received packet is not a response: {result}")
        except Exception as e:
            await self.shutdown(e)
            raise
        return result

    async def read_response_packet(self) -> Packet:
        """Reads a single response packet from the projector, with timeout.

        All packets end in b'\n' (0x0a). Not usable for initial handshake
        and authentication.

        On error, the transport will be shut down, and no further interaction is possible.
        """
        async with self._transaction_lock:
            return await self._read_response_packet()

    async def _read_response_packets(self, command_code: bytes, is_advanced: bool=False) -> ResponsePackets:
        """Reads a basic response packet and an optional advanced response packet (nonlocking).

        On error, the transport will be shut down, and no further interaction is possible.
        """
        try:
            basic_response_packet = await self._read_response_packet()
            advanced_response_packet: Optional[Packet] = None
            if basic_response_packet.command_code != command_code:
                raise JvcProjectorError(f"Received response packet for wrong command code (expected {command_code.hex(' ')}): {basic_response_packet}")
            if basic_response_packet.is_advanced_response:
                raise JvcProjectorError(f"Received advanced response packet before basic response packet: {basic_response_packet}")
            if is_advanced:
                advanced_response_packet = await self._read_response_packet()
                if advanced_response_packet.command_code != command_code:
                    raise JvcProjectorError(f"Received second response packet for wrong command code (expected {command_code.hex(' ')}): {advanced_response_packet}")
                if not advanced_response_packet.is_advanced_response:
                    raise JvcProjectorError(f"Received second basic response packet instead of advanced response packet: {advanced_response_packet}")
        except Exception as e:
            await self.shutdown(e)
            raise
        return (basic_response_packet, advanced_response_packet)

    async def read_response_packets(self, command_code: bytes, is_advanced: bool=False) -> Tuple[Packet, Optional[Packet]]:
        """Reads a basic response packet and an optional advanced response packet.

        On error, the transport will be shut down, and no further interaction is possible.
        """
        async with self._transaction_lock:
            return await self._read_response_packets(command_code, is_advanced=is_advanced)

    async def _read_exactly(self, length: int) -> bytes:
        """Reads exactly the specified number of bytes from the projector, with timeout (nonlocking).

        Usable for initial handshake and authentication which do not terminate
        exchanges with b'\n' (0x0a).

        On error, the transport will be shut down, and no further interaction is possible.
        """
        assert self.reader is not None

        try:
            data = await asyncio.wait_for(self.reader.readexactly(length), self.timeout_secs)
            logger.debug(f"Read exactly {len(data)} bytes: {data.hex(' ')}")
        except Exception as e:
            await self.shutdown(e)
            raise
        return data

    async def read_exactly(self, length: int) -> bytes:
        """Reads exactly the specified number of bytes from the projector, with timeout.

        Usable for initial handshake and authentication which do not terminate
        exchanges with b'\n' (0x0a).

        On error, the transport will be shut down, and no further interaction is possible.
        """
        async with self._transaction_lock:
            return await self._read_exactly(length)

    async def _write_exactly(self, data: bytes | bytearray | memoryview) -> None:
        """Writes exactly the specified number of bytes to the projector, with timeout (nonlocking).

        On error, the transport will be shut down, and no further interaction is possible.
        """
        assert self.writer is not None

        try:
            logger.debug(f"Writing exactly {len(data)} bytes: {data.hex(' ')}")
            self.writer.write(data)
            await asyncio.wait_for(self.writer.drain(), self.timeout_secs)
        except Exception as e:
            await self.shutdown(e)
            raise

    async def write_exactly(self, data: bytes | bytearray | memoryview) -> None:
        """Writes exactly the specified number of bytes to the projector, with timeout.

        On error, the transport will be shut down, and no further interaction is possible.
        """
        async with self._transaction_lock:
            await self._write_exactly(data)

    async def _send_packet(self, packet: Packet) -> None:
        """Sends a single command packet to the projector, with timeout (nonlocking).

        On error, the transport will be shut down, and no further interaction is possible.
        """
        await self._write_exactly(packet.raw_data)

    async def send_packet(self, packet: Packet) -> None:
        """Sends a single command packet to the projector, with timeout.

        On error, the transport will be shut down, and no further interaction is possible.
        """
        async with self._transaction_lock:
            await self._send_packet(packet)

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
        await self._send_packet(command_packet)
        basic_response_packet, advanced_response_packet = await self._read_response_packets(
            command_packet.command_code, command_packet.is_advanced_command)
        return (basic_response_packet, advanced_response_packet)

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
        try:
            if not self.reader_closed:
                self.reader_closed = True
                if self.reader is not None:
                    self.reader.feed_eof()
        except Exception as e:
            logger.debug("Exception while closing reader", exc_info=True)
        finally:
            try:
                if not self.writer_closed:
                    self.writer_closed = True
                    if self.writer is not None:
                        self.writer.close()
                    # await self.writer.wait_closed()
            except Exception as e:
                logger.debug("Exception while closing writer", exc_info=True)

    # @abstractmethod
    async def wait(self) -> None:
        """Waits for complete shutdown/cleanup. Does not initiate shutdown.
        Not safe to call from a callback.

        Returns immediately if the transport is already closed.
        Raises an exception if the final status of the transport is an exception.
        """
        try:
            if self.writer is not None:
                await self.writer.wait_closed()
        except Exception as e:
            logger.debug("Exception while waiting for writer to close", exc_info=True)
            await self.shutdown(e)
        finally:
            if not self.final_status.done():
                await self.shutdown()
        await self.final_status

    # @override
    async def __aenter__(self) -> TcpJvcProjectorClientTransport:
        """Enters a context that will close the transport on exit."""
        return self

    async def connect(self) -> None:
        """Connect to the projector and authenticate/handshake, with timeout.
        """
        try:
            async with self._transaction_lock:
                try:
                    assert self.reader is None and self.writer is None
                    logger.debug(f"Connecting to projector at {self.host}:{self.port}")
                    self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
                    # Perform the initial handshake. This is a bit weird, since the projector
                    # sends a greeting, then we send a request, then the projector sends an
                    # acknowledgement, but none of these include a terminating newline.
                    logger.debug(f"Handshake: Waiting for greeting")
                    greeting = await self._read_exactly(len(PJ_OK))
                    if greeting != PJ_OK:
                        raise JvcProjectorError(f"Handshake: Unexpected greeting (expected {PJ_OK.hex(' ')}): {greeting.hex(' ')}")
                    logger.debug(f"Handshake: Received greeting: {greeting.hex(' ')}")
                    # newer projectors (e.g., DLA-NX8) require a password to be appended to the PJREQ blob
                    # (with an underscore separator). Older projectors (e.g., DLA-X790) do not accept a password.
                    req_data = PJREQ
                    if not self.password is None and len(self.password) > 0:
                        req_data += b'_' + self.password.encode('utf-8')
                        logger.debug(f"Handshake: writing auth data: {PJREQ.hex(' ')} + _<password>")
                    else:
                        logger.debug(f"Handshake: writing hello data: {PJREQ.hex(' ')}")
                    await self._write_exactly(req_data)
                    pjack = await self._read_exactly(len(PJACK))
                    logger.debug(f"Handshake: Read exactly {len(pjack)} bytes: {pjack.hex(' ')}")
                    if pjack == PJNAK:
                        raise JvcProjectorError(f"Handshake: Authentication failed (bad password?)")
                    elif pjack != PJACK:
                        raise JvcProjectorError(f"Handshake: Unexpected ack (expected {PJACK.hex(' ')}): {pjack.hex(' ')}")
                    logger.info(f"Handshake: {self} connected and authenticated")
                except BaseException as e:
                    await self.shutdown(e)
                    raise
        except BaseException as e:
            await self.aclose(e)
            raise

    @classmethod
    async def create(
            cls,
            host: Optional[str]=None,
            password: Optional[str]=None,
            port: Optional[int]=None,
            timeout_secs: float=DEFAULT_TIMEOUT
          ) -> Self:
        """Creates and connects a transport to
           a JVC Projector that is reachable over TCP/IP.

              Args:
                host: The hostname or IPV4 address of the projector.
                      may optionally be prefixed with "tcp://".
                      May be suffixed with ":<port>" to specify a
                      non-default port, which will override the port argument.
                      May be "sddp://" or "sddp://<host>" to use
                      SSDP to discover the projector.
                      If None, the host will be taken from the
                        JVC_PROJECTOR_HOST environment variable.
                password:
                      The projector password. If None, the password
                      will be taken from the JVC_PROJECTOR_PASSWORD
                      environment variable. If an empty string or the
                      environment variable is not found, no password
                      will be used.
                port: The default TCP/IP port number to use. If None, the port
                      will be taken from the JVC_PROJECTOR_PORT. If that
                      environment variable is not found, the default JVC
                      projector port (20554) will be used.
                timeout_secs: The default timeout for operations on the
                        transport. If not provided, DEFAULT_TIMEOUT (2 seconds)
                        is used.
        """
        final_host, final_port, sddp_info = await resolve_projector_tcp_host(
            host,
            port
          )

        transport = cls(final_host, password=password, port=final_port, timeout_secs=timeout_secs)
        await transport.connect()
        # on error, the transport will be shut down, and no further interaction is possible
        return transport

    def __str__(self) -> str:
        return f"TcpJvcProjectorClientTransport({self.host}:{self.port})"

    def __repr__(self) -> str:
        return str(self)
