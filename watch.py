import os
import time
import uuid
import logging
from dotenv import load_dotenv
import psycopg2
from psycopg2 import sql
from convert import preview

# Configure logger
logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Set paths and database URL
REPOSITORY = os.getenv("INTERNAL_PATH")
DESTINATION = os.getenv("PREVIEW_PATH")
DB_URL = os.getenv("DB_URL")


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


def insert_new_directory(dir_id, dir_name, dir_relative_path):
    """
    Insert a new record into the graphs.
    """
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
        inner_error_message = f"Error retrieving directory ID from the database: {  # noqa: E501
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
            if not file.startswith('.'):  # Ignora arquivos que começam com "."
                file_path = os.path.join(root, file)
                try:
                    files_dict[file_path] = os.path.getmtime(file_path)
                except FileNotFoundError:
                    files_dict[file_path] = None

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
                    if file_path not in files_dict or files_dict[file_path] != mt:  # noqa: E501
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
                except Exception as exc:  # pylint: disable=broad-except
                    file_error_message = f"Error processing file {
                        file_path}: {exc}"
                    LOGGER.error(file_error_message)
                    log_error_to_db(file_error_message)

            files_dict.update(updated_files)


if __name__ == "__main__":
    while True:
        try:
            FOLDER_TO_WATCH = REPOSITORY
            monitor_folder(FOLDER_TO_WATCH)
        except Exception as e:  # pylint: disable=broad-except
            error_message = f"An unexpected error occurred: {e}"
            LOGGER.error(error_message)
            log_error_to_db(error_message)
            LOGGER.info("Restarting the monitoring process...")
