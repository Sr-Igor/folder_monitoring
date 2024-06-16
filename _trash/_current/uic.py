import logging
import os
import signal
import threading
import time
import uuid
import warnings
from http.server import HTTPServer, SimpleHTTPRequestHandler
from typing import Any

import psd_tools
import psycopg2
from dotenv import load_dotenv
from PIL import Image, ImageFile
from psycopg2 import sql


load_dotenv()

DB_URL = os.getenv("DB_URL")
QUALITY = os.getenv("QUALITY")

# Logger configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ignore warnings
warnings.filterwarnings("ignore", category=Image.DecompressionBombWarning)

# Handle truncated images
ImageFile.LOAD_TRUNCATED_IMAGES = True


def calculate_dpi(width, height):
    """
    Calculate DPI using default inch value.
    """
    # Default inch value
    default_inch = 1

    # Calculate DPI
    dpi = (width + height) / default_inch

    return dpi


def preview(
    arch: Any,
    folder_destiny: str = 'previews',
    graph_id: str = 'none',
    quality: int = QUALITY
) -> None:
    """
    Preview function to visualize and save image previews.

    Args:
        arch (Any): The path to the image file.
        folder_destiny (str, optional): Where the preview will be saved.
        graph_id (str, optional): The ID of the graph. Defaults to 'none'.
        quality (int, optional): JPEG quality for compression. Defaults to 50.

    Returns:
        None
    """
    logger.info("Viewing %s...", arch)
    if not os.path.exists(folder_destiny):
        os.makedirs(folder_destiny)

    try:
        ext = arch.split('.')[-1].lower()

        if ext == 'psb':
            psb = psd_tools.PSDImage.open(arch)
            img = psb.topil()
        else:
            img = Image.open(arch)

        if img.mode in ('CMYK', 'RGBA', 'LA', 'P'):
            img = img.convert('RGB')

        module = arch.split('.')
        path = module[0].split('/')
        name = path[-1]
        output_path = f'{folder_destiny}/{name}.jpeg'

        # Save image with compression
        img.save(output_path, 'JPEG', quality=quality,
                 optimize=True, progressive=True)

        # Extract additional information
        dpi = img.info.get('dpi', (None, None))
        if dpi[0] is not None and dpi[1] is not None:
            dpi = sum(dpi) // len(dpi)  # Average DPI if both values exist
        else:
            width, height = img.size
            dpi = None

        width, height = img.size
        dimension = f"{height}x{width}" if width and height else None
        pixels = width * height if width and height else None
        size = os.path.getsize(output_path) / (1024 *
                                               1024) if os.path.exists(output_path) else None

        logger.info("Conversion of %s completed successfully!", arch)
        save_to_database(arch, output_path, graph_id,
                         dpi, dimension, pixels, size)

    except Exception as e:  # pylint: disable=broad-except
        logger.error("An error occurred while converting the file: %s", e)
        save_to_database(arch, None, graph_id, None,
                         None, None, None, error=str(e))


def save_to_database(original_filename, preview_filename, graph_id, dpi,
                     dimension, pixels, size, error=None):
    """Save information to the database."""
    conn = None
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        entry_id = uuid.uuid4()
        if error:
            query = sql.SQL(
                "INSERT INTO logs_script (id, log) VALUES (%s, %s)"
            )
            cur.execute(query, (
                str(entry_id),
                str(error)
            ))
        else:
            query = sql.SQL(
                "INSERT INTO graphs_children (id, graph_id, preview, original, dpi, dimension, pixel, size) "  # noqa: E501
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
            )
            cur.execute(query, (
                str(entry_id),
                str(graph_id),
                preview_filename,
                original_filename,
                dpi,
                dimension,
                pixels,
                size
            ))
        conn.commit()
        logger.info("Information saved to the database successfully!")

    except psycopg2.Error as e:
        logger.error(
            "Error connecting or interacting with the database: %s", e)

    except Exception as e:  # pylint: disable=broad-except
        logger.error("Error saving information to the database: %s", e)

    finally:
        if conn:
            conn.close()


# Configure logger
logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Set paths and database URL
REPOSITORY = os.getenv("INTERNAL_PATH")
DESTINATION = os.getenv("PREVIEW_PATH")
DB_URL = os.getenv("DB_URL")
AUTH_TOKEN = os.getenv("AUTH")
WEB_URL = os.getenv("WEB_URL")


