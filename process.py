import os

from settings import SOURCE_DIR

from Lib.utils import (
    hide_original_file,
    print_error,
    print_info,
    print_warning,
)
from Lib.g_code_parser import GCodeXXL


if __name__ == '__main__':
    files = os.listdir(SOURCE_DIR)
    files_to_process = [i for i in files if i.endswith('.xxl')]

    if len(files_to_process) == 0:
        print_warning(f"No files to process. Make sure .xxl files are in {SOURCE_DIR} or change the source directory in settings.py")  # noqa
    else:
        for file_name in files_to_process:
            confirm = ''
            while confirm.strip().upper() not in ['Y', 'N']:
                confirm = input(f"Process {file_name}? [Y/N]")

            if confirm.strip().upper() == 'Y':
                print_info(f"Processing {file_name}")
                full_file_path = os.path.join(SOURCE_DIR, file_name)
                with open(full_file_path, 'r') as file:
                    file_data = file.read().split('\n')
                    gcode = GCodeXXL(full_file_path)
                    gcode.process()
                    gcode.write_new_files()
                confirm_hide_file = ''
                while confirm_hide_file.strip().upper() not in ['Y', 'N']:
                    error_count = len(gcode.errors)
                    info_count = len(gcode.info)
                    warning_count = len(gcode.warnings)
                    print_info(
                        f"Processing complete. Here's what happened:\n{error_count} errors\n{warning_count} warnings\n{info_count} info",  # noqa
                    )
                    if error_count:
                        errors = '\n'.join([error.message for error in gcode.errors])
                        print_error(f"errors:\n{errors}")
                    if warning_count:
                        warnings = '\n'.join([warnings.message for warnings in gcode.warnings])
                        print_warning(f"warnings:\n{warnings}")
                    if info_count:
                        info = '\n'.join([info.message for info in gcode.info])
                        print_info(f"info:\n{info}")

                    confirm_hide_file = input(f"Processing complete. Do you want to hide {file_name}? [Y/N]")  # noqa

                if confirm_hide_file.strip().upper() == 'Y':
                    hide_original_file(full_file_path)
            else:
                print_info(f"Skipping {file_name}")
