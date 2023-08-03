# Copyright (c) 2023 Samuel J. McKelvie
#
# MIT License - See LICENSE file accompanying this package.
#

from __future__ import annotations

from ..internal_types import *
from .packet import Packet, PacketType
from ..exceptions import JvcProjectorError
from .command_meta import CommandMeta

if TYPE_CHECKING:
    from .command import JvcCommand

class JvcResponse:
    """A response to a JVC command

    Raw command responses are either basic or advanced.

    For a command packet with a raw form
        21 89 01 <cmd_byte_0> <cmd_byte_1> <optional_cmd_payload> 0A

    Basic command response packets are of the form:

        06 89 01 <cmd_byte_0> <cmd_byte_1> 0A

    Advanced command responses consist of a basic command response packet followed
    by a response return code packet of the form:

        40 89 01 <cmd_byte_0> <cmd_byte_1> <return_code_payload> 0A

    """
    command: JvcCommand
    basic_response_packet: Packet
    advanced_response_packet: Optional[Packet]

    def __init__(self, command: JvcCommand, basic_response_packet: Packet, advanced_response_packet: Optional[Packet]=None):
        if not basic_response_packet.is_basic_response:
            raise JvcProjectorError(f"Basic response packet expected: {basic_response_packet}")
        if basic_response_packet.command_code != command.command_code:
            raise JvcProjectorError(f"Basic response packet command code {basic_response_packet.command_code.hex(' ')} does not match command {command}: {basic_response_packet}")
        if len(basic_response_packet.packet_payload) != 0:
            raise JvcProjectorError(f"Basic response packet payload expected to be empty, but got: {basic_response_packet}")
        if command.is_advanced:
            if advanced_response_packet is None:
                raise JvcProjectorError(f"Advanced command {command} requires advanced response packet, but got: {advanced_response_packet}")
            if not advanced_response_packet.is_advanced_response:
                raise JvcProjectorError(f"Advanced response packet expected, but got: {advanced_response_packet}")
            if advanced_response_packet.command_code != command.command_code:
                raise JvcProjectorError(f"Advanced response packet command code {advanced_response_packet.command_code.hex(' ')} does not match command {command}: {advanced_response_packet}")
            if not command.response_payload_length is None:
                if len(advanced_response_packet.packet_payload) != command.response_payload_length:
                    raise JvcProjectorError(f"Advanced response packet payload length {len(advanced_response_packet.packet_payload)} does not match command {command} expected response payload length {command.response_payload_length}: {advanced_response_packet}")
        else:
            if not advanced_response_packet is None:
                raise JvcProjectorError(f"Basic command {command} does not expect an advanced response packet")
        self.command = command
        self.basic_response_packet = basic_response_packet
        self.advanced_response_packet = advanced_response_packet
        self.post_init()

    def post_init(self) -> None:
        """Post-initialization hook, allows subclasses to perform additional initialization"""
        pass

    @property
    def name(self) -> str:
        return f"Response<{self.command.name}>"

    @property
    def command_meta(self) -> CommandMeta:
        return self.command.command_meta

    @property
    def response_map(self) -> Optional[Dict[bytes, str]]:
        """Returns a map of response payload to response strings, if any"""
        return self.command_meta.response_map

    def response_str(self) -> Optional[str]:
        """Returns a string representation of the response, if any"""
        result: Optional[str] = None
        if not self.response_map is None:
            result = self.response_map.get(self.payload, None)

        return result

    @property
    def raw_data(self) -> bytes:
        """Returns the raw data of the response. If the response is an advanced response,
           the payload of the advanced response packet is appended to the payload of the
           basic response packet"""
        data = self.basic_response_packet.raw_data
        if not self.advanced_response_packet is None:
            data = data[:] + self.advanced_response_packet.raw_data
        return data

    def __str__(self) -> str:
        return f"JvcResponse({self.command.name}: [{self.raw_data.hex(' ')}])"

    @property
    def is_advanced(self) -> bool:
        """Returns True iff the response is an advanced response"""
        return not self.advanced_response_packet is None

    @property
    def payload(self) -> bytes:
        """Returns the payload of the advanced response packet, if any"""
        return b'' if self.advanced_response_packet is None else self.advanced_response_packet.packet_payload

    def __repr__(self) -> str:
        return str(self)
