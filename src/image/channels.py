"""
This module contains functions to convert a tif image to a jpeg image.
"""

import subprocess
from src.config.config import MAGIC_PATH


def run_conversion(input_file, output_file, quality=75, resize=800, subsampling='4:2:0'):  # noqa
    """
    Convert a tif image to a jpeg image with specified quality and resize.
    """
    magick_path = MAGIC_PATH

    command = [
        magick_path, 'convert',
        input_file,
        '-profile', 'sRGB.icc',
        '-resize', str(resize) + 'x' + str(resize),
        '-sampling-factor', subsampling,
        '-quality', str(quality),
        '-strip',
        '-interlace', 'JPEG',
        output_file
    ]

    try:
        subprocess.run(command, check=True,
                       text=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print(f"Error in magick convert: {e}")
        print(e.stderr)
