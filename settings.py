SOURCE_DIR = r"C:\Users\bo\OneDrive\Documents\AspireOut\\"
PROCESSED_FILES_DIR = r"C:\Users\bo\OneDrive\Documents\AspireOut\Processed\\"
PROCESSED_FILES_DIR_NAME = "cnc_files"
ARCHIVE_DIR = r"C:\Users\bo\OneDrive\Documents\AspireOut\Archive\\"
G0_RAPID_MAX_SPEED = 400 * 24.5  # Replaces any rapid speeds over this amount with this amount
G0_RAPID_MIN_HEIGHT = .25  # warns if a rapid move is below this height
ARCHIVE_PROCESSED_FILE = True  # If True, a processed file gets renamed with a timestamp and moved to ARCHIVE_DIR
REMOVE_BORING_HEAD_RAPIDS = True  # If False, boring head rapids will be commented but remain in the output file
