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
'''
class JvcProjectorSession:
    reader: Optional[asyncio.StreamReader] = None
    writer: Optional[asyncio.StreamWriter] = None
    final_status: Future[None]

    def __init__(self, projector: JvcProjector):
        self.projector = projector
        self.final_status = Future()

    async def _async_dispose(self) -> None:
        try:
            if self.reader is not None:
                self.reader.feed_eof()
        except Exception as e:
            logging.exception("Exception while closing reader")
        try:
            if self.writer is not None:
                self.writer.close()
                await self.writer.wait_closed()
        except Exception as e:
            logging.exception("Exception while closing writer")

    async def __aenter__(self) -> JvcProjectorSession:
        logging.debug("Entering async context manager")
        return self

    # exit the async context manager
    async def __aexit__(
            self,
            exc_type: type[BaseException],
            exc_val: Optional[BaseException],
            exc_tb: TracebackType
          ) -> Optional[bool]:
        if exc_val is None:
            logging.debug("Exiting async context manager")
        else:
            logging.exception(f"Exiting async context manager with exception, exc_type={exc_type}, exc_val={exc_val}, exc_tb={exc_tb}")

        await self._async_dispose()

        return False

    @property
    def host(self) -> str:
        return self.projector.host

    @property
    def port(self) -> int:
        return self.projector.port

    @property
    def timeout_secs(self) -> Optional[float]:
        return self.projector.timeout_secs

    @property
    def password(self) -> Optional[str]:
        return self.projector.password

    @classmethod
    async def create(cls, projector: JvcProjector):
        self = cls(projector)
        try:
            await self.connect()
        except BaseException as e:
            logging.exception("Exception while connecting")
            await self._async_dispose()
            raise e
        return self

    async def read_response_packet(self) -> Packet:
        """Reads a single response packet from the projector, with timeout"""
        assert self.reader is not None

        packet_bytes = await asyncio.wait_for(self.reader.readline(), self.timeout_secs)
        logging.debug(f"Read packet bytes: {packet_bytes.hex(' ')}")
        if len(packet_bytes) == 0:
            raise JvcProjectorError("Connection closed by projector")
        if packet_bytes[-1] != 0x0a:
            raise JvcProjectorError(f"Connection closed by projector with partial packet: {packet_bytes.hex(' ')}")
        try:
            result = Packet(packet_bytes)
            result.validate()
        except Exception as e:
            raise JvcProjectorError(f"Invalid response packet received from projector: {packet_bytes.hex(' ')}") from e
        if not result.is_response:
            raise JvcProjectorError(f"Received packet is not a response: {result}")
        return result

    async def read_response_packets(self, command_code: bytes, is_advanced: bool=False) -> Tuple[Packet, Optional[Packet]]:
        """Reads a basic response packet and an optional advanced response packet"""
        basic_response_packet = await self.read_response_packet()
        advanced_response_packet: Optional[Packet] = None
        if basic_response_packet.command_code != command_code:
            raise JvcProjectorError(f"Received response packet for wrong command code (expected {command_code.hex(' ')}): {basic_response_packet}")
        if basic_response_packet.is_advanced_response:
            raise JvcProjectorError(f"Received advanced response packet before basic response packet: {basic_response_packet}")
        if is_advanced:
            advanced_response_packet = await self.read_response_packet()
            if advanced_response_packet.command_code != command_code:
                raise JvcProjectorError(f"Received second response packet for wrong command code (expected {command_code.hex(' ')}): {advanced_response_packet}")
            if not advanced_response_packet.is_advanced_response:
                raise JvcProjectorError(f"Received second basic response packet instead of advanced response packet: {advanced_response_packet}")
        return (basic_response_packet, advanced_response_packet)

    async def read_exactly(self, length: int) -> bytes:
        assert self.reader is not None

        data = await asyncio.wait_for(self.reader.readexactly(length), self.timeout_secs)
        logging.debug(f"Read exactly {len(data)} bytes: {data.hex(' ')}")
        return data

    async def write_exactly(self, data: bytes | bytearray | memoryview) -> None:
        assert self.writer is not None

        logging.debug(f"Writing exactly {len(data)} bytes: {data.hex(' ')}")
        self.writer.write(data)
        await asyncio.wait_for(self.writer.drain(), self.timeout_secs)

    async def send_packet(self, packet: Packet) -> None:
        """Sends a packet to the projector"""
        await self.write_exactly(packet.raw_data)

    async def transact(
            self,
            command_packet: Packet,
          ) -> Tuple[Packet, Optional[Packet]]:
        """Sends a command packet and reads the response packets"""
        await self.send_packet(command_packet)
        basic_response_packet, advanced_response_packet = await self.read_response_packets(
            command_packet.command_code, command_packet.is_advanced_command)
        return (basic_response_packet, advanced_response_packet)

    async def command(self, cmd: JvcCommand) -> JvcResponse:
        result = await cmd(self)
        return result

    async def cmd_null(self) -> None:
        await self.command(null_command)

    async def cmd_power_status(self) -> PowerStatus:
        response = await self.command(power_status_command)
        return response.power_status

    async def cmd_power_on(self) -> None:
        await self.command(power_on_command)

    async def cmd_power_off(self) -> None:
        await self.command(power_off_command)

    async def connect(self) -> None:
        assert self.reader is None and self.writer is None
        logging.debug(f"Connecting to: {self.projector}")
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
        # Perform the initial handshake. This is a bit weird, since the projector
        # sends a greeting, then we send a request, then the projector sends an
        # acknowledgement, but none of these include a terminating newline.
        logging.debug(f"Handshake: Waiting for greeting")
        greeting = await self.read_exactly(len(PJ_OK))
        if greeting != PJ_OK:
            raise JvcProjectorError(f"Handshake: Unexpected greeting (expected {PJ_OK}): {greeting.hex}")
        logging.debug(f"Handshake: Received greeting: {greeting.hex(' ')}")
        # newer projectors (e.g., DLA-NX8) require a password to be appended to the PJREQ blob
        # (with an underscore separator). Older projectors (e.g., DLA-X790) do not accept a password.
        req_data = PJREQ if self.password is None else PJREQ + b'_' + self.password.encode('utf-8')
        logging.debug(f"Handshake: writing auth data: {req_data.hex(' ')}")
        await self.write_exactly(req_data)
        pjack = await asyncio.wait_for(self.reader.readexactly(len(PJACK)), self.timeout_secs)
        logging.debug(f"Handshake: Read exactly {len(pjack)} bytes: {pjack.hex(' ')}")
        if pjack != PJACK:
            raise JvcProjectorError(f"Handshake: Unexpected ack (expected {PJACK.hex(' ')}): {pjack.hex(' ')}")
        logging.info(f"Handshake: {self} connected and authenticated")

    def __str__(self) -> str:
        return f"JvcProjectorSession(host={self.host}, port={self.port})"

    def __repr__(self) -> str:
       return str(self)

    async def close(self) -> None:
       await self._async_dispose()

'''

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

    transaction_lock: asyncio.Lock
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
        self.host = host
        self.port = port
        self.password = password
        self.timeout_secs = timeout_secs
        self.final_status = asyncio.Future()
        self.transaction_lock = asyncio.Lock()

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
        async with self.transaction_lock:
            return await self._read_response_packet()

    async def _read_response_packets(self, command_code: bytes, is_advanced: bool=False) -> Tuple[Packet, Optional[Packet]]:
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
        async with self.transaction_lock:
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
        async with self.transaction_lock:
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
        async with self.transaction_lock:
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
        async with self.transaction_lock:
            await self._send_packet(packet)

    async def _transact(
            self,
            command_packet: Packet,
          ) -> Tuple[Packet, Optional[Packet]]:
        """Sends a command packet and reads the response packet(s), with timeout (nonlocking).

        The first response packet is the basic response. The second response packet
        is the advanced response, if the command packet is an advanced command, or
        None otherwise (if the command packet is an advanced command, the projector
        will send a basic response packet followed by an advanced response packet).

        Basic validation is performed on the response packets (e.g., that the
        magic number is correct, that the response command code matches the command code).

        On error, the transport will be shut down, and no further interaction is possible.
        """
        await self._send_packet(command_packet)
        basic_response_packet, advanced_response_packet = await self._read_response_packets(
            command_packet.command_code, command_packet.is_advanced_command)
        return (basic_response_packet, advanced_response_packet)

    async def transact(
            self,
            command_packet: Packet,
          ) -> Tuple[Packet, Optional[Packet]]:
        """Sends a command packet and reads the response packet(s), with timeout.

        The first response packet is the basic response. The second response packet
        is the advanced response, if the command packet is an advanced command, or
        None otherwise (if the command packet is an advanced command, the projector
        will send a basic response packet followed by an advanced response packet).

        Basic validation is performed on the response packets (e.g., that the
        magic number is correct, that the response command code matches the command code).

        On error, the transport will be shut down, and no further interaction is possible.
        """
        async with self.transaction_lock:
            return await self._transact(command_packet)

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

    async def __aenter__(self) -> TcpJvcProjectorClientTransport:
        """Enters a context that will close the transport on exit."""
        return self

    async def connect(self) -> None:
        try:
            async with self.transaction_lock:
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
            host: str,
            password: Optional[str]=None,
            port: int=DEFAULT_PORT,
            timeout_secs: float=DEFAULT_TIMEOUT
          ) -> Self:
        transport = cls(host, password=password, port=port, timeout_secs=timeout_secs)
        await transport.connect()
        # on error, the transport will be shut down, and no further interaction is possible
        return transport

    def __str__(self) -> str:
        return f"TcpJvcProjectorClientTransport({self.host}:{self.port})"

    def __repr__(self) -> str:
        return str(self)
