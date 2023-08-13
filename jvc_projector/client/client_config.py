# Copyright (c) 2023 Samuel J. McKelvie
#
# MIT License - See LICENSE file accompanying this package.
#

"""
JVC Projector client configuration.

Provides general config object for a JvcProjectorClientTransport over
supported transport protocols.
"""

from __future__ import annotations

import os

from ..internal_types import *
from ..exceptions import JvcProjectorError
from ..constants import (
    DEFAULT_TIMEOUT,
    DEFAULT_PORT,
    STABLE_POWER_TIMEOUT,
    IDLE_DISCONNECT_TIMEOUT,
  )
from ..pkg_logging import logger
from ..protocol import JvcModel, models

class JvcProjectorClientConfig:
    """JVC Projector client configuration."""
    default_host: Optional[str]
    default_port: Optional[int]
    password: Optional[str]
    timeout_secs: float
    model: Optional[JvcModel]
    stable_power_timeout_secs: float
    idle_disconnect_secs: float
    auto_reconnect: bool

    def __init__(
            self,
            default_host: Optional[str]=None,
            password: Optional[str]=None,
            *,
            default_port: Optional[int]=None,
            timeout_secs: Optional[float] = None,
            model: Optional[Union[JvcModel, str]]=None,
            stable_power_timeout_secs: Optional[float] = None,
            idle_disconnect_secs: Optional[float] = None,
            auto_reconnect: Optional[bool] = None,
            base_config: Optional[JvcProjectorClientConfig]=None
          ) -> None:
        """Creates a configuration for a JVC Projector client.

           Args:
             default_host: The default hostname or IPV4 address of the projector.
                   may optionally be prefixed with "tcp://".
                   May be suffixed with ":<port>" to specify a
                   non-default port, which will override the default_port argument.
                   May be "sddp://" or "sddp://<host>" to use
                   SSDP to discover the projector.
                   If None, the default host will be taken from the
                     JVC_PROJECTOR_HOST environment variable.
             default_port: For TCP/IP transports, the default TCP/IP port number to use.
                    If None, the default port will be taken from the JVC_PROJECTOR_PORT.
                    If that environment variable is not found, the default JVC
                    projector port (20554) will be used.
             password:
                   The projector password. If None, the password
                   will be taken from the JVC_PROJECTOR_PASSWORD
                   environment variable. If an empty string or the
                   environment variable is not found, no password
                   will be used.
             timeout_secs:
                   The timeout for all client operations, in seconds.
                   If None, the timeout will be taken from the
                   JVC_PROJECTOR_TIMEOUT environment variable.
                   If the environment variable is not found, the
                   default timeout will be used.
             idle_disconnect_secs:
                   For auto-connect transports, the timeout for
                   disconnecting from the projector when idle, in seconds.
                   If None, IDLE_DISCONNECT_TIMOUT is used.
             model:
                   The projector model. If None, the model will be
                   inferred if necessary from SDDP, model_status.query,
                   etc.
             stable_power_timeout_secs:
                   The timeout for the projector to reach a stable power state
                   from WARMING or COOLING, in seconds. If None, a default
                   of 30 seconds is used.

             auto_reconnect:
                   For TCP transports, if True, the client transport will
                   automatically be wrapped in a transport that reconnects
                   on demand, and disconnects after an idle period. If None,
                   the base configuration is used. If no base configuration
                   is provided, the default is True.

             base_config:
                     An optional base configuration to use.
        """
        if base_config is None:
            self.init_from_defaults()
        else:
            self.init_from_base_config(base_config)

        if default_host is not None and default_host != '':
            self.default_host = default_host

        if default_port is not None and default_port > 0:
            self.default_port = default_port

        if password is not None:
            self.password = password

        if timeout_secs is not None:
            self.timeout_secs = timeout_secs

        if model is not None:
            if isinstance(model, str):
                if not model in models:
                    raise JvcProjectorError(f"Unknown JVC projector model: {model}")
                self.model = models[model]
            else:
                assert isinstance(model, JvcModel)
                self.model = model

        if stable_power_timeout_secs is not None:
            self.stable_power_timeout_secs = stable_power_timeout_secs

        if idle_disconnect_secs is not None:
            self.idle_disconnect_secs = idle_disconnect_secs

        if auto_reconnect is not None:
            self.auto_reconnect = auto_reconnect

    def init_from_defaults(self) -> None:
        """Initializes the configuration from defaults."""
        default_host: Optional[str] = os.environ.get('JVC_PROJECTOR_HOST')
        if default_host is None or default_host == '':
            default_host = "sddp://" # Use SDDP discovery by default
        self.default_host = default_host
        default_port_str = os.environ.get('JVC_PROJECTOR_PORT')
        default_port: Optional[int] = None
        if default_port_str is None or default_port_str == '':
            default_port = DEFAULT_PORT
        else:
            default_port = int(default_port_str)
        self.default_port = default_port
        password = os.environ.get('JVC_PROJECTOR_PASSWORD')
        if password == '':
            password = ''
        self.password = password
        self.timeout_secs = DEFAULT_TIMEOUT
        self.model = None
        self.stable_power_timeout_secs = STABLE_POWER_TIMEOUT
        self.idle_disconnect_secs = IDLE_DISCONNECT_TIMEOUT
        self.auto_reconnect = True

    def init_from_base_config(self, base_config: JvcProjectorClientConfig) -> None:
        """Initializes the configuration from a base configuration."""
        self.default_host = base_config.default_host
        self.default_port = base_config.default_port
        self.password = base_config.password
        self.timeout_secs = base_config.timeout_secs
        self.model = base_config.model
        self.stable_power_timeout_secs = base_config.stable_power_timeout_secs
        self.idle_disconnect_secs = base_config.idle_disconnect_secs
        self.auto_reconnect = base_config.auto_reconnect

    def __str__(self) -> str:
        return (
            f"JvcProjectorConfig("
            f"default_host={self.default_host}, "
            f"default_port={self.default_port}, "
            f"timeout_secs={self.timeout_secs!r})"
          )

    def __repr__(self) -> str:
        return str(self)
