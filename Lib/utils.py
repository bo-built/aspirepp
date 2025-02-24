import os
import time

from settings import ARCHIVE_DIR

def hide_original_file(source_file_path):
    """ Changes the file extension of the processed file to .xxl_ so that processing the directory doesn't see it again """
    timestr = str(int(time.time()))
    file_base_name = os.path.splitext(os.path.basename(source_file_path))[0]
    os.rename(source_file_path, os.path.join(ARCHIVE_DIR, file_base_name + f'_{timestr}.xxl_'))
 