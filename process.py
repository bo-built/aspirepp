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
from Lib.g_code_parser_messenger import CODES


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
            gcode.write_log_file(outfile_dir)

            print_info("Processing complete. Here's what happened:")
            if gcode.errors:
                for code, instances in gcode.errors.items():
                    message = CODES[code]['message']
                    print_error(f"Error  {code} \"{message}\" On {len(instances)} lines")
            if gcode.warnings:
                for code, instances in gcode.warnings.items():
                    message = CODES[code]['message']
                    print_warning(f"Warning {code} \"{message}\" On {len(instances)} lines")
            if gcode.info:
                for code, instances in gcode.info.items():
                    line_numbers = [inst.line.line_number for inst in instances]
                    message = CODES[code]['message']
                    print_info(f"Info {code} \"{message}\" On {len(instances)} lines")
            for direct_output in gcode.direct_output:
                print_info(direct_output.message)
            print_info("Output can be found at:")
            for file in gcode.out_files:
                print_info(file)
    else:
        sys.exit(1)
