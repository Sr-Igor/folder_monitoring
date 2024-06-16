"""
Module for monitoring a folder and its subfolders, registering directories in a
database, and processing modified files.

This module includes functions for:
- Monitoring a specified folder and its subfolders.
- Registering new directories in a database if they are not already registered.
- Processing modified files by generating previews, logging operations, and
  saving metadata to a database.

Dependencies:
    - os: Provides access to operating system functionalities.
    - signal: Allows handling of signals such as SIGINT and SIGTERM.
    - psycopg2: PostgreSQL adapter for Python.
    - uuid: Generates UUIDs for directory IDs.
    - db_logger.LOGGER: Logger object for logging operations.
    - image.preview: Function to generate image previews.
    - operations.log_error_to_db: Function to log errors to a database.
    - config.DESTINATION: Destination folder for processed files.
    - config.REPOSITORY: Root folder being monitored.
    - db_connection.connect_db, db_connection.close_db: Functions for
      establishing and closing database connections.
"""

import os
import signal
import time
import uuid

from src.config.config import DESTINATION, REPOSITORY
from src.logs.logger import LOGGER, log_shutdown
from src.image.image import preview
import src.database.db_operations as db


def is_directory_empty(directory):
    """
    Check if a directory is empty or contains only subdirectories.

    Args:
        directory (str): Path to the directory.

    Returns:
        bool: True if the directory is empty or contains only subdirectories,
        False otherwise.
    """
    try:
        # Itera sobre os itens no diretório
        for entry in os.scandir(directory):
            if entry.is_file() or (entry.is_dir() and not is_directory_empty(entry.path)):  # noqa
                return False
        return True
    except FileNotFoundError as exc:
        raise ValueError(f"The directory '{
                         directory}' does not exist.") from exc
    except PermissionError as exc:
        raise ValueError(f"Permission denied for directory '{
                         directory}'.") from exc


def ensure_directory_registered(full_dir_path):
    """
    Ensure that a directory is registered in the database.

    If the directory is not already registered, it inserts it into the database
    with a generated UUID.

    Args:
        full_dir_path (str): Full path of the directory.

    Returns:
        uuid.UUID: UUID of the directory.
    """
    dir_relative_path = os.path.relpath(full_dir_path, REPOSITORY)
    dir_id = db.get_directory_id(dir_relative_path)
    if dir_id is None:
        dir_name = os.path.basename(full_dir_path)
        dir_id = uuid.uuid4()
        db.insert_new_directory(dir_id, dir_name, dir_relative_path)
    return dir_id


def monitor_folder(folder_path, force_resync=False):
    """Monitor the specified folder and its subfolders."""
    LOGGER.info("Monitoring folder '%s' and its subfolders...", folder_path)
    files_dict = {}
    seen_directories = set()

    # WARN - If this true, all existent files will be reprocessed
    if not force_resync:
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
                    preview(file_path, folder_path, destination_path, dir_id)
                except Exception as exc:  # pylint: disable=broad-except
                    file_error_message = f"Error processing file {
                        file_path}: {exc}"
                    LOGGER.error(file_error_message)
                    db.log_error_to_db(file_error_message)

            files_dict.update(updated_files)
