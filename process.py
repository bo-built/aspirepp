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

""" This script takes a G Code file in XXL format and processes it to be compatible with
    an SCM Pratix S12 2015 CNC machine. It performs various checks and modifications on the
    G Code lines, such as verifying axis values, correcting rapid speeds, checking depth of cuts,
    and adding necessary machine-specific commands.

    The expected XXL format is generated from the included post-processor file for Vectric Aspire.

    The processed G Code is then compiled and written to new output files, along with a log file
    detailing any errors, warnings, or informational messages encountered during processing.

    To run, execute this script directly. A file dialog will open to select the XXL G Code file
    to process. It will put processed files in a subdirectory called "cnc_files".

    If a processed file for the given XXL file already exists, it will be overwritten.
    If ARCHIVE_PROCESSED_FILE is set to True, the existing processed file will be renamed with a
    timestamp and moved to the ARCHIVE_DIR before the new.
"""


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
