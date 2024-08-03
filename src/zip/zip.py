"""
Module for creating a ZIP archive from specified files.

This module provides functionality to create a ZIP archive containing specific files. # noqa
It calculates the compression ratio and logs relevant information during the process.

Functions:
- create_zip_from_files(file_paths):
    Creates a ZIP archive with files specified by file_paths.
    Args:
        file_paths (list): List of file paths to include in the ZIP archive.

    Returns:
        str: Path to the created ZIP archive.

Logging:
    The module logs various details during the creation process using a logger named LOGGER.
    It logs:
    - Creation of the ZIP file and its path.
    - Total size of original files included in the ZIP.
    - Addition of each file to the ZIP, including file name, archive name, current ZIP size,
      and compression percentage.
    - Final details after ZIP creation, including final ZIP size and total compression ratio.
"""

import os
import zipfile
import tempfile
from src.logs.logger import LOGGER as logger


def create_zip_from_files(file_paths):
    """
    Create a ZIP archive with the specified files.

    Args:
        file_paths (list): List of file paths to include in the ZIP archive.

    Returns:
        str: Path to the created ZIP archive.
    """
    zip_path = tempfile.mktemp(suffix='.zip')
    logger.info('Creating ZIP file at: %s', zip_path)

    total_original_size = sum(os.path.getsize(file_path)
                              for file_path in file_paths if os.path.isfile(file_path))  # noqa
    logger.info('Total size of original files: %.2f MB',
                total_original_size / (1024 * 1024))

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_f:
        for file_path in file_paths:
            if os.path.isfile(file_path):
                arc_name = os.path.basename(file_path)
                zip_f.write(file_path, arc_name)

                # Calculate the size of the ZIP file after each addition
                zip_f_size = os.path.getsize(zip_path)
                logger.info('Added %s to ZIP. Current ZIP size: %.2f MB',
                            arc_name, zip_f_size / (1024 * 1024))
            else:
                logger.warning('File not found or invalid path: %s',
                               file_path)

    return zip_path