class AuthHTTPRequestHandler(SimpleHTTPRequestHandler):
    """HTTP request handler with Bearer token authentication and CORS support."""  # noqa

    def do_GET(self):
        """Serve a GET request with authentication."""
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

        # If the token is valid, proceed with the normal handling
        super().do_GET()

    def log_message(self, format, *args):  # pylint: disable=redefined-builtin
        """Override to suppress logging from base class."""
        # To suppress the default logging, remove this to enable it
        pass  # pylint: disable=unnecessary-pass

    def end_headers(self):
        """Override to add CORS support."""
        self.send_header('Access-Control-Allow-Origin', WEB_URL)
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Authorization')
        super().end_headers()

    def do_OPTIONS(self):  # pylint: disable=invalid-name
        """Handle OPTIONS preflight request."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Authorization')
        self.end_headers()


def connect_db():
    """Connect to the database and return the connection and cursor."""
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    return conn, cur


def close_db(conn, cur):
    """Close the connection to the database."""
    cur.close()
    conn.close()


def log_error_to_db(error_text):
    """Log error to the logs_script table in the database."""
    conn, cur = connect_db()
    try:
        log_id = uuid.uuid4()
        query = sql.SQL(
            "INSERT INTO logs_script (id, log) VALUES (%s, %s)"
        )
        cur.execute(query, (str(log_id), error_text))
        conn.commit()
    except psycopg2.DatabaseError as exc:
        LOGGER.error("Error logging to the database: %s", exc)
        conn.rollback()
    finally:
        close_db(conn, cur)


def log_initialization():
    """Log script initialization."""
    LOGGER.info("Script is running.")
    log_error_to_db("Script is running.")


def log_shutdown():
    """Log script shutdown."""
    LOGGER.info("Script down.")
    log_error_to_db("Script down.")


log_initialization()


def insert_new_directory(dir_id, dir_name, dir_relative_path):
    """Insert a new record into the graphs."""
    conn, cur = connect_db()
    try:
        query = sql.SQL(
            "INSERT INTO graphs (id, name, path) VALUES (%s, %s, %s)"
        )
        cur.execute(query, (str(dir_id), dir_name, dir_relative_path))
        conn.commit()
        LOGGER.info(
            "New dir registered in the db: %s with relative path %s, UUID: %s",
            dir_name, dir_relative_path, dir_id
        )
    except psycopg2.DatabaseError as exc:
        inner_error_message = f"Error registering directory in the database: {
            exc}"
        LOGGER.error(inner_error_message)
        log_error_to_db(inner_error_message)
        conn.rollback()
    finally:
        close_db(conn, cur)


def get_directory_id(dir_relative_path):
    """Get the ID of a directory if it exists in the database."""
    conn, cur = connect_db()
    try:
        query = sql.SQL(
            "SELECT id FROM graphs WHERE path = %s"
        )
        cur.execute(query, (dir_relative_path,))
        result = cur.fetchone()
        if result:
            return result[0]
        else:
            return None
    except psycopg2.DatabaseError as exc:
        inner_error_message = f"Error retrieving directory ID from the database: {  # noqa
            exc}"
        LOGGER.error(inner_error_message)
        log_error_to_db(inner_error_message)
    finally:
        close_db(conn, cur)


def ensure_directory_registered(full_dir_path):
    """Ensure that the directory is registered in the database."""
    dir_relative_path = os.path.relpath(full_dir_path, REPOSITORY)
    dir_id = get_directory_id(dir_relative_path)
    if dir_id is None:
        dir_name = os.path.basename(full_dir_path)
        dir_id = uuid.uuid4()
        insert_new_directory(dir_id, dir_name, dir_relative_path)
    return dir_id


def is_directory_empty(directory):
    """Check if the folder is empty."""
    return not any(os.scandir(directory))


def monitor_folder(folder_path):
    """Monitor the specified folder and its subfolders."""
    LOGGER.info("Monitoring folder '%s' and its subfolders...", folder_path)
    files_dict = {}
    seen_directories = set()

    for root, dirs, files in os.walk(folder_path):
        seen_directories.add(root)
        for file in files:
            if not file.startswith('.'):
                file_path = os.path.join(root, file)
                try:
                    files_dict[file_path] = os.path.getmtime(file_path)
                except FileNotFoundError:
                    files_dict[file_path] = None

    def signal_handler(sign, frame):  # pylint: disable=unused-argument
        """Handler for termination signal."""
        log_shutdown()
        exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    while True:
        time.sleep(1)
        updated_files = {}
        current_directories = set()

        for root, dirs, files in os.walk(folder_path):
            current_directories.add(root)
            for dir_name in dirs:
                full_dir_path = os.path.join(root, dir_name)
                if full_dir_path not in seen_directories:
                    if not is_directory_empty(full_dir_path):
                        dir_id = ensure_directory_registered(full_dir_path)
                    else:
                        LOGGER.info("Empty directory ignored: %s",
                                    full_dir_path)
                    seen_directories.add(full_dir_path)

            for file in files:
                if not file.startswith('.'):
                    file_path = os.path.join(root, file)
                    try:
                        mt = os.path.getmtime(file_path)
                    except FileNotFoundError:
                        mt = None
                    if file_path not in files_dict or files_dict[file_path] != mt:  # noqa
                        updated_files[file_path] = mt

        if updated_files:
            LOGGER.info("Modified files:")
            for file_path, mt in updated_files.items():
                LOGGER.info("%s: %s", file_path, mt)

                relative_path = os.path.relpath(file_path, folder_path)
                destination_path = os.path.join(
                    DESTINATION, os.path.dirname(relative_path)
                )

                os.makedirs(destination_path, exist_ok=True)

                full_dir_path = os.path.dirname(file_path)
                dir_id = ensure_directory_registered(full_dir_path)

                try:
                    preview(file_path, destination_path, dir_id)
                except Exception as exc:
                    file_error_message = f"Error processing file {
                        file_path}: {exc}"
                    LOGGER.error(file_error_message)
                    log_error_to_db(file_error_message)

            files_dict.update(updated_files)


def start_http_server(directory, port=8000, server_name="Server"):
    """Start an HTTP server to serve files from the specified directory."""
    os.chdir(directory)
    handler = AuthHTTPRequestHandler
    httpd = HTTPServer(('0.0.0.0', port), handler)
    LOGGER.info(f"{server_name}  serving HTTP on 0.0.0.0 port {
                port} from directory: {directory}")
    httpd.serve_forever()


def run_server_in_thread(directory, port, server_name="Server"):
    """Run the HTTP server in a separate thread."""
    server_thread = threading.Thread(target=start_http_server, args=(
        directory, port, server_name), daemon=True)
    server_thread.start()


if __name__ == "__main__":
    try:
        FOLDER_TO_WATCH = REPOSITORY
        run_server_in_thread('./', 8000, "Repository Server")
        monitor_folder(FOLDER_TO_WATCH)
    except Exception as e:  # pylint: disable=broad-except
        error_message = f"An unexpected error occurred: {e}"
        LOGGER.error(error_message)
        log_error_to_db(error_message)
    finally:
        log_shutdown()
