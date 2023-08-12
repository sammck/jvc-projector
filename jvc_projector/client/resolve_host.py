# Copyright (c) 2023 Samuel J. McKelvie
#
# MIT License - See LICENSE file accompanying this package.
#

"""
JVC Projector host IP/Port resolver.

Provides a method that can resolve various host pathnames, environment variables,
SDDP discovery, etc. into a projector IP address and port.
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

from .client_transport import (
    JvcProjectorClientTransport,
    ResponsePackets
  )

import sddp_discovery_protocol as sddp
from sddp_discovery_protocol import SddpClient, SddpResponseInfo

async def resolve_projector_tcp_host(
        host: Optional[str]=None,
        default_port: Optional[int]=None,
      ) -> Tuple[str, int, Optional[SddpResponseInfo]]:
    """Resolves a projector host string into a hostname and port.

        Args:
            host: The hostname or IPV4 address of the projector.
                    may optionally be prefixed with "tcp://".
                    May be suffixed with ":<port>" to specify a
                    non-default port, which will override the default_port argument.
                    May be "sddp://" or "sddp://<sddp-hostname>" to use
                    SSDP to discover the projector.
                    If None, the host will be taken from the
                    JVC_PROJECTOR_HOST environment variable.
            default_port: The default TCP/IP port number to use. If None, the port
                    will be taken from the JVC_PROJECTOR_PORT. If that
                    environment variable is not found, the default JVC
                    projector port (20554) will be used.

        Returns:
            A tuple of (hostname: str, port: int, sddp_response_info: Optional[SddpResponseInfo]) where:
                hostname: The resolved IP address.
                port:     The resolved port number.
                sddp_response_info:
                          The SDDP response info, if SDDP was used to
                          discover the projector. None otherwise.
    """
    if host is None or host == '':
        host = os.environ.get('JVC_PROJECTOR_HOST')
        if host is None or host == '':
            host = "sddp://" # Use SDDP discovery

    if default_port is None or default_port <= 0:
        default_port_str = os.environ.get('JVC_PROJECTOR_PORT')
        if default_port_str is None or default_port_str == '':
            default_port = DEFAULT_PORT
        else:
            default_port = int(default_port_str)

    result_host: Optional[str] = None
    port: Optional[int] = None
    sddp_response_info: Optional[sddp.SddpResponseInfo] = None

    if host.startswith('sddp://'):
        sddp_host: Optional[str] = host[7:]
        if sddp_host == '':
            sddp_host = None
        filter_headers: Dict[str, str] ={
            "Manufacturer": "JVCKENWOOD",
            "Primary-Proxy": "projector",
          }

        async with SddpClient(include_loopback=True) as sddp_client:
            async with sddp_client.search(filter_headers=filter_headers) as search_request:
                async for response in search_request:
                    if sddp_host is None or response.datagram.hdr_host == sddp_host:
                        sddp_response_info = response
                        break
                else:
                    raise JvcProjectorError("SDDP discovery failed to find a projector")

        assert sddp_response_info is not None
        result_host = sddp_response_info.src_addr[0]
        optional_port = sddp_response_info.datagram.headers.get('Port')
        if optional_port is None:
            port = default_port
        else:
            port = int(optional_port)
    else:
        if host.startswith('tcp://'):
            host = host[6:]
        if ':' in host:
            host, port_str = host.rsplit(':', 1)
            port = int(port_str)
        else:
            port = default_port
        result_host = host

    return (result_host, port, sddp_response_info)
