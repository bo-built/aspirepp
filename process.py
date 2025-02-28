import tkinter as tk
from tkinter import filedialog
import sys

from Lib.utils import (
    print_error,
    print_info,
    print_warning,
    file_extension_is_xxl,
    upsert_processed_files_dir,
)
from Lib.g_code_parser import GCodeXXL


def open_file_dialog():
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    file_path = filedialog.askopenfilename()
    return file_path


if __name__ == "__main__":
    selected_file = open_file_dialog()
    if selected_file:
        # print(selected_file)
        # sys.exit(0)
        if not file_extension_is_xxl(selected_file):
            ''' Bail if it isn't an XXL file '''
            print_error(f"{selected_file} is not an XXL file. Try again.")
            sys.exit(1)
        print_info(f"Processing {selected_file}")
        outfile_dir = upsert_processed_files_dir(selected_file)
        with open(selected_file, 'r') as file:
            file_data = file.read().split('\n')
            gcode = GCodeXXL(selected_file)
            gcode.process()
            gcode.compile_formatted_lines()
            gcode.write_new_files(outfile_dir)

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

    else:
        sys.exit(1)
