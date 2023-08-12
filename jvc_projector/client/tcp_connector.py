# Copyright (c) 2023 Samuel J. McKelvie
#
# MIT License - See LICENSE file accompanying this package.
#

"""
JVC Projector TCP/IP client connector.

Provides an connector for a JvcProjectorClientTransport over a TCP/IP
socket.
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
from .client_config import JvcProjectorClientConfig

from .tcp_client_transport import TcpJvcProjectorClientTransport

class TcpJvcProjectorConnector(JvcProjectorConnector):
    """JVC Projector TCP/IP client transport connector."""

    config: JvcProjectorClientConfig

    def __init__(
            self,
            host: Optional[str]=None,
            password: Optional[str]=None,
            port: Optional[int]=None,
            timeout_secs: Optional[float] = None,
            config: Optional[JvcProjectorClientConfig]=None,
          ) -> None:
        """Creates a connector that can create transports to
           a JVC Projector that is reachable over TCP/IP.

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
                      The projector password. If None, the password
                      will be taken from the JVC_PROJECTOR_PASSWORD
                      environment variable. If an empty string or the
                      environment variable is not found, no password
                      will be used.
                port: The default TCP/IP port number to use. If None, the port
                      will be taken from the JVC_PROJECTOR_PORT. If that
                      environment variable is not found, the default JVC
                      projector port (20554) will be used.
                timeout_secs: The default timeout for operations on the
                        transport. If not provided, DEFAULT_TIMEOUT (2 seconds)
                        is used.
                config: A JvcProjectorClientConfig object that specifies
                        the default host, port, password, etc to use.
                        If None, a default config will be created.
        """
        super().__init__()
        self.config = JvcProjectorClientConfig(
            default_host=host,
            default_port=port,
            timeout_secs=timeout_secs,
            password=password,
            base_config=config
          )
        host = self.config.default_host
        assert host is not None
        if '://' in host and not host.startswith('tcp://') and not host.startswith('sddp://'):
            raise JvcProjectorError(f"Invalid host protocol specifier for TCP transport: '{host}'")

    # @abstractmethod
    async def connect(self) -> JvcProjectorClientTransport:
        """Create and initialize (including handshake and authentication)
           a TCP/IP client transport for the projector associated with this
           connector.
        """

        transport = await TcpJvcProjectorClientTransport.create(
            self.config.default_host,
            password=self.config.password,
            port=self.config.default_port,
            timeout_secs=self.config.timeout_secs
          )
        return transport


    def __str__(self) -> str:
        return f"TcpJvcProjectorConnector(host='{self.config.default_host}', port={self.config.default_port})"

    def __repr__(self) -> str:
        return str(self)
