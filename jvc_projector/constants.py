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

IDLE_DISCONNECT_TIMEOUT = 2.0
"""For autoconnect transports, the timeout for the client to disconnect after an idle period,
   in seconds."""

CONNECT_TIMEOUT = 15.0
"""The timeout for connecting to the projector over TCP/IP, in seconds."""

CONNECT_RETRY_INTERVAL = 1.0
"""The interval between connection attempts over TCP/IP, in seconds."""

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
