# Copyright (c) 2023 Samuel J. McKelvie
#
# MIT License - See LICENSE file accompanying this package.
#

from __future__ import annotations

from ..internal_types import *
from ..exceptions import JvcProjectorError
from .packet import Packet
from .response import JvcResponse
from ..pkg_logging import logger
from .command_meta import (
    CommandMeta,
    bytes_to_command_meta,
    name_to_command_meta,
  )

from .constants import (
    PacketType,
    PACKET_MAGIC,
    END_OF_PACKET_BYTES
  )
class JvcCommand:
    """A command to a JVC projector"""
    command_packet: Packet
    command_meta: CommandMeta

    def __init__(
            self,
            command_packet: Packet,
            command_meta: Optional[CommandMeta]=None,
          ):
        command_packet.validate()
        if not command_packet.packet_type in (PacketType.BASIC_COMMAND, PacketType.ADVANCED_COMMAND):
            raise JvcProjectorError(f"Invalid command packet type {command_packet.packet_type}: {command_packet}")
        if command_meta is None:
            command_metas = bytes_to_command_meta(command_packet.raw_data)
            if len(command_metas) == 0:
                raise JvcProjectorError(f"Unrecognized command packet: {command_packet}")
            if len(command_metas) > 1:
                logger.debug(f"Multiple command metas found for command packet; using first: {command_packet}")
            command_meta = command_metas[0]
        self.command_packet = command_packet
        self.command_meta = command_meta
        if not command_packet.raw_data.startswith(command_meta.packet_prefix):
            raise JvcProjectorError(f"Command packet does not match command meta prefix {command_meta.packet_prefix.hex(' ')}: {command_packet}")
        if not command_meta.payload_length is None:
            if command_packet.payload_length != command_meta.payload_length:
                raise JvcProjectorError(
                    f"Command packet payload length {command_packet.payload_length} does not match command meta payload length {command_meta.payload_length}: {command_packet}")

    @property
    def name(self) -> str:
        """Returns the name of the command"""
        return self.command_meta.name

    @property
    def raw_data(self) -> bytes:
        """Returns the raw data of the command"""
        return self.command_packet.raw_data

    @property
    def command_code(self) -> bytes:
        """Returns the command code of the command"""
        return self.command_packet.command_code

    @property
    def payload_length(self) -> int:
        """Returns length in bytes of the payload of the command"""
        return len(self.payload_data)

    @property
    def payload_data(self) -> bytes:
        """Returns the payload of the command"""
        return self.command_packet.packet_payload

    @property
    def packet_type(self) -> PacketType:
        """Returns the packet type of the command"""
        return self.command_packet.packet_type

    @property
    def is_advanced(self) -> bool:
        """Returns True iff the command is an advanced command"""
        return self.command_packet.is_advanced_command

    @property
    def response_payload_length(self) -> Optional[int]:
        """Fixed length of the payload of the advanced response, if known.
           0 for basic commands. None if the payload is variable in size."""
        return self.command_meta.response_payload_length

    @property
    def response_map(self) -> Optional[Dict[bytes, str]]:
        """Map of response payloads to friendly response strings.
           None if not an advanced command."""
        return self.command_meta.response_map

    @classmethod
    def create_from_meta(
            cls,
            command_meta: CommandMeta,
            payload: Optional[bytes]=None,
          ) -> Self:
        """Creates a basic or advanced JvcCommand from command metadata"""
        if payload is None:
            payload = b''
        raw_data = command_meta.packet_prefix + payload
        command_packet = Packet(raw_data)
        return cls(command_packet, command_meta)

    @classmethod
    def create_from_name(
            cls,
            command_name: str,
            payload: Optional[bytes]=None,
          ):
        """Creates a basic or advanced JvcCommand from command name"""
        command_meta = name_to_command_meta(command_name)
        return cls.create_from_meta(command_meta, payload=payload)

    def create_basic_response_packet(self) -> Packet:
        """Creates a basic response packet for the command"""
        raw_data = (
            bytes([PacketType.BASIC_RESPONSE.value]) +
            PACKET_MAGIC +
            self.command_code +
            END_OF_PACKET_BYTES
          )
        result = Packet(raw_data)
        return result

    def create_advanced_response_packet(self, payload: bytes) -> Packet:
        """Creates an advanced response packet for the command"""
        if not self.is_advanced:
            raise JvcProjectorError(f"Cannot create advanced response packet for basic command: {self}")
        if payload is None:
            payload = b''
        if self.response_payload_length is not None:
            if len(payload) != self.response_payload_length:
                raise JvcProjectorError(
                    f"Invalid response payload length {len(payload)}, expected {self.response_payload_length} for command : {payload.hex(' ')}")
        raw_data = (
            bytes([PacketType.ADVANCED_RESPONSE.value]) +
            PACKET_MAGIC +
            self.command_code +
            payload +
            END_OF_PACKET_BYTES
          )
        result = Packet(raw_data)
        return result

    def create_response(self, payload: Optional[bytes]=None) -> JvcResponse:
        """Creates a JvcResponse from the command"""
        if payload is None:
            payload = b''
        basic_response_packet = self.create_basic_response_packet()
        advanced_response_packet: Optional[Packet] = None
        if self.is_advanced:
            advanced_response_packet = self.create_advanced_response_packet(payload)
        elif len(payload) > 0:
            raise JvcProjectorError(f"Invalid response payload length {len(payload)} for basic command {self}: {payload.hex(' ')}")
        result = JvcResponse(self, basic_response_packet, advanced_response_packet)
        return result

    def __str__(self) -> str:
        return f"JvcCommand({self.name}: {self.command_packet})"

    def __repr__(self) -> str:
        return str(self)
