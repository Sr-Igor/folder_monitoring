"""
Module to start an HTTP server in Python.

This module provides functionality to start an HTTP server that serves files
from a specified directory and runs the server in a separate thread. It uses
custom request handling for additional features.

Classes:
    AuthHTTPRequestHandler: Custom request handler for authentication.

Functions:
    start_http_server(directory, port=8000, server_name="Server"): Starts an
    HTTP server.
    run_http_server_in_thread(directory, port, server_name="Server"): Runs
    the HTTP server in a separate thread.

Usage:
    import your_module_name

    # Start server directly
    your_module_name.start_http_server("/path/to/directory", port=8000,
    server_name="MyServer")

    # Run server in a separate thread
    your_module_name.run_http_server_in_thread("/path/to/directory",
    port=8000, server_name="MyServer")
"""

import os
import threading
from http.server import HTTPServer
from src.auth.auth import AuthHTTPRequestHandler
from src.logs.logger import LOGGER
from src.config.config import IP_SERVER


def start_http_server(directory, port=8000, server_name="Server"):
    """
    Starts an HTTP server serving files from the specified directory.

    This function changes the current working directory to the given directory,
    sets up an HTTP server, and serves files using the custom
    `AuthHTTPRequestHandler` class.

    Args:
        directory (str): The directory from which to serve files.
        port (int, optional): The port number on which the server listens.
        Defaults to 8000. server_name (str, optional): The name of the server
        used in logging. Defaults to "Server".

    Returns:
        None
    """
    os.chdir(directory)
    handler = AuthHTTPRequestHandler
    httpd = HTTPServer((IP_SERVER, int(port)), handler)

    LOGGER.info("%s serving HTTP on %s in port %s from directory: %s",
                server_name, IP_SERVER, port, directory)
    httpd.serve_forever()


def run_http_server_in_thread(directory, port, server_name="Server"):
    """
    Runs the HTTP server in a separate thread.

    This function starts the HTTP server in a new thread, allowing it to run
    concurrently with other code.

    Args:
        directory (str): The directory from which to serve files.
        port (int): The port number on which the server listens.
        server_name (str, optional): The name of the server used in logging.
        Defaults to "Server".

    Returns:
        None
    """
    server_thread = threading.Thread(target=start_http_server, args=(
        directory, port, server_name), daemon=True)
    server_thread.start()
