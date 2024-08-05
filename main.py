"""
Main script for running the repository monitoring application.

This script initializes logging, starts a server in a separate thread, monitors
a specified folder for changes, and handles any unexpected errors that may occur. # noqa
Dependencies:
    - db_logger.log_initialization: Initializes logging for the application.
    - db_logger.log_shutdown: Cleans up resources and finalizes logging.
    - db_logger.LOGGER: Logger object for logging events and errors.
    - config.REPOSITORY: Root folder to monitor for changes.
    - config.PORT: Port number for the server.
    - monitor.monitor_folder: Function to monitor a folder and its subfolders.
    - server.run_https_server_in_thread: Function to run a server in a separate thread.

Functions:
    main: Main function to execute the repository monitoring application.
"""

from src.logs.logger import log_initialization, log_shutdown, LOGGER
from src.config.config import PORT,  ABSOLUTE_PATH
from src.server.server import run_http_server_in_thread
from src.database.db_operations import log_error_to_db


def main():
    """
    Main function to execute the repository monitoring application.

    This function performs the following steps:
    1. Initializes logging for the application.
    2. Defines the folder to monitor (REPOSITORY).
    3. Starts a server in a separate thread on the specified port (PORT).
    4. Monitors the specified folder (REPOSITORY) for changes.
    5. Logs any unexpected errors that occur during execution.

    Returns:
        None
    """
    try:
        log_initialization()
        run_http_server_in_thread(ABSOLUTE_PATH, PORT, "Repository Server")
    except Exception as e:  # pylint: disable=broad-except
        error_message = f"An unexpected error occurred: {e}"
        LOGGER.error(error_message)
        log_error_to_db(error_message)
    finally:
        log_shutdown()


if __name__ == "__main__":
    main()
