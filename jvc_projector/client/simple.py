# Copyright (c) 2023 Samuel J. McKelvie
#
# MIT License - See LICENSE file accompanying this package.
#

"""
JVC Projector simple multi-protocol client connection API.

Provides a simple API for connection to a projector over any transport.
"""

from __future__ import annotations

import os
import asyncio
from asyncio import Future
from abc import ABC, abstractmethod

from ..internal_types import *
from ..exceptions import JvcProjectorError
from ..constants import DEFAULT_TIMEOUT, DEFAULT_PORT
from ..pkg_logging import logger
from ..protocol import Packet, PJ_OK, PJREQ, PJACK, PJNAK
from .connector import JvcProjectorConnector
from .client_transport import (
    JvcProjectorClientTransport,
    ResponsePackets
  )

from .tcp_connector import TcpJvcProjectorConnector
from .client_config import JvcProjectorClientConfig
from .client_impl import JvcProjectorClient

from .general_connector import GeneralJvcProjectorConnector

async def jvc_projector_transport_connect(
        host: Optional[str]=None,
        password: Optional[str]=None,
        config: Optional[JvcProjectorClientConfig]=None
      ) -> JvcProjectorClientTransport:
    """Create and initialize (including handshake and authentication)
       a transport for a JVC projector from a configuration.

    Args:
        host: The hostname or IPV4 address of the projector.
                may optionally be prefixed with "tcp://".
                May be suffixed with ":<port>" to specify a
                non-default port, which will override the port argument.
                May be "sddp://" or "sddp://<host>" to use
                SSDP to discover the projector.
                If None, the host will be taken from the
                JVC_PROJECTOR_HOST environment variable.
        password:
                The password to use to authenticate with the projector.
                If None, the password will be taken from the
                config.
        config: A JvcProjectorClientConfig object that specifies
                the default host, port, and password to use.
                If None, a default config will be created.
    """
    connector = GeneralJvcProjectorConnector(
        host=host,
        password=password,
        config=config
      )
    transport = await connector.connect()
    return transport

async def jvc_projector_connect(
        host: Optional[str]=None,
        password: Optional[str]=None,
        config: Optional[JvcProjectorClientConfig]=None
      ) -> JvcProjectorClient:
    """Create and initialize (including handshake and authentication)
       a JVC projector client from a configuration.

    Args:
        host: The hostname or IPV4 address of the projector.
                may optionally be prefixed with "tcp://".
                May be suffixed with ":<port>" to specify a
                non-default port, which will override the port argument.
                May be "sddp://" or "sddp://<host>" to use
                SSDP to discover the projector.
                If None, the host will be taken from the
                JVC_PROJECTOR_HOST environment variable.
        password:
                The password to use to authenticate with the projector.
                If None, the password will be taken from the
                config.
        config: A JvcProjectorClientConfig object that specifies
                the default host, port, and password, etc. to use.
                If None, a default config will be created.
    """
    config = JvcProjectorClientConfig(
        default_host=host,
        password=password,
        base_config=config
      )
    transport = await jvc_projector_transport_connect(
        config=config
      )
    try:
        client = JvcProjectorClient(
            transport=transport,
            config=config,
        )
    except BaseException:
        await transport.aclose()
        raise

    return client
