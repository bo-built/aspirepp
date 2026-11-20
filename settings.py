# Name of subdirectory that will be created next to source XXl file
# for processed files to be written to
PROCESSED_FILES_DIR_NAME = "cnc_files"

# Global location to save archived files
ARCHIVE_DIR = r"C:\Users\bo\OneDrive\Documents\AspireOut\Archive\\"

# Replaces any rapid speeds over this amount with this amount
G0_RAPID_MAX_SPEED = 400 * 24.5

# warns if a rapid move is below this height
G0_RAPID_MIN_HEIGHT = .25

# If True, a processed file gets renamed with a timestamp and moved to ARCHIVE_DIR
ARCHIVE_PROCESSED_FILE = True

# If False, boring head rapids will be commented but remain in the output file
REMOVE_BORING_HEAD_RAPIDS = True
