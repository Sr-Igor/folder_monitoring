"""
Module for image preview generation and logging.

This module provides functions to generate image previews, handle different
image formats (including PSD files), calculate DPI, and log operations using
the configured LOGGER.

Dependencies:
    - os: Provides access to operating system functionalities.
    - psd_tools: Library for working with PSD files.
    - PIL.Image, PIL.ImageFile: Image processing library and utilities.
    - operations.save_to_database: Function to save data to a database.
    - db_logger.LOGGER: Logger object for logging operations.
    - config.QUALITY: Quality setting for image compression.

Functions:
    calculate_dpi: Calculates DPI (dots per inch) based on image dimensions.
    preview: Generates a preview of an image, converts it to JPEG format with
        specified quality, logs the conversion process, and saves metadata
        to a database.
"""

import os
import warnings

import psd_tools
from PIL import Image, ImageFile

from config import QUALITY
from db_logger import LOGGER
from operations import save_to_database

ImageFile.LOAD_TRUNCATED_IMAGES = True

# Ignore warnings
warnings.filterwarnings("ignore", category=Image.DecompressionBombWarning)


def calculate_dpi(width, height):
    """
    Calculate DPI (dots per inch) based on image dimensions.

    Args:
        width (int): Image width in pixels.
        height (int): Image height in pixels.

    Returns:
        float: Calculated DPI value.
    """
    default_inch = 1
    dpi = (width + height) / default_inch
    return dpi


def preview(arch,
            folder_path,
            folder_destiny='previews',
            graph_id='none',
            quality=int(QUALITY)):  # noqa
    """
    Generate a preview of an image.

    This function loads an image file, converts it to JPEG format with specified # noqa
    quality, calculates DPI, logs the conversion process, and saves metadata
    to a database.

    Args:
        arch (str): Path to the image file.
        folder_path (str): Path to the folder containing the image.
        folder_destiny (str, optional): Destination folder for the generated
            preview images. Defaults to 'previews'.
        graph_id (str, optional): ID associated with the image. Defaults to 'none'.
        quality (int, optional): Quality level for JPEG compression. Defaults to
            the value defined in config.QUALITY.

    Returns:
        None
    """
    LOGGER.info("Viewing %s...", arch)
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

        module = arch.replace(folder_path, '').replace('\\', '/').split('.')
        path = module[0].split('/')
        name = path[-1]
        LOGGER.info("Converting %s... with %s of quality", name, quality)

        output_path = f'{folder_destiny}/{name}.jpeg'

        img.save(output_path, 'JPEG', quality=quality,
                 optimize=True, progressive=True)

        dpi = img.info.get('dpi', (None, None))
        if dpi[0] is not None and dpi[1] is not None:
            dpi = sum(dpi) // len(dpi)
        else:
            width, height = img.size
            dpi = None

        width, height = img.size
        dimension = f"{height}x{width}" if width and height else None
        pixels = width * height if width and height else None
        size = os.path.getsize(output_path) / (1024 *
                                               1024) if os.path.exists(output_path) else None  # noqa

        LOGGER.info("Conversion of %s completed successfully!", arch)
        save_to_database(arch, output_path, graph_id,
                         dpi, dimension, pixels, size)

    except Exception as e:  # pylint: disable=broad-except
        LOGGER.error("An error occurred while converting the file: %s", e)
        save_to_database(arch, None, graph_id, None,
                         None, None, None, error=str(e))