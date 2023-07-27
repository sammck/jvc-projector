# Copyright (c) 2023 Samuel J. McKelvie
#
# MIT License - See LICENSE file accompanying this package.
#

"""Package jvc_projector provides  a command-line A tool and API for controlling
JVC projectors via their proprietary TCP/IP protocol.
"""

from .version import __version__

from .pkg_logging import logger

from .internal_types import Jsonable, JsonableDict

from .exceptions import JvcProjectorError

from .constants import DEFAULT_PORT, DEFAULT_TIMEOUT, STABLE_POWER_TIMEOUT

from .internal_types import Jsonable, JsonableDict
