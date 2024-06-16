"""
Module for logging script initialization and shutdown.

This module initializes a logger and provides functions to log script
initialization and shutdown messages using the logger. It also logs these
messages to a database via operations.log_error_to_db().

Dependencies:
    - logging: Standard Python logging library.
    - operations: Module providing database logging functionality.

Constants:
    LOGGER: Logger object configured for this module.
"""

import logging
import src.database.db_operations as db_operations

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


def log_initialization():
    """
    Logs script initialization.

    This function logs a message indicating that the script is running.
    Additionally, it logs the same message to a database using
    operations.log_error_to_db().

    Returns:
        None
    """
    LOGGER.info("Script is running.")
    db_operations.log_error_to_db("Script is running.")


def log_shutdown():
    """
    Logs script shutdown.

    This function logs a message indicating that the script is shutting down.
    Additionally, it logs the same message to a database using
    operations.log_error_to_db().

    Returns:
        None
    """
    LOGGER.info("Script down.")
    db_operations.log_error_to_db("Script down.")
