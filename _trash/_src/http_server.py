import os
from http.server import HTTPServer, SimpleHTTPRequestHandler

from dotenv import load_dotenv

from logger import LOGGER

load_dotenv()

AUTH_TOKEN = os.getenv("AUTH")
WEB_URL = os.getenv("WEB_URL")


class AuthHTTPRequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
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

        super().do_GET()

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', WEB_URL)
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Authorization')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Authorization')
        self.end_headers()


def run_http_server_in_thread(directory, port=8000, server_name="Server"):
    os.chdir(directory)
    handler = AuthHTTPRequestHandler
    httpd = HTTPServer(('0.0.0.0', port), handler)
    LOGGER.info("%s serving HTTP on port %s from directory: %s",
                server_name, port, directory)
    httpd.serve_forever()
