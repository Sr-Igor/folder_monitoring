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
        try:
            if not file_path.startswith('.'):
                file_path = os.path.normpath(file_path)  # Normalize file path
                mt = os.path.getmtime(file_path)
                LOGGER.info("Modified file detected: %s: %s", file_path, mt)

                relative_path = os.path.relpath(file_path, REPOSITORY)
                relative_path = os.path.normpath(
                    relative_path)  # Normalize relative path
                destination_path = os.path.join(
                    DESTINATION, os.path.dirname(relative_path)
                )
                destination_path = os.path.normpath(
                    destination_path)  # Normalize destination path

                os.makedirs(destination_path, exist_ok=True)

                full_dir_path = os.path.dirname(file_path)
                full_dir_path = os.path.normpath(
                    full_dir_path)  # Normalize directory path
                dir_id = ensure_directory_registered(full_dir_path)

                try:
                    preview(file_path, REPOSITORY, destination_path, dir_id)
                except Exception as exc:
                    file_error_message = f"Error processing file {
                        file_path}: {exc}"
                    LOGGER.error(file_error_message)
                    db.log_error_to_db(file_error_message)
        except Exception as e:
            LOGGER.error("Error processing file: %s, Error: %s", file_path, e)


def ensure_directory_registered(full_dir_path):
    try:
        dir_relative_path = os.path.relpath(full_dir_path, REPOSITORY)
        dir_relative_path = os.path.normpath(
            dir_relative_path)  # Normalize relative path
        dir_id = db.get_directory_id(dir_relative_path)
        if dir_id is None:
            dir_name = os.path.basename(full_dir_path)
            dir_id = uuid.uuid4()
            db.insert_new_directory(dir_id, dir_name, dir_relative_path)
        return dir_id
    except Exception as e:
        LOGGER.error(
            "Error ensuring directory is registered: %s, Error: %s", full_dir_path, e)
        raise


def signal_handler(sign, frame):
    log_shutdown()
    sys.exit(0)


def monitor_folder(folder_path, force_resync=False):
    LOGGER.info("Monitoring folder '%s' and its subfolders...", folder_path)
    folder_path = os.path.normpath(folder_path)  # Normalize folder path

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


if __name__ == "__main__":
    monitor_folder(REPOSITORY)
