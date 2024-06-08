import logging
import os
import uuid
from typing import Any
import warnings
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

# Ignore warnings
warnings.filterwarnings("ignore", category=Image.DecompressionBombWarning)


def calculate_dpi(width, height):
    """
    Calculate DPI using default inch value.
    """
    # Default inch value
    default_inch = 1

    # Calculate DPI
    dpi = (width + height) / default_inch

    return dpi


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

        # Extract additional information
        dpi = img.info.get('dpi', (None, None))
        if dpi[0] is not None and dpi[1] is not None:
            dpi = sum(dpi) // len(dpi)  # Average DPI if both values exist
        else:
            width, height = img.size

            # dpi = calculate_dpi(width, height)
            dpi = None

        width, height = img.size
        dimension = f"{height}x{width}" if width and height else None
        pixels = width * height if width and height else None
        size = os.path.getsize(
            # Size in MB
            arch) / (1024 * 1024) if os.path.exists(arch) else None

        logger.info("Conversion of %s completed successfully!", arch)
        save_to_database(arch, output_path, graph_id,
                         dpi, dimension, pixels, size)

    except Exception as e:  # pylint: disable=broad-except
        logger.error("An error occurred while converting the file: %s", e)
        save_to_database(arch, None, graph_id, None,
                         None, None, None, error=str(e))


def save_to_database(original_filename, preview_filename, graph_id, dpi,
                     dimension, pixels, size, error=None):
    """Save information to the database."""
    conn = None
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        entry_id = uuid.uuid4()
        if error:
            query = sql.SQL(
                "INSERT INTO logs_script (id, log) VALUES (%s, %s)"
            )
            cur.execute(query, (
                str(entry_id),
                str(error)
            ))
        else:
            query = sql.SQL(
                "INSERT INTO graphs_children (id, graph_id, preview, original, dpi, dimension, pixel, size) "  # noqa: E501
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
        logger.info("Information saved to the database successfully!")

    except psycopg2.Error as e:
        logger.error(
            "Error connecting or interacting with the database: %s", e)

    except Exception as e:  # pylint: disable=broad-except
        logger.error("Error saving information to the database: %s", e)

    finally:
        if conn:
            conn.close()
