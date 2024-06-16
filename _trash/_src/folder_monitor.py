# folder_monitor.py
import os
import time
import argparse  # Adicionado para lidar com argumentos de linha de comando
from uuid import uuid4

from database import get_directory_id, insert_new_directory
from image_processing import preview
from logger import LOGGER, log_error_to_db


def ensure_directory_registered(full_dir_path):
    """Ensure that the directory is registered in the database."""
    dir_relative_path = os.path.relpath(full_dir_path)
    dir_id = get_directory_id(dir_relative_path)
    if dir_id is None:
        dir_name = os.path.basename(full_dir_path)
        dir_id = uuid4()
        insert_new_directory(dir_id, dir_name, dir_relative_path)
    return dir_id


def is_directory_empty(directory):
    """Check if the folder is empty."""
    is_empty = not any(os.scandir(directory))
    if is_empty:
        LOGGER.info("Empty directory ignored: %s", directory)

    return is_empty


def monitor_folder(folder_path, folder_preview, process_existing):
    LOGGER.info("Monitoring folder '%s' and its subfolders...", folder_path)
    files_dict = {}
    seen_directories = set()
    current_directories = set()  # Inicialize current_directories aqui

    if process_existing:
        LOGGER.info("Processing existing files in the folder...")
        for root, dirs, files in os.walk(folder_path):
            current_directories.add(root)
            for file in files:
                if not file.startswith('.'):
                    file_path = os.path.join(root, file)
                    try:
                        mt = os.path.getmtime(file_path)
                    except FileNotFoundError:
                        mt = None
                    # Atualiza o dict com os arquivos existentes
                    files_dict[file_path] = mt

                    relative_path = os.path.relpath(file_path, folder_path)
                    destination_path = os.path.join(
                        folder_preview, os.path.dirname(relative_path))

                    os.makedirs(destination_path, exist_ok=True)

                    full_dir_path = os.path.dirname(file_path)
                    dir_id = ensure_directory_registered(full_dir_path)

                    try:
                        preview(file_path, folder_path,
                                destination_path, dir_id)
                    except Exception as exc:
                        file_error_message = f"Error processing file {
                            file_path}: {exc}"
                        LOGGER.error(file_error_message)
                        log_error_to_db(file_error_message)

    while True:
        time.sleep(1)
        updated_files = {}
        current_directories = set()  # Redefina a cada iteração

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
                    folder_preview, os.path.dirname(relative_path))

                os.makedirs(destination_path, exist_ok=True)

                full_dir_path = os.path.dirname(file_path)
                dir_id = ensure_directory_registered(full_dir_path)

                try:
                    preview(file_path, folder_path, destination_path, dir_id)
                except Exception as exc:  # pylint: disable=broad-except
                    file_error_message = f"Error processing file {
                        file_path}: {exc}"
                    LOGGER.error(file_error_message)
                    log_error_to_db(file_error_message)

            files_dict.update(updated_files)


# if __name__ == "__main__":
#     parser = argparse.ArgumentParser(
#         description="Monitor a folder for new or modified files.")
#     parser.add_argument("folder_path", help="Path to the folder to monitor")
#     parser.add_argument(
#         "folder_preview", help="Path to the folder for previews")
#     parser.add_argument("--process-existing", action="store_true",
#                         help="Process existing files on start")

#     args = parser.parse_args()
#     monitor_folder(args.folder_path, args.folder_preview,
#                    args.process_existing)
