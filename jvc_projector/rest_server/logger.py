#!/usr/bin/env python3

# Copyright (c) 2023 Samuel J. McKelvie
#
# MIT License - See LICENSE file accompanying this package.
#

"""
A REST FastAPI server that controls a JVC projector.
"""

from __future__ import annotations

import logging

logger = logging.getLogger('jvc_projector.rest_server')
