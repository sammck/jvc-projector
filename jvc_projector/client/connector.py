# Copyright (c) 2023 Samuel J. McKelvie
#
# MIT License - See LICENSE file accompanying this package.
#

"""
JVC Projector client abstract transport connectorinterface.

Provides a low-level abstract interface for objects that can create
trasport connections (including handshake and authentication)
to a JVC projector.
This abstraction allows for the implementation of proxies and alternate network
transports (e.g., HTTP).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..internal_types import *
from .client_transport import JvcProjectorClientTransport
from .client_config import JvcProjectorClientConfig

class JvcProjectorConnector(ABC):
    """Abstract base class for JVC Projector client transport connectors."""

    @abstractmethod
    async def connect(self) -> JvcProjectorClientTransport:
        """Create and initialize (including handshake and authentication)
           a client transport for the projector associated with this
           connector.

        Must be implemented by subclasses.
        """
        raise NotImplementedError()
