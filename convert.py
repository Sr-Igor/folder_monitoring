"""
Generate image previews and save them to a database.
"""

import logging
import os
import uuid
from typing import Any
import psd_tools
import psycopg2
from dotenv import load_dotenv
from PIL import Image
from psycopg2 import sql

load_dotenv()

DB_URL = os.getenv("DB_URL")

# Logger configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def preview(
    arch: Any,
    folder_destiny: str = 'previews',
    graph_id: str = 'none'
) -> None:
    """
    Preview function to visualize and save image previews.

    Args:
        arch (Any): The path to the image file.
        folder_destiny (str, optional): Where the preview will be saved.
        graph_id (str, optional): The ID of the graph. Defaults to 'none'.

    Returns:
        None
    """
    logger.info("Viewing %s...", arch)
    if not os.path.exists(folder_destiny):
        os.makedirs(folder_destiny)

    try:
        ext = arch.split('.')[-1].lower()

        if ext == 'psb':
            psb = psd_tools.PSDImage.open(arch)
            img = psb.topil()
        else:
            img = Image.open(arch)

        if img.mode in ('CMYK', 'RGBA', 'LA', 'P'):
            img = img.convert('RGB')

        module = arch.split('.')
        path = module[0].split('/')
        name = path[-1]
        output_path = f'{folder_destiny}/{name}.jpeg'

        img.save(output_path, 'JPEG')

        logger.info("Conversion of %s completed successfully!", arch)
        save_to_database(arch, output_path, graph_id)

    except Exception as e:  # pylint: disable=broad-except
        logger.error("An error occurred while converting the file: %s", e)


def save_to_database(original_filename, preview_filename, graph_id):
    """Save information to the database."""
    conn = None
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        entry_id = uuid.uuid4()
        query = sql.SQL(
            "INSERT INTO graphs_children (id, graph_id, preview, original) "
            "VALUES (%s, %s, %s, %s)"
        )
        cur.execute(query, (str(entry_id), str(graph_id),
                    preview_filename, original_filename))
        conn.commit()
        logger.info("Information saved to the database successfully!")

    except psycopg2.Error as e:
        logger.error(
            "Error connecting or interacting with the database: %s", e)

    except Exception as e:  # pylint: disable=broad-except
        logger.error("Error saving information to the database: %s", e)

    finally:
        if conn:
            conn.close()
