"""
Module for image preview generation and logging.

This module provides functions to generate image previews, handle different
image formats (including PSD and complex TIFF files), calculate DPI, and log
operations using the configured LOGGER.

Dependencies:
    - os: Provides access to operating system functionalities.
    - psd_tools: Library for working with PSD files.
    - tifffile: Library for working with TIFF files.
    - PIL.Image, PIL.ImageFile: Image processing library and utilities.
    - operations.save_to_database: Function to save data to a database.
    - db_logger.LOGGER: Logger object for logging operations.
    - config.QUALITY: Quality setting for image compression.

Functions:
    preview: Generates a preview of an image, converts it to JPEG format with
        specified quality, logs the conversion process, and saves metadata
        to a database.
    convert_cmyk_to_rgb: Converts a CMYK image to RGB format.
    resize_image: Resizes an image to a maximum width.
    save_image_as_jpeg: Saves an image as JPEG format.
"""

import os
import warnings
from io import BytesIO
import psd_tools
import tifffile
from PIL import Image, ImageFile, ImageCms
import cv2
import numpy as np

from src.config.config import QUALITY, PIXEL_LIMIT
from src.logs.logger import LOGGER
from src.database.db_operations import save_to_database, is_file_registered

ImageFile.LOAD_TRUNCATED_IMAGES = True
Image.MAX_IMAGE_PIXELS = 250000000000

# Ignore warnings
warnings.filterwarnings("ignore", category=Image.DecompressionBombWarning)


def is_complex_tiff(image):
    """ Check if the image is a complex TIFF file. """
    try:
        pil_image = Image.open(image)
        if 'icc_profile' in pil_image.info:
            return True
        return False
    except Exception as e:  # pylint: disable=broad-except
        LOGGER.info("ICC profile not opened return false by default: %s", e)
        return False


def convert_tiff_to_image(arch):
    """
    Convert a TIFF file to an image format supported by Pillow.

    Args:
        arch (str): Path to the TIFF file.

    Returns:
        Image: Converted image.
    """
    with tifffile.TiffFile(arch) as tif:
        img = tif.asarray()
        # Handle multi-channel TIFF images
        if img.ndim == 3 and img.shape[2] > 3:
            img = img[:, :, :3]  # Take only the first three channels
        # Convert to uint8 if necessary
        if img.dtype != np.uint8:
            img = img.astype(np.uint8)
        img = Image.fromarray(img)
    return img


def convert_cmyk_to_rgb(image):
    """Convert CMYK image to RGB format."""

    pil_image = Image.open(image)
    if 'icc_profile' in pil_image.info:
        icc_profile = pil_image.info['icc_profile']
        srgb_profile = ImageCms.createProfile("sRGB")
        cmyk_profile = ImageCms.ImageCmsProfile(BytesIO(icc_profile))

        pil_image = ImageCms.profileToProfile(
            pil_image, cmyk_profile, srgb_profile, outputMode='RGB')

    open_cv_image = np.array(pil_image)
    open_cv_image = open_cv_image[:, :, ::-1].copy()

    return open_cv_image


def resize_image(image, max_width):
    """Resize image to a maximum width."""

    height, width = image.shape[:2]
    if width <= max_width:
        return image

    ratio = max_width / width
    new_height = int(height * ratio)

    resized_image = cv2.resize(  # pylint: disable=no-member
        image, (max_width, new_height), interpolation=cv2.INTER_AREA)  # pylint: disable=no-member # noqa
    return resized_image


def save_image_as_jpeg(image, path):
    """Save image as JPEG format."""

    max_width = int(PIXEL_LIMIT)
    resized_image = resize_image(image, max_width)
    cv2.imwrite(path, resized_image, [  # pylint: disable=no-member
                int(cv2.IMWRITE_JPEG_QUALITY), int(QUALITY)])  # pylint: disable=no-member # noqa


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

    complex_tiff = False

    try:
        ext = arch.split('.')[-1].lower()
        if ext == 'psb':
            psb = psd_tools.PSDImage.open(arch)
            img = psb.topil()
        elif ext in ['tiff', 'tif']:
            complex_tiff = is_complex_tiff(arch)
            if complex_tiff:
                LOGGER.info("Complex TIFF was detected.")
                img = convert_cmyk_to_rgb(arch)
            else:
                LOGGER.info("Converting simple TIFF to image.")
                img = convert_tiff_to_image(arch)
        else:
            img = Image.open(arch)

        module = arch.replace(folder_path, '').replace('\\', '/').split('.')
        path = module[0].split('/')
        name = path[-1]
        LOGGER.info("Converting %s... with %s of quality", name, quality)

        output_path = f'{folder_destiny}/{name}.jpeg'

        if complex_tiff:
            save_image_as_jpeg(img, output_path)
        else:
            if img.mode in ('CMYK', 'RGBA', 'LA', 'P'):
                print('Converting to RGB')
                img = img.convert('RGB')

            max_dimension = int(PIXEL_LIMIT)
            if img.width > max_dimension or img.height > max_dimension:
                ratio = min(max_dimension / img.width,
                            max_dimension / img.height)
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(
                    new_size, Image.LANCZOS)  # pylint: disable=no-member

            img.save(output_path, 'JPEG', quality=quality,
                     optimize=True, progressive=True)

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
