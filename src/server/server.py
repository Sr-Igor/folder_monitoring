"""
Server management module.

This module provides functions to start an HTTP server in a separate thread,
using the specified directory, port, and server name. It utilizes threading
for concurrent execution and HTTPServer for handling HTTP requests.

Dependencies:
    - os: Provides operating system functionalities.
    - threading: Supports threading capabilities for concurrent execution.
    - http.server.HTTPServer: Implements HTTP server functionality.
    - auth.AuthHTTPRequestHandler: Custom HTTP request handler with authentication. # noqa
    - db_logger.LOGGER: Logger object for logging server events.
    - config.IP_SERVER: IP address or hostname to bind the server.

Functions:
    start_http_server: Starts an HTTP server serving files from a specified directory.
    run_server_in_thread: Runs an HTTP server in a separate thread.
"""

import os
import threading
from http.server import HTTPServer
from src.auth.auth import AuthHTTPRequestHandler
from src.logs.logger import LOGGER
from src.config.config import IP_SERVER


def start_http_server(directory, port=8000, server_name="Server"):
    """
    Start an HTTP server serving files from a specified directory.

    Args:
        directory (str): Directory path from which to serve files.
        port (int, optional): Port number for the HTTP server. Defaults to 8000. # noqa
        server_name (str, optional): Name of the server. Defaults to "Server".

    Returns:
        None
    """
    os.chdir(directory)
    handler = AuthHTTPRequestHandler
    httpd = HTTPServer((IP_SERVER, int(port)), handler)
    LOGGER.info("%s serving HTTP on %s in port %s from directory: %s",
                server_name, IP_SERVER, port, directory)
    httpd.serve_forever()


def run_server_in_thread(directory, port, server_name="Server"):
    """
    Run an HTTP server in a separate thread.

    Args:
        directory (str): Directory path from which to serve files.
        port (int): Port number for the HTTP server.
        server_name (str, optional): Name of the server. Defaults to "Server".

    Returns:
        None
    """
    server_thread = threading.Thread(target=start_http_server, args=(
        directory, port, server_name), daemon=True)
    server_thread.start()
