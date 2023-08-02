# Copyright (c) 2023 Samuel J. McKelvie
#
# MIT License - See LICENSE file accompanying this package.
#

"""
JVC Projector emulator.

Provides a simple emulation of a JVC projector on TCP/IP.
"""

from __future__ import annotations

import asyncio
from enum import Enum

from ..internal_types import *
from ..pkg_logging import logger
from ..protocol import Packet, PJ_OK, PJREQ, PJACK, PJNAK, END_OF_PACKET_BYTES
from ..constants import DEFAULT_PORT
from ..exceptions import JvcProjectorError

from ..protocol.command_meta import bytes_to_command_meta

HANDSHAKE_TIMEOUT = 5.0
"""Timeout for the initial handshake."""

IDLE_TIMEOUT = 30.0
"""Timeout for idle connections, after handshake."""

class EmulatorSessionState(Enum):
    UNCONNECTED = 0
    SENDING_GREETING = 1
    READING_AUTHENTICATION = 2
    SENDING_AUTH_ACK = 3
    SENDING_AUTH_NAK = 4
    READING_COMMAND = 5
    RUNNING_COMMAND = 6
    SENDING_RESPONSE = 7
    SHUTTING_DOWN = 8
    CLOSED = 9

class JvcProjectorEmulatorSession(asyncio.Protocol):
    session_id: int = -1
    emulator: JvcProjectorEmulator
    transport: Optional[asyncio.Transport] = None
    peer_name: str = "<unconnected>"
    description: str = "EmulatorSession(<unconnected>)"
    state: EmulatorSessionState = EmulatorSessionState.UNCONNECTED
    partial_data: bytes = b""
    transport_closed: bool = True
    auth_timer: Optional[asyncio.TimerHandle] = None
    idle_timer: Optional[asyncio.TimerHandle] = None

    def __init__(self, emulator: JvcProjectorEmulator):
        self.emulator = emulator
        self.session_id = emulator.alloc_session_id(self)
        self.description = f"EmulatorSession(id={self.session_id}, from=<unconnected>)"

    @property
    def password(self) -> Optional[str]:
        return self.emulator.password

    def write(self, data: Union[bytes, bytearray, memoryview]) -> None:
        if self.transport is None:
            logger.debug(f"EmulatorSession: Attempt to write to closed session {self.description}; ignored")
            return
        self.transport.write(data)

    def connection_made(self, transport: asyncio.BaseTransport):
        """Called when a connection is made.

        The argument is the transport representing the pipe connection.
        To receive data, wait for data_received() calls.
        When the connection is closed, connection_lost() is called.
        """
        assert isinstance(transport, asyncio.Transport)
        assert self.state == EmulatorSessionState.UNCONNECTED
        self.transport = transport
        self.transport_closed = False
        self.peer_name = transport.get_extra_info('peername')
        self.description = f"EmulatorSession(id={self.session_id}, from='{self.peer_name}')"
        logger.debug(f"EmulatorSession: Connection from {self.peer_name}")
        self.state = EmulatorSessionState.SENDING_GREETING
        self.transport.write(PJ_OK)
        self.state = EmulatorSessionState.READING_AUTHENTICATION
        self.auth_timer = asyncio.get_running_loop().call_later(
            HANDSHAKE_TIMEOUT,
            lambda: self._on_auth_read_timeout())

    def close(self) -> None:
        if not self.state in (EmulatorSessionState.CLOSED, EmulatorSessionState.SHUTTING_DOWN):
            self.state = EmulatorSessionState.SHUTTING_DOWN
            if not self.transport_closed and not self.transport is None:
                self.transport_closed = True
                self.transport.close()
            self.state = EmulatorSessionState.CLOSED
            self.emulator.free_session_id(self.session_id)

    def _on_auth_read_timeout(self) -> None:
        assert not self.transport is None
        self.auth_timer = None
        if self.state == EmulatorSessionState.READING_AUTHENTICATION:
            logger.debug(f"{self}: Authentication timeout")
            self.state = EmulatorSessionState.SENDING_AUTH_NAK
            self.transport.write(PJNAK)
            self.close()

    def _on_idle_read_timeout(self) -> None:
        assert not self.transport is None
        self.idle_timer = None
        if self.state == EmulatorSessionState.READING_COMMAND:
            logger.debug(f"{self}: Idle timeout")
            self.close()

    def data_received(self, data: bytes) -> None:
        """Called when some data is received."""
        assert not self.transport is None
        try:
            self.partial_data += data
            i_eop = self.partial_data.find(END_OF_PACKET_BYTES)
            if self.state == EmulatorSessionState.READING_AUTHENTICATION:
                valid_auth_data = PJREQ
                password = self.password
                if not password is None and len(password) > 0:
                    valid_auth_data += b'_' + password.encode('utf-8')
                nb_auth = len(valid_auth_data)
                if len(self.partial_data) >= nb_auth or (0 <= i_eop < nb_auth):
                    if not self.auth_timer is None:
                        self.auth_timer.cancel()
                        self.auth_timer = None
                    if 0 <= i_eop < nb_auth:
                        auth_data = self.partial_data[:i_eop+1]
                    else:
                        auth_data = self.partial_data[:nb_auth]
                    self.partial_data = self.partial_data[len(auth_data):]
                    if auth_data == valid_auth_data:
                        logger.debug(f"{self}: Authentication successful")
                        self.state = EmulatorSessionState.SENDING_AUTH_ACK
                        self.transport.write(PJACK)
                        self.state = EmulatorSessionState.READING_COMMAND
                        self.idle_timer = asyncio.get_running_loop().call_later(
                            IDLE_TIMEOUT,
                            lambda: self._on_idle_read_timeout())
                    else:
                        logger.debug(f"{self}: Authentication failed")
                        self.state = EmulatorSessionState.SENDING_AUTH_NAK
                        self.transport.write(PJNAK)
                        self.close()
            elif i_eop >= 0 and self.state == EmulatorSessionState.READING_COMMAND:
                if not self.idle_timer is None:
                    self.idle_timer.cancel()
                    self.idle_timer = None
                packet_bytes = self.partial_data[:i_eop + 1]
                self.partial_data = self.partial_data[i_eop + 1:]
                packet = Packet(packet_bytes)
                self.state = EmulatorSessionState.RUNNING_COMMAND
                self.emulator.on_packet_received(self, packet)
                self.state = EmulatorSessionState.READING_COMMAND
                self.idle_timer = asyncio.get_running_loop().call_later(
                    IDLE_TIMEOUT,
                    lambda: self._on_idle_read_timeout())
        except BaseException as e:
            logger.exception(f"{self}: Exception while processing data: {e}")
            self.close()
            raise


    def connection_lost(self, exc: Optional[BaseException]) -> None:
        """Called when the connection is lost or closed.

        The argument is an exception object or None (the latter
        meaning a regular EOF is received or the connection was
        aborted or closed).
        """
        logger.debug(f"{self}: Connection lost, exception={exc}; closing connection")
        self.close()

    def eof_received(self) -> bool:
        """Called when the other end calls write_eof() or equivalent.

        If this returns a false value (including None), the transport
        will close itself.  If it returns a true value, closing the
        transport is up to the protocol.
        """
        logger.debug(f"{self}: EOF received; closing connection")
        self.close()
        return True

