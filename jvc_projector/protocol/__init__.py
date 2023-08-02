# Copyright (c) 2023 Samuel J. McKelvie
#
# MIT License - See LICENSE file accompanying this package.
#

"""
Low-level protocol definitions for JVC projectors.

Refer to https://support.jvc.com/consumer/support/documents/DILAremoteControlGuide.pdf
for the official protocol documentation.
"""

from .constants import (
    PacketType,
    PACKET_MAGIC,
    END_OF_PACKET,
    END_OF_PACKET_BYTES,
    MAX_PACKET_LENGTH,
    MIN_PACKET_LENGTH,
  )

from .packet import (
    Packet,
  )

from .response import (
    JvcResponse,
    OneByteReturnCodeResponse
  )

from .command import (
    JvcCommand,
  )

from .handshake import (
    PJ_OK,
    PJREQ,
    PJACK,
    PJNAK,
)
