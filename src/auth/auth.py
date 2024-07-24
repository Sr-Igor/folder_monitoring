"""
Module to handle HTTP requests with token-based authorization and file
downloading.

This module defines a custom HTTP request handler, `AuthHTTPRequestHandler`,
which extends
`SimpleHTTPRequestHandler` to include token-based authorization, CORS support,
and file download capabilities.

Classes:
    AuthHTTPRequestHandler: Handles HTTP GET requests, providing secure file
                            downloads and CORS support.

Usage:
    from your_module_name import AuthHTTPRequestHandler

    # Use this handler with an HTTP server
    handler = AuthHTTPRequestHandler
"""

import os
from http.server import SimpleHTTPRequestHandler
from urllib.parse import parse_qs, urlparse, unquote
import requests
from src.config.config import AUTH_TOKEN, WEB_URL, DOWNLOAD_URL, LOG_URL, WINDOWS  # noqa
from src.database.db_operations import (
    DatabaseError, fetch_filtered_items)
from src.zip.zip import create_zip_from_files


class AuthHTTPRequestHandler(SimpleHTTPRequestHandler):
    """
    Custom HTTP request handler with basic token-based
    authorization and CORS support.

    This handler processes HTTP GET requests, checking for a valid
    authorization token and handling requests for file downloads.
    It also supports CORS for cross-origin resource sharing.
    """

    def do_GET(self):
        """
        Handle GET requests.

        This method checks for a valid 'Authorization' header and processes
        file download requests. It supports downloading files in ZIP
        format if requested, and logs download activity.

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

            if not DOWNLOAD_URL:
                self.send_response(500)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'Missing DOWNLOAD_URL environment variable')
                return

            if not LOG_URL:
                self.send_response(500)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'Missing LOG_URL environment variable')
                return

            user_token = self.headers.get('x-user-token')

            headers = {'Authorization': f'Bearer {user_token}'}
            try:
                response = requests.get(
                    DOWNLOAD_URL, headers=headers, timeout=10)
                response.raise_for_status()

                filters = response.json().get('data')

                try:
                    results = fetch_filtered_items(file_paths, filters)

                    list_original = [item[0] for item in results]
                    list_preview = [item[2] for item in results]
                    list_of_ids = [item[1] for item in results]

                    mode = query_params.get('mode', ['original'])[0]

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

                    client_id = query_params.get('client', [None])[0]
                    response = requests.put(
                        LOG_URL, headers=headers, timeout=10, json={'client_id': client_id, 'graphs': list_of_ids, 'mode': mode})  # noqa

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
            file_path = unquote(parsed_path.path)

            if (file_path[1:3] == ':/' or file_path[1:3] == ':\\') and WINDOWS:
                file_path = file_path.lstrip('/')
            else:
                if not os.path.isabs(file_path):
                    file_path = os.path.join(
                        os.getcwd(), file_path.lstrip('/'))

            if not os.path.exists(file_path):
                self.send_response(404)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'File not found or invalid path')
                return

            if not os.access(file_path, os.R_OK):
                self.send_response(403)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'Forbidden: Cannot read file')
                return

            self_path = file_path

            is_file = os.path.isfile(self_path)

            if is_file:
                with open(self_path, 'rb') as file:
                    self.send_response(200)
                    self.send_header(
                        'Content-Type', 'application/octet-stream')
                    self.send_header(
                        'Content-Disposition', f'attachment; filename="{os.path.basename(self_path)}"')  # noqa
                    self.end_headers()
                    self.wfile.write(file.read())
            else:
                super().do_GET()

    def end_headers(self):
        """
        Add CORS headers before sending response headers.

        This method adds headers for CORS (Cross-Origin Resource Sharing)
        support before ending the headers.

        Returns:
            None
        """
        self.send_header('Access-Control-Allow-Origin', WEB_URL)
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers',
                         'Authorization, X-User-Token')
        super().end_headers()

    def do_OPTIONS(self):  # pylint: disable=invalid-name
        """
        Handle OPTIONS requests for CORS preflight.

        This method responds to OPTIONS requests by setting the necessary
        headers for CORS preflight requests.

        Returns:
            None
        """
        self.send_response(200)
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers',
                         'Authorization, X-User-Token')
        self.end_headers()
