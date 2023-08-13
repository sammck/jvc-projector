#!/usr/bin/env python3

# Copyright (c) 2023 Samuel J. McKelvie
#
# MIT License - See LICENSE file accompanying this package.
#

"""
A REST FastAPI server that controls a JVC projector.
"""

from __future__ import annotations

from fastapi import FastAPI

import time
import os
import sys
import json
import asyncio

from signal import SIGINT, SIGTERM
from contextlib import asynccontextmanager

from .logger import logger
from ..internal_types import *
from .. import (
    __version__ as pkg_version,
    DEFAULT_PORT,
    JvcProjectorClient,
    JvcCommand,
    JvcResponse,
    JvcModel,
    models,
    jvc_projector_connect,
    JvcProjectorClientConfig,
    full_class_name
  )

from .api import router as api_router

@asynccontextmanager
async def fastapi_lifetime(app: FastAPI) -> None:
    """
    A context manager that initializes and cleans up for FastAPI.
    """

    try:
        logger.info("Projector REST server starting up--initializing...")
        config_file = os.environ.get("JVC_PROJECTOR_CONFIG", None)
        if config_file is None:
            if os.path.exists("jvc_projector_config.json"):
                config_file = "jvc_projector_config.json"
        if config_file is None:
            raw_config: JsonableDict = {}
        else:
            with open(config_file, "r") as f:
                raw_config: JsonableDict = json.load(f)
        app.state.raw_config = raw_config
        jvc_config = JvcProjectorClientConfig.from_jsonable(raw_config)
        app.state.jvc_config = jvc_config
        app.state.launch_time = time.monotonic()
        jvc_client = await jvc_projector_connect(config=jvc_config)
        app.state.jvc_client = jvc_client
        logger.info(f"Serving API for projector at {jvc_client}...")

        logger.info("Projector REST server initialization done; starting server...")
        yield
    finally:
        logger.info("Projector REST server shutting down--cleaning up...")

proj_api = FastAPI(lifespan=fastapi_lifetime)
proj_api.include_router(api_router)

def get_projector_client() -> JvcProjectorClient:
    return proj_api.state.jvc_client

def get_projector_config() -> JvcProjectorClientConfig:
    return proj_api.state.jvc_config

def get_raw_config() -> JsonableDict:
    return proj_api.state.raw_config

