""""
This module is responsible for deleting old zip files from the ZIP_PATH
directory.
"""

import os
import sched
import time
from datetime import datetime, timedelta
from src.config.config import ZIP_PATH, CLEAN_ZIP_DAYS

scheduler = sched.scheduler(time.time, time.sleep)


def delete_old_files():
    """"
    Delete old zip files from the ZIP_PATH directory.
    """
    cutoff_time = datetime.now() - timedelta(days=int(CLEAN_ZIP_DAYS))
    cutoff_timestamp = cutoff_time.timestamp()
    for filename in os.listdir(ZIP_PATH):
        file_path = os.path.join(ZIP_PATH, filename)
        if os.path.isfile(file_path):
            file_creation_time = os.path.getctime(file_path)
            if file_creation_time < cutoff_timestamp:
                try:
                    os.remove(file_path)
                    print(f'Deleted Zip File: {file_path}')
                except Exception as e:  # pylint: disable=broad-except
                    print(f'Error deleting zip {file_path}: {e}')


def clean_schedule_task():
    """""
    Schedule the task to run every
    """
    scheduler.enter(86400, 1, clean_schedule_task)
    delete_old_files()
    scheduler.run()
