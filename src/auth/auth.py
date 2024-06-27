
import os
from http.server import SimpleHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

from src.config.config import AUTH_TOKEN, WEB_URL
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
            zip_path = create_zip_from_files(file_paths)
            self.send_response(200)
            self.send_header('Content-Type', 'application/zip')
            self.send_header(
                'Content-Disposition', f'attachment; filename="{os.path.basename(zip_path)}"')  # noqa
            self.end_headers()
            with open(zip_path, 'rb') as file:
                self.wfile.write(file.read())
            os.remove(zip_path)
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
