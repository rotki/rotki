"""Main rotki server using FastAPI

This is the async replacement for the Flask/WSGI server.
"""
import logging
import os
import signal
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from rotkehlchen.api.server import RotkiASGIServer
from rotkehlchen.args import app_args
from rotkehlchen.logging import TRACE, RotkehlchenLogsAdapter, add_logging_level, configure_logging
from rotkehlchen.rotkehlchen import Rotkehlchen

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class RotkehlchenServer:
    """Main server that starts the FastAPI application"""
    
    def __init__(self) -> None:
        """Initializes the backend server
        May raise:
        - SystemPermissionError due to the given args containing a datadir
        that does not have the correct permissions
        """
        arg_parser = app_args(
            prog='rotki',
            description=(
                'rotki, the portfolio tracker and accounting tool that respects your privacy'
            ),
        )
        self.args = arg_parser.parse_args()
        add_logging_level('TRACE', TRACE)
        configure_logging(self.args)
        
        # Initialize Rotkehlchen instance
        self.rotkehlchen = Rotkehlchen(self.args)
        
        # Parse CORS domains
        if ',' in self.args.api_cors:
            self.cors_domains = [str(domain) for domain in self.args.api_cors.split(',')]
        else:
            self.cors_domains = [str(self.args.api_cors)]
            
        # Create ASGI server
        self.asgi_server = RotkiASGIServer(
            rotkehlchen=self.rotkehlchen,
            cors_domain_list=self.cors_domains,
        )
        
    def main(self) -> None:
        """Start the FastAPI server"""
        log.info(
            f'rotki v{self.rotkehlchen.get_version()} starting '
            f'on host {self.args.api_host} and port {self.args.api_port}'
        )
        
        # Configure uvicorn
        config = uvicorn.Config(
            app=self.asgi_server.app,
            host=self.args.api_host,
            port=self.args.api_port,
            log_level="info" if __debug__ else "warning",
            access_log=__debug__,
        )
        
        # Run server
        server = uvicorn.Server(config)
        server.run()
        
    async def async_main(self) -> None:
        """Async version of main - for future use"""
        log.info(
            f'rotki v{self.rotkehlchen.get_version()} starting '
            f'on host {self.args.api_host} and port {self.args.api_port}'
        )
        
        # Configure uvicorn
        config = uvicorn.Config(
            app=self.asgi_server.app,
            host=self.args.api_host,
            port=self.args.api_port,
            log_level="info" if __debug__ else "warning",
            access_log=__debug__,
        )
        
        # Run server
        server = uvicorn.Server(config)
        await server.serve()
        
    def shutdown(self) -> None:
        """Shutdown the server"""
        log.debug('Shutdown initiated')
        # TODO: Implement graceful shutdown for uvicorn