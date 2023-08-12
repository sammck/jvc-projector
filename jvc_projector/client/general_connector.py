# Copyright (c) 2023 Samuel J. McKelvie
#
# MIT License - See LICENSE file accompanying this package.
#

"""
JVC Projector multi-protocol client connector.

Provides general connector for a JvcProjectorClientTransport over
supported transport protocols.
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

class GeneralJvcProjectorConnector(JvcProjectorConnector):
    """General JVC Projector client transport connector."""
    config: JvcProjectorClientConfig
    child_connector: JvcProjectorConnector

    def __init__(
            self,
            host: Optional[str]=None,
            password: Optional[str]=None,
            config: Optional[JvcProjectorClientConfig]=None
          ) -> None:
        """Creates a connector that can create transports to
           a JVC Projector over any supported transport protocol.

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
        super().__init__()
        self.config = JvcProjectorClientConfig(
            default_host=host,
            password=password,
            base_config=config
        )
        host = self.config.default_host
        assert host is not None
        if not '://' in host or host.startswith('tcp://') or host.startswith('sddp://'):
            self.child_connector = TcpJvcProjectorConnector(
                config=self.config,
              )
        else:
            raise JvcProjectorError(
                f"Unsupported protocol in host specifier: {host}"
              )

    # @abstractmethod
    async def connect(self) -> JvcProjectorClientTransport:
        """Create and initialize (including handshake and authentication)
           a TCP/IP client transport for the projector associated with this
           connector.
        """
        transport = await self.child_connector.connect()
        return transport

    def __str__(self) -> str:
        return f"GeneralJvcProjectorConnector({self.child_connector})"

    def __repr__(self) -> str:
        return str(self)
