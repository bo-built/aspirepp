import os
import time

from pathlib import Path
from termcolor import colored

from settings import ARCHIVE_DIR, PROCESSED_FILES_DIR_NAME


def print_error(text):
    print(colored(text, "red"))


def print_warning(text):
    print(colored(text, "yellow"))


def print_info(text):
    print(colored(text, "blue"))


def hide_original_file(source_file_path):
    """ Changes the file extension of the processed file to .xxl_ so that processing the directory
        doesn't see it again
    """
    timestr = str(int(time.time()))
    file_base_name = os.path.splitext(os.path.basename(source_file_path))[0]
    os.rename(source_file_path, os.path.join(ARCHIVE_DIR, file_base_name + f'_{timestr}.xxl_'))


def file_extension_is_xxl(filename):
    """ Boolean test if given filename has xxl extension """
    pth = Path(filename)
    return pth.suffix.lower() == '.xxl'


def upsert_processed_files_dir(infile_path):
    pth = Path(infile_path)
    process_dir = Path(f"{pth.parent}\\{PROCESSED_FILES_DIR_NAME}")
    process_dir.mkdir(exist_ok=True)
    return process_dir


def get_file_basename(file):
    pth = Path(file)
    return pth.name.split('.')[0]
