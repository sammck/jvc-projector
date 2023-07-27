#!/usr/bin/env python3

# Copyright (c) 2023 Samuel J. McKelvie
#
# MIT License - See LICENSE file accompanying this package.
#

from __future__ import annotations

import sys
import argparse
import json
import base64
import asyncio
import logging
from signal import SIGINT, SIGTERM

from jvc_projector.internal_types import *

from jvc_projector import (
    __version__ as pkg_version,
    SddpClient,
    SddpSearchRequest,
    SddpResponseInfo,
  )


class CmdExitError(RuntimeError):
    exit_code: int

    def __init__(self, exit_code: int, msg: Optional[str]=None):
        if msg is None:
            msg = f"Command exited with return code {exit_code}"
        super().__init__(msg)
        self.exit_code = exit_code

class ArgparseExitError(CmdExitError):
    pass

class NoExitArgumentParser(argparse.ArgumentParser):
    def exit(self, status=0, message=None):
        if message:
            self._print_message(message, sys.stderr)
        raise ArgparseExitError(status, message)

class CommandHandler:
    _argv: Optional[Sequence[str]]
    _parser: argparse.ArgumentParser
    _args: argparse.Namespace
    _provide_traceback: bool = True

    def __init__(self, argv: Optional[Sequence[str]]=None):
        self._argv = argv

    async def cmd_bare(self) -> int:
        print("A command is required", file=sys.stderr)
        return 1

    async def discover_projector(self, bind_addresses: Optional[List[str]]=None) -> Optional[SddpResponseInfo]:
        if not bind_addresses is None and len(bind_addresses) == 0:
            bind_addresses = None
        filter_headers: Dict[str, Union[str, int]] ={
            "Manufacturer": "JVCKENWOOD",
            "Primary-Proxy": "projector",
          }

        async with SddpClient(bind_addresses=bind_addresses) as client:
            async with SddpSearchRequest(
                    client,
                    filter_headers=filter_headers,
              ) as search_request:
                async for info in search_request.iter_responses():
                    return info
        return None

    async def cmd_find_ip(self) -> int:
        proj_info = await self.discover_projector(self._args.bind_addresses)
        if proj_info is None:
            raise CmdExitError(1, "No projector found")
        proj_ip = proj_info.src_addr[0]
        print(proj_ip)
        return 0

    async def cmd_version(self) -> int:
        print(pkg_version)
        return 0

    async def arun(self) -> int:
        """Run the sddp command-line tool with provided arguments

        Args:
            argv (Optional[Sequence[str]], optional):
                A list of commandline arguments (NOT including the program as argv[0]!),
                or None to use sys.argv[1:]. Defaults to None.

        Returns:
            int: The exit code that would be returned if this were run as a standalone command.
        """
        import argparse

        parser = argparse.ArgumentParser(description="Control a JVC projector.")


        # ======================= Main command

        self._parser = parser
        parser.add_argument('--traceback', "--tb", action='store_true', default=False,
                            help='Display detailed exception information')
        parser.add_argument('--log-level', dest='log_level', default='warning',
                            choices=['debug', 'info', 'warning', 'error', 'critical'],
                            help='''The logging level to use. Default: warning''')
        parser.set_defaults(func=self.cmd_bare)

        subparsers = parser.add_subparsers(
                            title='Commands',
                            description='Valid commands',
                            help='Additional help available with "<command-name> -h"')

        # ======================= find-ip

        parser_search = subparsers.add_parser('find-ip', description="Use the SDDP protocol to find the IP address of a JVC projector on the local subnet")
        parser_search.add_argument('-b', '--bind', dest="bind_addresses", action='append', default=[],
                            help='''The local unicast IP address to bind to on the desired subnet. May be repeated. Default: all local non-loopback unicast addresses.''')
        parser_search.set_defaults(func=self.cmd_find_ip)

        # ======================= version

        parser_version = subparsers.add_parser('version',
                                description='''Display version information.''')
        parser_version.set_defaults(func=self.cmd_version)

        # =========================================================

        try:
            args = parser.parse_args(self._argv)
        except ArgparseExitError as ex:
            return ex.exit_code
        traceback: bool = args.traceback
        self._provide_traceback = traceback

        try:
            logging.basicConfig(
                level=logging.getLevelName(args.log_level.upper()),
            )
            self._args = args
            func: Callable[[], Awaitable[int]] = args.func
            logging.debug(f"Running command {func.__name__}, tb = {traceback}")
            rc = await func()
            logging.debug(f"Command {func.__name__} returned {rc}")
        except Exception as ex:
            if isinstance(ex, CmdExitError):
                rc = ex.exit_code
            else:
                rc = 1
            if rc != 0:
                if traceback:
                    raise
            print(f"sddp: error: {ex}", file=sys.stderr)
        except BaseException as ex:
            print(f"sddp: Unhandled exception: {ex}", file=sys.stderr)
            raise

        return rc

    def run(self) -> int:
        return asyncio.run(self.arun())

def run(argv: Optional[Sequence[str]]=None) -> int:
    try:
        rc = CommandHandler(argv).run()
    except CmdExitError as ex:
        rc = ex.exit_code
    return rc

async def arun(argv: Optional[Sequence[str]]=None) -> int:
    try:
        rc = await CommandHandler(argv).arun()
    except CmdExitError as ex:
        rc = ex.exit_code
    return rc

# allow running with "python3 -m", or as a standalone script
if __name__ == "__main__":
    sys.exit(run())

'''
    parser = argparse.ArgumentParser()

    parser.add_argument("--port", default=20554, type=int,
        help="JVC projector port number to connect to. Default: 20554")
    parser.add_argument("-t", "--timeout", default=2.0, type=float,
        help="Timeout for network operations (seconds). Default: 2.0")
    parser.add_argument("-l", "--loglevel", default="ERROR",
        help="Logging level. Default: ERROR.",
        choices=["ERROR", "WARNING", "INFO", "DEBUG"])
    parser.add_argument("-p", "--password", default=None,
        help="Password to use when connecting to newer JVC hosts (e.g., DLA-NZ8). Default: use ENV var JVC_PROJECTOR_PASSWORD, or no password.")
    parser.add_argument("-H", "--host", help="JVC projector hostname or IP address. Default: Use env var JVC_PROJECTOR_HOST")
    parser.add_argument('command', nargs='*', default=[])

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.getLevelName(args.loglevel),
        format="%(asctime)s %(levelname)s %(filename)s:%(lineno)d] %(message)s",
        datefmt="%F %H:%M:%S")

    password: Optional[str] = args.password
    if password is None:
        password = os.getenv("JVC_PROJECTOR_PASSWORD")
    if not password is None and password == '':
        password = None

    host: Optional[str] = args.host
    if host is None:
        host = os.getenv("JVC_PROJECTOR_HOST")
        if host is None:
            raise Exception("No projector host specified. Use --host or set env var JVC_PROJECTOR_HOST")

    port: int = args.port
    timeout_secs: float = args.timeout
    cmd_args: List[str] = args.command


    projector = JvcProjector(
        host,
        port=port,
        password=password,
        timeout_secs=timeout_secs)


    async with await projector.connect() as session:
        await session.command(null_command)
        power_status = await session.cmd_power_status()
        print(f"Power status: {power_status}")
        model_name = await session.cmd_model_name()
        print(f"Model name: {model_name}")
        if len(cmd_args) > 0:
            await run_command(session, cmd_args)
            power_status = await session.cmd_power_status()
            print(f"Power status: {power_status}")

'''
