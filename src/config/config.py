"""
Module for loading environment variables and defining constants.

This module loads environment variables using `dotenv` from a `.env` file in
the current directory. It defines constants for various settings used in the
application.

Constants:
    REPOSITORY (str): Internal path retrieved from environment variable
        INTERNAL_PATH.
    DESTINATION (str): Preview path retrieved from environment variable
        PREVIEW_PATH.
    DB_URL (str): Database URL retrieved from environment variable DB_URL.
    AUTH_TOKEN (str): Authorization token retrieved from environment variable
        AUTH.
    WEB_URL (str): Web URL retrieved from environment variable WEB_URL.
    QUALITY (str): Quality setting retrieved from environment variable QUALITY,
        default is "50".
    IP_SERVER (str): Server IP address retrieved from environment variable
        IP_SERVER, default is "0.0.0.0".
    PORT (str): Server port retrieved from environment variable PORT, default
        is "8000".
"""

import os
from dotenv import load_dotenv

load_dotenv()

REPOSITORY = os.getenv("INTERNAL_PATH")
DESTINATION = os.getenv("PREVIEW_PATH")
DB_URL = os.getenv("DB_URL")
AUTH_TOKEN = os.getenv("AUTH")
WEB_URL = os.getenv("WEB_URL")
QUALITY = os.getenv("QUALITY", "50")
IP_SERVER = os.getenv("IP_SERVER", "0.0.0.0")
PORT = os.getenv("PORT", "8000")
