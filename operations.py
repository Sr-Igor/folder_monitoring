"""
Database operations module.

This module provides functions to log errors and save information to a database. # noqa
It utilizes psycopg2 for database connectivity and operations, and db_logger
for logging database-related events.

Dependencies:
    - uuid: Generates UUIDs for log and entry IDs.
    - psycopg2.sql: Helps in constructing SQL queries.
    - psycopg2.DatabaseError, psycopg2.Error: Exceptions related to database operations.
    - db_connection.connect_db, db_connection.close_db: Functions for establishing
      and closing database connections.
    - db_logger: Module for logging database-related events.

Functions:
    log_error_to_db: Logs an error message to the database.
    save_to_database: Saves information (original and preview filenames, graph ID,
        DPI, dimensions, pixels, size) to the database.
"""

import uuid
from psycopg2 import sql, DatabaseError, Error
from db_connection import connect_db, close_db
import db_logger as log


def log_error_to_db(error_text):
    """
    Log an error message to the database.

    Args:
        error_text (str): Error message to log.

    Returns:
        None
    """
    conn, cur = connect_db()
    try:
        log_id = uuid.uuid4()
        query = sql.SQL("INSERT INTO logs_script (id, log) VALUES (%s, %s)")
        cur.execute(query, (str(log_id), error_text))
        conn.commit()
    except DatabaseError as exc:
        log.LOGGER.error("Error logging to the database: %s", exc)
        conn.rollback()
    finally:
        close_db(conn, cur)


def save_to_database(original_filename, preview_filename, graph_id, dpi, dimension, pixels, size, error=None):  # noqa
    """
    Save information to the database.

    Args:
        original_filename (str): Original filename or path.
        preview_filename (str): Preview filename or path.
        graph_id (uuid.UUID): ID of the associated graph or entity.
        dpi (int or None): DPI (dots per inch) of the image.
        dimension (str or None): Dimensions of the image.
        pixels (int or None): Number of pixels in the image.
        size (float or None): Size of the image file in MB.
        error (str or None, optional): Error message (if any). Defaults to None. # noqa

    Returns:
        None
    """
    conn = None
    try:
        conn, cur = connect_db()
        entry_id = uuid.uuid4()
        if error:
            query = sql.SQL(
                "INSERT INTO logs_script (id, log) VALUES (%s, %s)")
            cur.execute(query, (str(entry_id), str(error)))
        else:
            query = sql.SQL(
                "INSERT INTO graphs_children (id, graph_id, preview, original, dpi, dimension, pixel, size) "  # noqa
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
        log.LOGGER.info("Information saved to the database successfully!")
    except Error as e:
        log.LOGGER.error(
            "Error connecting or interacting with the database: %s", e)
    except Exception as e:  # pylint: disable=broad-except
        log.LOGGER.error("Error saving information to the database: %s", e)
    finally:
        if conn:
            close_db(conn, cur)