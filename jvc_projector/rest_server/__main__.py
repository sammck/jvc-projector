# Copyright (c) 2023 Samuel J. McKelvie
#
# MIT License - See LICENSE file accompanying this package.
#

"""
A REST FastAPI server that controls a JVC projector.
"""
import sys
import uvicorn
import logging
from dotenv import load_dotenv

def run() -> int:
    load_dotenv()

    logging.basicConfig(level=logging.DEBUG)

    from jvc_projector.rest_server.app import proj_api
    uvicorn.run(proj_api, log_config=None)
    return 0

if __name__ == "__main__":
    rc = run()
    sys.exit(rc)