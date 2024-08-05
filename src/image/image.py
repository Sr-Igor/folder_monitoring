"""
Module for image preview generation and logging.

This module provides functions to generate image previews, handle different
image formats (including PSD and complex TIFF files), calculate DPI, and log
operations using the configured LOGGER.

Dependencies:
    - os: Provides access to operating system functionalities.
    - PIL.Image, PIL.ImageFile: Image processing library and utilities.
    - operations.save_to_database: Function to save data to a database.
    - db_logger.LOGGER: Logger object for logging operations.
    - config.QUALITY: Quality setting for image compression.

Functions:
    preview: Generates a preview of an image, converts it to JPEG format with
        specified quality, logs the conversion process, and saves metadata
        to a database.
"""

import os
import warnings
from PIL import Image, ImageFile
from src.image.manual import manual_conversion
from src.image.magick import magick_conversion

from src.config.config import QUALITY, PIXEL_LIMIT
from src.logs.logger import LOGGER
from src.database.db_operations import save_to_database, is_file_registered

ImageFile.LOAD_TRUNCATED_IMAGES = True
Image.MAX_IMAGE_PIXELS = 250000000000

# Ignore warnings
warnings.filterwarnings("ignore", category=Image.DecompressionBombWarning)

def preview(arch,
            folder_path,
            folder_destiny='previews',
            graph_id='none',
            quality=int(QUALITY)):
    """
    Generate a preview of an image.

    This function loads an image file, converts it to JPEG format with
    specified quality, calculates DPI, logs the conversion process, and saves
    metadata to a database.

    Args:
        arch (str): Path to the image file.
        folder_path (str): Path to the folder containing the image.
        folder_destiny (str, optional): Destination folder for the generated
            preview images. Defaults to 'previews'.
        graph_id (str, optional): ID associated with the image.
        Defaults to 'none'. quality (int, optional): Quality level for JPEG
        compression. Defaults to the value defined in config.QUALITY.

    Returns:
        None
    """
    LOGGER.info("Processing %s...", arch)

    if not os.path.exists(folder_destiny):
        os.makedirs(folder_destiny)

    module = arch.replace(folder_path, '').replace('\\', '/').split('.')
    path = module[0].split('/')
    name = path[-1]
    LOGGER.info("Converting %s... with %s of quality", name, quality)

    output_path = f'{folder_destiny}/{name}.jpeg'

    try:
        ext = arch.split('.')[-1].lower()
        if ext == 'psb':
            manual_conversion(arch, output_path)
        else:
            magick_conversion(arch, output_path, quality, PIXEL_LIMIT)

        dpi = None
        dimension = None
        pixels = None

        # Get size of the original file
        size_original = os.path.getsize(arch) / (1024 * 1024) if os.path.exists(arch) else None  # noqa
        size_original_mb = f"{size_original:.2f}" if size_original else None

        LOGGER.info("Conversion of %s completed successfully!", arch)

        if is_file_registered(arch):
            LOGGER.info("File %s is already registered. Skipping re-save.", arch)  # noqa
            return

        save_to_database(arch, output_path, graph_id, dpi,
                         dimension, pixels, size_original_mb, name)

    except Exception as e:  # pylint: disable=broad-except
        LOGGER.error("An error occurred while converting the file: %s", e)
        save_to_database(arch, None, graph_id, None,
                         None, None, None, None, str(e))
