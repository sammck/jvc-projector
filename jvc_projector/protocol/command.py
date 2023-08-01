# Copyright (c) 2023 Samuel J. McKelvie
#
# MIT License - See LICENSE file accompanying this package.
#

from __future__ import annotations

from ..internal_types import *
from ..exceptions import JvcProjectorError
from .packet import Packet, PacketType
from .response import JvcResponse
from ..pkg_logging import logger
class JvcCommand:
    """A command to a JVC projector"""
    name: str
    command_packet: Packet
    response_cls: type[JvcResponse]
    expected_payload_length: Optional[int]

    def __init__(
            self,
            name: str,
            command_packet: Packet,
            response_cls: type[JvcResponse]=JvcResponse,
            expected_payload_length: Optional[int]=None
          ):
        command_packet.validate()
        if not command_packet.packet_type in (PacketType.BASIC_COMMAND, PacketType.ADVANCED_COMMAND):
            raise JvcProjectorError(f"Cannot create JvcCommand from non-command packet: {command_packet}")
        self.name = name
        self.command_packet = command_packet
        self.response_cls = response_cls
        self.expected_payload_length = expected_payload_length

    @property
    def command_code(self) -> bytes:
        """Returns the command code of the command"""
        return self.command_packet.command_code

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

    @classmethod
    def create(
            cls,
            name: str,
            cmd_bytes: bytes,
            payload: Optional[bytes]=None,
            is_advanced: bool=False,
            response_cls: type[JvcResponse]=JvcResponse,
            expected_payload_length: Optional[int]=None
          ) -> JvcCommand:
        """Creates a basic or advanced JvcCommand"""
        packet_type = PacketType.ADVANCED_COMMAND if is_advanced else PacketType.BASIC_COMMAND
        command_packet = Packet.create(packet_type, cmd_bytes, payload)
        return cls(name, command_packet, response_cls=response_cls, expected_payload_length=expected_payload_length)

    @classmethod
    def create_basic(
            cls,
            name: str,
            cmd_bytes: bytes,
            payload: Optional[bytes]=None,
            response_cls: type[JvcResponse]=JvcResponse,
          ) -> JvcCommand:
        return cls.create(
                name,
                cmd_bytes,
                payload=payload,
                is_advanced=False,
                response_cls=response_cls
              )

    @classmethod
    def create_advanced(
            cls,
            name: str,
            cmd_bytes: bytes,
            payload: Optional[bytes]=None,
            response_cls: type[JvcResponse]=JvcResponse,
            expected_payload_length: Optional[int]=None
          ) -> JvcCommand:
        return cls.create(
                name,
                cmd_bytes,
                payload=payload,
                is_advanced=True,
                response_cls=response_cls,
                expected_payload_length=expected_payload_length
              )


    def create_response(self, basic_response_packet: Packet, advanced_response_packet: Optional[Packet]=None) -> JvcResponse:
        response =  self.response_cls(self, basic_response_packet, advanced_response_packet=advanced_response_packet)
        return response

    def __str__(self) -> str:
        return f"JvcCommand({self.name}: {self.command_packet})"

    def __repr__(self) -> str:
        return str(self)

class BasicCommand(JvcCommand):
    """A JVC command that returns a basic response"""

    def __init__(self, name: str, command_code: bytes, payload: Optional[bytes]=None, response_cls: type[JvcResponse]=JvcResponse):
        command_packet = Packet.create(PacketType.BASIC_COMMAND, command_code, payload)
        super().__init__(name, command_packet, response_cls=response_cls)

class AdvancedCommand(JvcCommand):
    """A JVC command that returns a basic response"""

    def __init__(
            self,
            name: str,
            command_code: bytes,
            payload: Optional[bytes]=None,
            response_cls: type[JvcResponse]=JvcResponse,
            expected_payload_length: Optional[int]=None
          ):
        command_packet = Packet.create(PacketType.ADVANCED_COMMAND, command_code, payload)
        super().__init__(name, command_packet, response_cls=response_cls, expected_payload_length=expected_payload_length)

