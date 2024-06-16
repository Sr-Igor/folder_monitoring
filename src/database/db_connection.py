"""
Module for database connection management using psycopg2.

This module provides functions to connect to and close connections with a
PostgreSQL database using psycopg2.

Dependencies:
    - psycopg2: PostgreSQL adapter for Python.
    - config.DB_URL: Database URL imported from the `config` module.

Functions:
    connect_db: Establishes a connection to the database and returns
        connection and cursor objects.
    close_db: Closes the connection and cursor passed as parameters.
"""

import psycopg2
from src.config.config import DB_URL


def connect_db():
    """
    Establishes a connection to the database.

    Returns:
        tuple: A tuple containing the connection (`psycopg2
            .extensions.connection`)
            and cursor (`psycopg2.extensions.cursor`) objects.
    """
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    return conn, cur


def close_db(conn, cur):
    """
    Closes the database connection and cursor.

    Args:
        conn (psycopg2.extensions.connection): PostgreSQL database connection
            object.
        cur (psycopg2.extensions.cursor): PostgreSQL database cursor object.

    Returns:
        None
    """
    cur.close()
    conn.close()
