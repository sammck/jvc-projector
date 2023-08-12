# Copyright (c) 2023 Samuel J. McKelvie
#
# MIT License - See LICENSE file accompanying this package.
#

"""
JVC Projector emulator.

Provides a simple emulation of a JVC projector on TCP/IP.
"""

from .resolve_host import resolve_projector_tcp_host
from .connector import JvcProjectorConnector
from .general_connector import GeneralJvcProjectorConnector
from .simple import jvc_projector_transport_connect, jvc_projector_connect
from .tcp_connector import TcpJvcProjectorConnector
from .client_config import JvcProjectorClientConfig
from .client_impl import (
    JvcProjectorClient,
  )
