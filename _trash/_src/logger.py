# logger.py
import logging
import os
import psycopg2
from psycopg2 import sql
from uuid import uuid4
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DB_URL")
LOGGER = logging.getLogger(__name__)


def configure_logging():
    logging.basicConfig(level=logging.INFO)


def log_initialization():
    LOGGER.info("Script is running.")
    log_error_to_db("Script is running.")


def log_shutdown():
    LOGGER.info("Script down.")
    log_error_to_db("Script down.")


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


def log_error_to_db(error_text):
    conn, cur = connect_db()
    try:
        log_id = uuid4()
        query = sql.SQL("INSERT INTO logs_script (id, log) VALUES (%s, %s)")
        cur.execute(query, (str(log_id), error_text))
        conn.commit()
    except psycopg2.DatabaseError as exc:
        LOGGER.error("Error logging to the database: %s", exc)
        conn.rollback()
        raise
    finally:
        close_db(conn, cur)
