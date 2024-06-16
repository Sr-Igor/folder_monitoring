# database.py
import os
from uuid import uuid4

import psycopg2
from psycopg2 import sql

from logger import LOGGER, log_error_to_db

DB_URL = os.getenv("DB_URL")


def connect_db():
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        return conn, cur
    except psycopg2.Error as e:
        LOGGER.error("Error connecting to the database: %s", e)
        raise


def close_db(conn, cur):
    try:
        cur.close()
        conn.close()
    except psycopg2.Error as e:
        LOGGER.error("Error closing database connection: %s", e)
        raise


def save_to_database(original_filename, preview_filename, graph_id, dpi,
                     dimension, pixels, size, error=None):
    conn, cur = connect_db()
    try:
        entry_id = uuid4()
        if error:
            query = sql.SQL(
                "INSERT INTO logs_script (id, log) VALUES (%s, %s)")
            cur.execute(query, (str(entry_id), str(error)))
        else:
            query = sql.SQL("INSERT INTO graphs_children (id, graph_id, preview, original, dpi, dimension, pixel, size) "  # noqa
                            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)")
            cur.execute(query, (str(entry_id), str(graph_id), preview_filename, original_filename, dpi,  # noqa
                                dimension, pixels, size))
        conn.commit()
        LOGGER.info("Information saved to the database successfully!")
    except psycopg2.Error as e:
        LOGGER.error("Error saving information to the database: %s", e)
        log_error_to_db(str(e))
        conn.rollback()
        raise
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
        inner_error_message = f"Error retrieving directory ID from the database: {  # noqa
            exc}"
        LOGGER.error(inner_error_message)
        log_error_to_db(inner_error_message)
    finally:
        close_db(conn, cur)


def insert_new_directory(dir_id, dir_name, dir_relative_path):
    """Insert a new record into the graphs."""
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
