# Copyright (c) 2023 Samuel J. McKelvie
#
# MIT License - See LICENSE file accompanying this package.
#

"""
A REST FastAPI server that controls a JVC projector.
"""
from .app import proj_api, get_projector_client, get_projector_config, get_raw_config
