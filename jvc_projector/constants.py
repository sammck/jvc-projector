# Copyright (c) 2023 Samuel J. McKelvie
#
# MIT License - See LICENSE file accompanying this package.
#

"""Constants used by jvc_projector"""

DEFAULT_PORT = 20554
"""The listen port number used by the projector for TCP/IP control."""

DEFAULT_TIMEOUT = 2.0
"""The default timeout for all TCP/IP control operations, in seconds."""

STABLE_POWER_TIMEOUT = 60.0
"""The timeout for the projector to reach a stable power state from WARMING or COOLING, in seconds."""

# Initial connection handshake:
#   Projector: "PJ_OK"
#   Client: "PJREQ", if there is no password, or f"PJREQ_{password}" if there is a password
#   Projector: "PJACK" if the password is correct, or "PJNAK" if the password is incorrect
#   <Normal command/response session begins>

PJ_OK = b"PJ_OK"
"""Sent by the projector immediately on connecting. Note there is no terminating newline"""

PJREQ = b"PJREQ"
"""Sent to the projector after receiving PJ_OK, to request authentication.
   If a password is set, then f"_{password}" is appended to the byte string. Note
   that there is no terminating newline."""

PJACK = b"PJACK"
"""Sent by the projector in response to a successful authentication. Note there is no terminating newline."""

# Protocol packets:
#
#   All packets sent to or received from the projector are of the form:
#       <packet_type_byte> 89 01 <two_byte_command_code> <packet_payload> 0A
#
#   The 0A byte is a newline character, and is the terminating byte for all packets. It is
#   never present in any of the other portions of a packet.
#

PACKET_MAGIC = b"\x89\x01"
"""The magic bytes that follow the packet type in all packets sent to or received from the projector."""

END_OF_PACKET = 0x0a
"""The terminating byte for all packets sent to or received from the projector."""

MAX_PACKET_LENGTH = 30
"""The maximum length of a packet sent to or received from the projector, in bytes."""

MIN_PACKET_LENGTH = 6
"""The minimum length of a packet sent to or received from the projector, in bytes."""
