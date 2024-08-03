"""
HTTP Server Module with Authorization

This module sets up an HTTP server to handle authenticated GET requests
for downloading files, creating zip archives, and serving files with
support for CORS and custom headers.

Classes:
    AuthHTTPRequestHandler: A request handler class with authorization and
    file handling.

Functions:
    handle_zip_creation(list_of_files, query_params): Creates a zip file from
    a list of files and notifies the client via WebSocket.
"""

import os
import threading
from http.server import SimpleHTTPRequestHandler
from urllib.parse import parse_qs, urlparse, unquote
import asyncio
import requests
from src.config.config import AUTH_TOKEN, WEB_URL, DOWNLOAD_URL, LOG_URL, WINDOWS  # noqa
from src.database.db_operations import DatabaseError, fetch_filtered_items
from src.zip.zip import create_zip_from_files
from src.server.socket import notify_client


class AuthHTTPRequestHandler(SimpleHTTPRequestHandler):
    """
    A request handler class with authorization and file handling.

    Methods:
        do_GET(): Handle GET requests with authorization and file handling.
        handle_zip_creation(list_of_files, query_params): Creates a zip file
        from a list of files and notifies the client via WebSocket.
        end_headers(): Add custom headers to the response.
        do_OPTIONS(): Handle OPTIONS requests for CORS preflight.
    """

    def do_GET(self):
        """
        Handle GET requests with authorization and file handling.
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

                    threading.Thread(target=self.handle_zip_creation, args=(
                        list_of_files, query_params)).start()

                    client_id = query_params.get('client', [None])[0]
                    if client_id:
                        requests.put(
                            LOG_URL, headers=headers, timeout=10, json={'client_id': client_id, 'graphs': list_of_ids, 'mode': 'original'})  # noqa

                    self.send_response(201)
                    self.send_header('Content-Type', 'text/plain')
                    self.end_headers()

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
        elif parsed_path.path == '/download_exec':
            query_params = parse_qs(parsed_path.query)
            if 'path' not in query_params:
                self.send_response(400)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'Missing path parameter')
                return

            zip_path = query_params.get('path', [''])[0]

            existing_zip = os.path.exists(zip_path)

            if not existing_zip:
                self.send_response(404)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'File not found')
                return

            try:
                self.send_response(200)
                self.send_header('Content-Type', 'application/zip')
                self.send_header(
                    'Content-Disposition', f'attachment; filename="{os.path.basename(zip_path)}"')  # noqa
                self.end_headers()
                with open(zip_path, 'rb') as file:
                    while True:
                        chunk = file.read(8192)
                        if not chunk:
                            break
                        self.wfile.write(chunk)

                os.remove(zip_path)
            except Exception as e:  # pylint: disable=broad-except
                self.send_response(500)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write(f'Error serving file: {e}'.encode('utf-8'))
                return
        else:
            file_path = unquote(parsed_path.path)
            file_path = file_path[1:] if WINDOWS else file_path

            if (file_path[1:3] == ':/' or file_path[1:3] == ':\\') and WINDOWS:
                file_path = file_path.lstrip('/')

            if not os.path.isabs(file_path):
                file_path = os.path.join(os.getcwd(), file_path.lstrip('/'))

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
                try:
                    with open(self_path, 'rb') as file:
                        self.send_response(200)
                        self.send_header(
                            'Content-Type', 'application/octet-stream')
                        self.send_header(
                            'Content-Disposition', f'attachment; filename="{os.path.basename(self_path)}"')  # noqa
                        self.end_headers()
                        while True:
                            chunk = file.read(8192)
                            if not chunk:
                                break
                            self.wfile.write(chunk)
                except Exception as e:  # pylint: disable=broad-except
                    self.send_response(500)
                    self.send_header('Content-Type', 'text/plain')
                    self.end_headers()
                    self.wfile.write(f'Error serving file: {
                                     e}'.encode('utf-8'))
                    return
            else:
                super().do_GET()

    def handle_zip_creation(self, list_of_files, query_params):
        """
        Creates a zip file from a list of files and notifies the client
        via WebSocket.

        Args:
            list_of_files (list): A list of file paths to include in the
            zip archive.
            query_params (dict): Query parameters from the request.
        """
        zip_path = create_zip_from_files(list_of_files)

        # Notify the client via WebSocket
        user_id = query_params.get('user_id', [None])[0]
        print('Notifying client', user_id)
        asyncio.run(notify_client(
            user_id, {'status': 'ready', 'zip_path': zip_path}))

    def end_headers(self):
        """
        Add custom headers to the response.
        """
        self.send_header('Access-Control-Allow-Origin', WEB_URL)
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers',
                         'Authorization, X-User-Token')
        super().end_headers()

    def do_OPTIONS(self):  # pylint: disable=invalid-name
        """
        Handle OPTIONS requests for CORS preflight.
        """
        self.send_response(200)
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers',
                         'Authorization, X-User-Token')
        self.end_headers()
