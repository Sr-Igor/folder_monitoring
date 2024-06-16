import os
import warnings

import psd_tools
from PIL import Image, ImageFile

from logger import LOGGER, save_to_database

# Ignore warnings
warnings.filterwarnings("ignore", category=Image.DecompressionBombWarning)

ImageFile.LOAD_TRUNCATED_IMAGES = True


def preview(arch: str, folder_path,
            folder_destiny: str = 'previews',
            graph_id: str = 'none',
            quality: int = 50) -> None:
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
        LOGGER.info("Converting %s...", name)
        # print(name)
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
