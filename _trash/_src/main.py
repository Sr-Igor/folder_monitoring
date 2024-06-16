# main.py
import os
import threading
from dotenv import load_dotenv
from http_server import run_http_server_in_thread
from folder_monitor import monitor_folder
import logger as log

load_dotenv()

REPOSITORY = os.getenv("INTERNAL_PATH")
PREVIEW = os.getenv("PREVIEW_PATH")
ABSOLUTE_PATH = os.getenv("ABSOLUTE_PATH")
PROCESS_EXISTING = os.getenv(
    "PROCESS_EXISTING", "False").lower() == "true"  # Adicionado

if __name__ == "__main__":
    log.configure_logging()
    log.log_initialization()

    try:
        # run_http_server_in_thread(ABSOLUTE_PATH, 8000, "Repository Server")
        monitor_folder(REPOSITORY, PREVIEW, PROCESS_EXISTING)
    except Exception as e:  # pylint: disable=broad-except
        error_message = f"An unexpected error occurred: {e}"
        log.LOGGER.error(error_message)
        log.log_error_to_db(error_message)
    finally:
        log.log_shutdown()
