"""
Module to start an HTTPS server with SSL/TLS encryption in Python.

This module provides functionality to start an HTTPS server that serves files
from a specified directory and runs the server in a separate thread. It uses
SSL/TLS for secure communication and custom request handling.

Classes:
    AuthHTTPRequestHandler: Custom request handler for authentication.

Functions:
    start_https_server(directory, port=8000, server_name="Server"): Starts an
    HTTPS server.
    run_https_server_in_thread(directory, port, server_name="Server"): Runs
    the HTTPS server in a separate thread.

Usage:
    import your_module_name

    # Start server directly
    your_module_name.start_https_server("/path/to/directory", port=8443,
    server_name="MyServer")

    # Run server in a separate thread
    your_module_name.run_https_server_in_thread("/path/to/directory",
    port=8443, server_name="MyServer")
"""

import os
import threading
from http.server import HTTPServer
import ssl
from src.auth.auth import AuthHTTPRequestHandler
from src.logs.logger import LOGGER
from src.config.config import IP_SERVER, CERT_FILE, KEY_FILE


def start_https_server(directory, port=8000, server_name="Server"):
    """
    Starts an HTTPS server serving files from the specified directory.

    This function changes the current working directory to the given directory,
    sets up an HTTP server with SSL/TLS encryption, and serves files using
    the custom `AuthHTTPRequestHandler` class.

    Args:
        directory (str): The directory from which to serve files.
        port (int, optional): The port number on which the server listens. Defaults to 8000. # noqa
        server_name (str, optional): The name of the server used in logging. Defaults to "Server".

    Returns:
        None
    """
    os.chdir(directory)
    handler = AuthHTTPRequestHandler
    httpd = HTTPServer((IP_SERVER, int(port)), handler)

    # SSL/TLS configuration using SSLContext
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)

    httpd.socket = context.wrap_socket(httpd.socket, server_side=True)

    LOGGER.info("%s serving HTTPS on %s in port %s from directory: %s",
                server_name, IP_SERVER, port, directory)
    httpd.serve_forever()


def run_https_server_in_thread(directory, port, server_name="Server"):
    """
    Runs the HTTPS server in a separate thread.

    This function starts the HTTPS server in a new thread, allowing it to run
    concurrently with other code.

    Args:
        directory (str): The directory from which to serve files.
        port (int): The port number on which the server listens.
        server_name (str, optional): The name of the server used in logging.
        Defaults to "Server".

    Returns:
        None
    """
    server_thread = threading.Thread(target=start_https_server, args=(
        directory, port, server_name), daemon=True)
    server_thread.start()
