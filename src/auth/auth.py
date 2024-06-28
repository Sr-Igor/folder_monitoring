"""
Module for a custom HTTP request handler with token-based authentication and CORS support. # noqa

This module defines the `AuthHTTPRequestHandler` class which extends `SimpleHTTPRequestHandler` 
to add basic Bearer token authentication for GET requests and CORS headers support.

Classes:
- AuthHTTPRequestHandler: Custom HTTP request handler that adds token-based authorization for GET 
  requests and handles CORS for cross-origin requests.

Methods:
- do_GET(self):
    Handles GET requests.
    Verifies the 'Authorization' header for a valid Bearer token.
    If the token is valid, processes the request accordingly.
    If the token is missing or invalid, sends a 401 Unauthorized response.
    Also handles specific download requests, checking permissions, and creating a ZIP file 
    from the requested files.

- log_message(self, format, *args):
    Overrides the `log_message` method to suppress logging of messages to the console.
    Args:
        format (str): The format string.
        *args: Additional arguments to format into the message.

- end_headers(self):
    Adds CORS headers and finalizes the HTTP response.
    Sends CORS headers to allow cross-origin requests from the specified domain.
    Calls the superclass's `end_headers` method to finalize the response.

- do_OPTIONS(self):
    Handles OPTIONS requests.
    Responds to OPTIONS requests with allowed HTTP methods and headers for CORS purposes.
    
Dependencies:
- os: Module for interacting with the operating system.
- requests: Library for making HTTP requests.
- SimpleHTTPRequestHandler: Base class for simple HTTP request handlers.
- parse_qs, urlparse: Functions for parsing URLs and query parameters.
- AUTH_TOKEN, WEB_URL: Authorization token and CORS URL from the configuration module.
- download_log, fetch_filtered_items: Database operation functions from `db_operations`.
- create_zip_from_files: Function for creating ZIP files from the `zip` module.

Environment:
- DOWNLOAD_URL: Download URL obtained from environment variables.

Author:
- The module is designed to add basic authentication and CORS support for an HTTP server.

Usage Example:
- This module is used as part of an HTTP server that requires token-based authentication to 
  access download resources. It can be integrated into a larger server to serve files 
  with appropriate authentication.
"""


import os
from http.server import SimpleHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

import requests

from src.config.config import AUTH_TOKEN, WEB_URL
from src.database.db_operations import (DatabaseError, download_log,  # noqa
                                        fetch_filtered_items)
from src.zip.zip import create_zip_from_files


class AuthHTTPRequestHandler(SimpleHTTPRequestHandler):
    """
    Custom HTTP request handler with basic token-based
    authorization and CORS support.

    This handler validates a Bearer token present in the
    authorization header for GET requests. It also sets CORS
    headers to allow requests from the specified domain.

    Methods:
        do_GET: Handles GET requests, checking the authorization
        header.
        log_message: Suppresses logging of messages to the
        console.
        end_headers: Adds CORS headers and finalizes the HTTP
        response.
        do_OPTIONS: Handles OPTIONS requests for CORS support.
    """

    def do_GET(self):
        """
        Handle GET requests.

        This method checks the 'Authorization' header for a
        valid Bearer token. If the token is valid, it calls
        the superclass's do_GET method to serve the request.
        If the token is missing or invalid, it sends a 401
        Unauthorized response.

        Returns:
            None
        """
        auth_header = self.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            self.send_response(401)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Missing or invalid Authorization header')
            return

        token = auth_header.split('Bearer ')[1]
        if token != AUTH_TOKEN:
            self.send_response(401)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Unauthorized')
            return

        parsed_path = urlparse(self.path)
        if parsed_path.path == '/download':

            query_params = parse_qs(parsed_path.query)
            if 'directory' not in query_params:
                self.send_response(400)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'Missing directory parameter')
                return

            file_paths = query_params['directory'][0].split(',')

            # Fazer verificação de permissão
            download_url = os.getenv('DOWNLOAD_URL')
            if not download_url:
                self.send_response(500)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write(
                    b'Missing DOWNLOAD_URL environment variable')
                return

            user_token = self.headers.get('x-user-token')

            headers = {'Authorization': f'Bearer {user_token}'}
            try:
                response = requests.get(
                    download_url, headers=headers, timeout=10)
                response.raise_for_status()

                filters = response.json().get('data')
                response_id = response.json().get('id')

                try:
                    results = fetch_filtered_items(file_paths, filters)

                    list_original = [item[0] for item in results]
                    list_preview = [item[2] for item in results]
                    list_of_ids = [item[1] for item in results]

                    mode = query_params['mode'][0]

                    list_of_files = list_original if mode == 'original' else list_preview  # noqa
                    list_not_found = [
                        item for item in file_paths if item not in list_of_ids]

                    if not list_of_files:
                        self.send_response(404)
                        self.send_header('Content-Type', 'text/plain')
                        self.end_headers()
                        self.wfile.write(b'No files found')
                        return

                    if list_not_found:
                        self.send_response(404)
                        self.send_header('Content-Type', 'text/plain')
                        self.end_headers()
                        self.wfile.write(f'Files not found: {
                                         list_not_found}'.encode('utf-8'))
                        return

                    zip_path = create_zip_from_files(list_of_files)
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/zip')
                    self.send_header(
                        'Content-Disposition', f'attachment; filename="{os.path.basename(zip_path)}"')  # noqa
                    self.end_headers()
                    with open(zip_path, 'rb') as file:
                        self.wfile.write(file.read())

                    os.remove(zip_path)

                    download_log(list_of_ids, response_id, mode)

                except DatabaseError as e:
                    self.send_response(500)
                    self.send_header('Content-Type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(f'Database error: {e}'.encode('utf-8'))
                    return

            except requests.RequestException as e:
                self.send_response(502)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write(f'Error fetching download: {
                    e}'.encode('utf-8'))
                return
        else:
            super().do_GET()

    def log_message(self, format, *args):  # pylint: disable=redefined-builtin
        """
        Override the default log_message to suppress logging.

        This method is used to suppress the logging of HTTP
        requests to the console.

        Args:
            format (str): The format string.
            *args: Additional arguments to format into the
            message.

        Returns:
            None
        """
        pass  # pylint: disable=unnecessary-pass

    def end_headers(self):
        """
        Send CORS headers and end the HTTP response.

        This method adds CORS headers to the response to allow
        cross-origin requests from the specified URL, and then
        calls the superclass's end_headers method to finalize
        the response.

        Returns:
            None
        """
        self.send_header('Access-Control-Allow-Origin', WEB_URL)
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Authorization')
        self.send_header('Access-Control-Allow-Headers', 'X-User-Token')
        super().end_headers()

    def do_OPTIONS(self):  # pylint: disable=invalid-name
        """
        Handle OPTIONS requests.

        This method responds to OPTIONS requests with the
        allowed HTTP methods and headers for CORS purposes.

        Returns:
            None
        """
        self.send_response(200)
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Authorization')
        self.end_headers()
