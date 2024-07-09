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
import sys
import time
import uuid
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from src.config.config import DESTINATION, REPOSITORY
from src.logs.logger import LOGGER, log_shutdown
from src.image.image import preview
import src.database.db_operations as db


class FolderMonitorHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.is_directory:
            return
        self.process(event.src_path)

    def on_created(self, event):
        if event.is_directory:
            return
        self.process(event.src_path)

    def process(self, file_path):
        if not file_path.startswith('.'):
            try:
                mt = os.path.getmtime(file_path)
            except FileNotFoundError:
                mt = None
            LOGGER.info("Modified file detected: %s: %s", file_path, mt)

            relative_path = os.path.relpath(file_path, REPOSITORY)
            destination_path = os.path.join(
                DESTINATION, os.path.dirname(relative_path)
            )

            os.makedirs(destination_path, exist_ok=True)

            full_dir_path = os.path.dirname(file_path)
            dir_id = ensure_directory_registered(full_dir_path)

            try:
                preview(file_path, REPOSITORY, destination_path, dir_id)
            except Exception as exc:
                file_error_message = f"Error processing file {
                    file_path}: {exc}"
                LOGGER.error(file_error_message)
                db.log_error_to_db(file_error_message)


def ensure_directory_registered(full_dir_path):
    dir_relative_path = os.path.relpath(full_dir_path, REPOSITORY)
    dir_id = db.get_directory_id(dir_relative_path)
    if dir_id is None:
        dir_name = os.path.basename(full_dir_path)
        dir_id = uuid.uuid4()
        db.insert_new_directory(dir_id, dir_name, dir_relative_path)
    return dir_id


def signal_handler(sign, frame):
    log_shutdown()
    sys.exit(0)


def monitor_folder(folder_path, force_resync=False):
    LOGGER.info("Monitoring folder '%s' and its subfolders...", folder_path)

    event_handler = FolderMonitorHandler()
    observer = Observer()
    observer.schedule(event_handler, folder_path, recursive=True)
    observer.start()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
