"""
This module contains the manual function that converts a PSB file to a JPEG file.
"""

import warnings
import psd_tools
from PIL import Image, ImageFile
from src.config.config import QUALITY, PIXEL_LIMIT
ImageFile.LOAD_TRUNCATED_IMAGES = True

# Ignore warnings
warnings.filterwarnings("ignore", category=Image.DecompressionBombWarning)
warnings.filterwarnings("ignore", category=UserWarning, module='psd_tools')

def manual_conversion(arch, output_path): 
    """
    Convert a PSB file to a JPEG file
    """
    psb = psd_tools.PSDImage.open(arch)
    img = psb.topil()

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

    img.save(output_path, 'JPEG', quality=int(QUALITY),
            optimize=True, progressive=True)