# Copyright (c) 2023 Samuel J. McKelvie
#
# MIT License - See LICENSE file accompanying this package.
#

from __future__ import annotations

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

PJNAK = b"PJNAK"
"""Sent by the projector in response to an unsuccessful authentication. Note there is no terminating newline."""
