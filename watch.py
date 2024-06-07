"""
Monitor a folder and its subfolders for changes and generate previews
"""

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
        LOGGER.error("Error registering directory in the database: %s", exc)
        conn.rollback()
    finally:
        close_db(conn, cur)


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

                        dir_relative_path = os.path.relpath(
                            full_dir_path, REPOSITORY
                        )

                        dir_id = uuid.uuid4()

                        insert_new_directory(
                            dir_id, dir_name, dir_relative_path
                        )
                    else:
                        LOGGER.info("Empty directory ignored: %s",
                                    full_dir_path)
                    seen_directories.add(full_dir_path)

            for file in files:
                file_path = os.path.join(root, file)
                try:
                    mt = os.path.getmtime(file_path)
                except FileNotFoundError:
                    mt = None
                if file_path not in files_dict or files_dict[file_path] != mt:
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

                preview(file_path, destination_path, dir_id)

            files_dict.update(updated_files)


if __name__ == "__main__":
    FOLDER_TO_WATCH = REPOSITORY
    monitor_folder(FOLDER_TO_WATCH)