class JvcProjectorEmulator:
    password: Optional[str]
    bind_addr: str
    port: int
    sessions: Dict[int, JvcProjectorEmulatorSession]
    next_session_id: int = 0
    requests: asyncio.Queue[Optional[Tuple[JvcProjectorEmulatorSession, Packet]]]

    def __init__(
            self,
            password: Optional[str] = None,
            bind_addr: Optional[str] = None,
            port: int = DEFAULT_PORT,
          ):
        self.password = password
        self.bind_addr = '0.0.0.0' if bind_addr is None else bind_addr
        self.port = port
        self.sessions = {}
        self.requests = asyncio.Queue()

    def alloc_session_id(self, session: JvcProjectorEmulatorSession) -> int:
        result = self.next_session_id
        self.next_session_id += 1
        self.sessions[result] = session
        return result

    def free_session_id(self, session_id: int) -> None:
        self.sessions.pop(session_id, None)

    def on_packet_received(self, session: JvcProjectorEmulatorSession, packet: Packet) -> None:
        """Called when a packet is received from a session."""
        self.requests.put_nowait((session, packet))

    async def handle_request_packet(
            self,
            session: JvcProjectorEmulatorSession,
            packet: Packet
          ) -> Optional[List[Packet]]:
        """Handle a single request packet, and return response packets.

        If an exception is raised, the session is closed.
        """
        if not packet.is_valid:
            raise JvcProjectorError(f"Invalid request packet: {packet}")
        if not packet.is_command:
            raise JvcProjectorError(f"Invalid command packet type {packet.packet_type}: {packet}")

        raise NotImplementedError()

    async def handle_requests(self) -> None:
        """Handle requests from sessions."""
        while True:
            session_and_packet = await self.requests.get()
            try:
                if session_and_packet is None:
                    self.requests.task_done()
                    logger.debug("Emulator handler: Received EOF; exiting")
                    break
                session, packet = session_and_packet
                try:
                    logger.debug(f"{session}: Emulator handler: received packet: {packet}")
                    response_packets = await self.handle_request_packet(session, packet)
                    if not response_packets is None:
                        for response_packet in response_packets:
                            logger.debug(f"{session}: Emulator handler: Sending response packet: {response_packet}")
                            session.write(response_packet.raw_data)
                except asyncio.CancelledError as e:
                    logger.debug(f"{session}: Handler task cancelled; exiting")
                    break
                except Exception as e:
                    logger.exception(f"{session}: Handler task: Exception while handling request; killing session: {e}")
                    break
            finally:
                self.requests.task_done()

    async def run(self) -> None:
        """Run the emulator.

        This method does not return until the emulator is stopped.
        """
        handler_task = asyncio.create_task(self.handle_requests())
        try:
            loop = asyncio.get_running_loop()
            server = await loop.create_server(
                lambda: JvcProjectorEmulatorSession(self),
                host=self.bind_addr,
                port=self.port)
            logger.debug(f"Emulator: Listening on {self.bind_addr}:{self.port}")
            async with server:
                await server.serve_forever()
        finally:
            logger.debug("Emulator: Server loop terminated; stopping handler task")
            await self.requests.put(None)
            await handler_task
            logger.debug("Emulator: Handler task stopped")
