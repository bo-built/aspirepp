from decimal import Decimal
from pathlib import Path

from settings import (
    G0_RAPID_MAX_SPEED,
    G0_RAPID_MIN_HEIGHT,
    REMOVE_BORING_HEAD_RAPIDS,
)

from Lib.utils import get_file_basename
from Lib.g_code_parser_messenger import GCodeMessage, GCodeCustomMessage


""" Map of default G Code line prefixes and their corresponding command type. """
G_CODE_TYPE_MAP = {
    'G0': 'RAPID MOVE',
    'G1': 'LINEAR FEED MOVE',
    'G2': 'ARC MOVE (CLOCKWISE)',
    'G3': 'ARC MOVE (COUNTER CLOCKWISE)',
    'XBLOWER': 'XBLOWER',
    'C': 'C Line',
    'F': 'F Line',
    'H': 'HEADER',
    'B': 'BORING',
}


class ProcessingException(Exception):
    """ Raised when a fatal error occurs during processing of the G code file,
        Such as a missing origin coordinate.
    """
    def __init__(self, message, code=000):
        self.message = message

    def __str__(self):
        return f"Fatal Processing Error: {self.message}"


class GCodeDummyLine(object):
    """ This class represents a dummy line of G code that is inserted into the
        processed code lines list.  It is used to insert lines that are not part
        of the original G code file, but are needed for processing.
    """
    def __init__(self, code_type, text_line, line_number):
        self.line_number = line_number
        self.original_text = text_line
        self.formatted_text = text_line
        self.code_type = code_type
        self.command_type = G_CODE_TYPE_MAP[code_type]
        self.comment = None
        self.X = None
        self.Y = None
        self.Z = None
        self.I = None  # noqa: ambiguous variable
        self.J = None
        self.S = None
        self.V = None
        self.T = None
        self.Tool = None


class GCodeLine(object):
    """ This class represents a single line of G code and is responsible for
        parsing the line into its components.  It also formats the line for output.
    """
    def __init__(self, text_line, line_number):

        self.line_number = line_number + 1
        self.original_text = text_line
        self.formatted_text = ''
        self.code_type = None
        self.command_type = None
        self.comment = None
        self.X = None
        self.Y = None
        self.Z = None
        self.I = None  # noqa: ambiguous variable
        self.J = None
        self.S = None
        self.V = None
        self.T = None
        self.Tool = None

        self.code_data = text_line.split(' ')
        self.code_type = self.code_data[0]

        self.known_vars = ['X', 'Y', 'Z', 'I', 'J', 'V', 'T', 'S']
        if self.code_data[0] == 'H' or not self.code_data[0] in G_CODE_TYPE_MAP:
            """ This is the header line so don't change it
            """
            self.formatted_text = self.original_text
        elif self.code_data[0].startswith('C'):
            self.code_type = 'C'
            self.command_type = G_CODE_TYPE_MAP['C']
        elif self.code_data[0].startswith('F'):
            self.code_type = 'F'
            self.command_type = G_CODE_TYPE_MAP['F']
        elif self.code_data[0] == 'XBLOWER':
            """ This is an XBLOWER command, make sure it looks like
                XBLOWER E=0# T=105
                and not
                XBLOWER E=0# T105
                or
                XBLOWER E=0# T=T105
            """
            self.command_type == 'XBLOWER'
            tool_var = ''
            for bit in self.code_data:
                if bit.startswith('T=T'):
                    replace_str = 'T=T'
                    tool_var = bit
                elif bit.startswith('T='):
                    replace_str = 'T='
                    tool_var = bit
                elif bit.startswith('T'):
                    replace_str = 'T'
                    tool_var = bit
            self.T = tool_var.replace(replace_str, '')
            self.Tool = int(self.T)
        else:
            """ This should be a normal G code command, make sure it looks like
                G2 X=##.#### Y=##.#### Z=##.#### I=##.#### J=##.#### ; COMMENT
            """
            self.command_type = G_CODE_TYPE_MAP[self.code_type]
            if ';' in self.original_text:
                line_parts = self.original_text.split(';')
                self.comment = line_parts[1]
                code_parts = line_parts[0]
                self.code_data = code_parts.split(' ')

            _bit = 0
            for bit in self.code_data:
                for var_name in self.known_vars:
                    if bit.startswith(var_name) and not bit.startswith(f"{var_name}="):
                        setattr(self, var_name, bit.replace(var_name, ''))
                        bit = bit.replace(var_name, f"{var_name}=")
                    elif bit.startswith(f"{var_name}="):
                        setattr(self, var_name, bit.replace(f"{var_name}=", ''))
                    self.code_data[_bit] = bit
                _bit += 1
            if self.code_type.startswith('G') and self.code_type != 'G0':
                self.Y = self.Y.replace('-', '')

        if self.T and self.T.startswith("T"):
            self.T = self.T.replace("T", "")
            self.Tool = int(self.T.replace("T", ""))
        elif self.T:
            self.Tool = int(self.T)

        self.format_print_line()

    def format_variables_into_print_line(self):
        var_strings = []
        for var in self.known_vars:
            var_val = getattr(self, var)
            if var_val:
                var_strings.append(f"{var}={var_val}")
        if var_strings:
            var_string = ' '.join(var_strings)
            self.formatted_text = f"{self.code_type} {var_string}"
        else:
            self.formatted_text = self.formatted_text

        if self.comment:
            self.formatted_text = f"{self.formatted_text} ; {self.comment}"

    def format_print_line(self):
        if self.code_type == 'XBLOWER':
            self.formatted_text = f"XBLOWER E=0# T={self.Tool}"
        elif self.code_type == "C":
            self.formatted_text = "C=0"
        elif self.code_type == "F":
            self.formatted_text = "F=1"
        elif self.code_type == "H":
            self.formatted_text = self.formatted_text
        else:
            self.format_variables_into_print_line()

    def change_to_boring_operation(self, current_bore_tool, current_spindle_speed):
        self.code_type = 'B'
        if not self.T:
            self.T = current_bore_tool
            self.Tool = current_bore_tool
        if not self.S:
            self.S = current_spindle_speed
        self.command_type = G_CODE_TYPE_MAP['B']
        self.format_variables_into_print_line()


class GCodeXXL(object):
    """ This class represents a G Code file in XXL format.
        Each line is parsed and formatted for the SCM Machine as a GCodeLine object.
    """

    def __init__(self, source_file_path, z_max_tolerance=None):
        """ Open the source file and initiate the GCodeXXL object with properties
            for formatting helper functions.
        """
        self.source_file_path = source_file_path
        with open(source_file_path, 'r') as file:
            self.x_max = Decimal(0)
            self.y_max = Decimal(0)
            self.z_max = Decimal(0)
            self.y_max_original_value = ''
            if z_max_tolerance:
                self.z_max_tolerance = Decimal(z_max_tolerance)
            else:
                self.z_max_tolerance = Decimal(.006)

            self.file_data = file.read().split('\n')
            self.file_header = self.file_data[0]
            self.processed_code_lines = []
            self.compiled_lines = ''
            self.warnings = {}
            self.errors = {}
            self.info = {}
            self.direct_output = []
            self.out_files = []
            self.log_file = ''

    def process(self):
        """ This is the main processing function. Once the file has been
            loaded by __init__, this function will call all the necessary
            helper functions to format the file contents into G Code that is
            compatible with the SCM CNC machine.
        """
        self.get_axis_max_values_from_file()
        self.z_warning_threshold = self.z_max_tolerance + self.z_max
        self.verify_y_max_not_zero()
        self.process_lines()
        self.check_depth_of_cuts()
        self.check_rapid_height()
        self.correct_rapid_speed()
        self.update_code_for_boring_head()
        self.add_x_blower()

    def add_error(self, code, line):
        """ Adds an error message to the errors dictionary. """
        code_errors = self.errors.get(code, [])
        code_errors.append(GCodeMessage(line_number=line.line_number, code=code))
        self.errors[code] = code_errors

    def add_warning(self, code, line):
        """ Adds a warning message to the warnings dictionary. """
        code_warnings = self.warnings.get(code, [])
        code_warnings.append(GCodeMessage(line_number=line.line_number, code=code))
        self.warnings[code] = code_warnings

    def add_info(self, code, line):
        """ Adds an info message to the info dictionary. """
        code_infos = self.info.get(code, [])
        code_infos.append(GCodeMessage(line_number=line.line_number, code=code))
        self.info[code] = code_infos

    def add_direct_output(self, message):
        """ Adds a direct output message to the direct_output list. """
        self.direct_output.append(GCodeCustomMessage(message))

    def compile_formatted_lines(self):
        """ Compiles the formatted lines into a single string for output.
            Individual lines are separated by a newline character.
        """
        self.compiled_lines = '\n'.join([line.formatted_text for line in self.processed_code_lines])

    def get_axis_max_values_from_file(self):
        """ Parse the file header and find the X,Y,Z Max values """
        bits = self.file_header.split(' ')
        for bit in bits:
            if bit.startswith('DX'):
                self.x_max = Decimal(bit.replace('DX', ''))
            elif bit.startswith('DZ'):
                self.z_max = Decimal(bit.replace('DZ', ''))
            elif bit.startswith('DY'):
                self.y_max_original_value = bit
                self.y_max = Decimal(bit.replace('DY', ''))

    def verify_y_max_not_zero(self):
        """ Detects if value of Y MAX in the file is 0 and prompts for a value if it is 0.
        """
        if self.y_max is None:
            raise ProcessingException("Could not find Y value")

        input_y_string = ''
        if self.y_max <= 0:
            input_y_value = 0
            while self.y_max <= 0:
                input_y_value = input("DY is not set. What is the material Max Y value? [00.000]")
                try:
                    self.y_max = Decimal(input_y_value)
                    input_y_string = f"DY{self.y_max:.3f}"
                    print(f"Setting Y as {self.y_max}")
                except:  # noqa: TODO catch specific exception here
                    print("Enter a number!")
                    input_y_value = 0
            self.file_header = self.file_header.replace(
                self.y_max_original_value,
                input_y_string
            )
            self.file_data[0] = self.file_header

    def process_lines(self):
        """ Loop through each line of the source file and create a GCodeLine
            object for each line. once processed as a GCodeLine object, the
            line is added to the processed_code_lines list.
        """
        _line = 0
        for line in self.file_data:
            g_code_line = GCodeLine(line, _line)
            self.processed_code_lines.append(g_code_line)
            _line += 1

    def correct_rapid_speed(self):
        """ Ensures that any G0 rapid move lines don't exceed the maximum setting.
        """
        _line = 0
        for line in self.processed_code_lines:
            if line.code_type == 'G0' and line.V:
                velocity = Decimal(line.V)
                if velocity > (G0_RAPID_MAX_SPEED):
                    line.V = G0_RAPID_MAX_SPEED
                    self.add_warning(line=line, code=301)
            _line += 1

    def check_rapid_height(self):
        """ Ensures no Z coordinate in a rapid move is below G0_RAPID_MIN_HEIGHT """
        for line in self.processed_code_lines:
            if line.code_type == 'G0' and line.Z:
                if line.Z and Decimal(line.Z) >= 0:
                    self.add_error(line=line, code=101)
                elif line.Z and abs(Decimal(line.Z)) < G0_RAPID_MIN_HEIGHT:
                    self.add_warning(line=line, code=202)

    def check_depth_of_cuts(self):
        """ Ensures no Z coordinate is below material thickness (max_z) plus z_max_tolerance. """
        for line in self.processed_code_lines:
            if line.Z and Decimal(line.Z) > self.z_warning_threshold:
                self.add_error(line=line, code=102)

    def update_code_for_boring_head(self):
        """ Turns operations which use the boring head into
            B coded lines and removes them if they are rapids to make the
            G Code compatible with the SCM CNC machine.
        """
        current_tool = None
        current_bore_tool = None
        current_spindle_speed = None
        del_lines = []
        line_count = 0
        boring_map = []
        for line in self.processed_code_lines:
            if line.Tool and line.Tool != current_tool:
                current_tool = line.Tool
                # print(f"setting current tool to {line.Tool}; {line.formatted_text}")
            if current_tool and current_tool < 100:
                if line.code_type == 'G0':
                    current_spindle_speed = line.S
                    # print(f"Handling boring rapid - {line.original_text}")
                    current_bore_tool = line.Tool
                    if REMOVE_BORING_HEAD_RAPIDS:
                        del_lines.append(line)
                    else:
                        line.formatted_text = f";*******BORING HEAD {line.formatted_text}************"  # noqa: line too long
                elif line.code_type.startswith('G'):
                    line.change_to_boring_operation(current_bore_tool, current_spindle_speed)
                    line_count += 1
                    if (line.X, line.Y) not in boring_map:
                        boring_map.append((line.X, line.Y))

        self.add_direct_output(
            f"Deleted illegal rapid from boring head operation on {len(del_lines)} lines."
        )
        self.add_direct_output(f"Converted {len(boring_map)} lines to boring head operation code.")

        for deleteme in del_lines:
            self.processed_code_lines.remove(deleteme)

    def add_x_blower(self):
        """ Inserts an XBLOWER and C line ahead of any new G0 operation.
            These are machine specific commands that are required for the SCM CNC machine to
            operate correctly.
        """
        _index = 0
        current_code_type = None
        insert_points = []
        insert_lines = []
        for line in self.processed_code_lines:
            if line.code_type != current_code_type and line.code_type == 'G0':
                x_dummy_line = GCodeDummyLine('XBLOWER', f'XBLOWER E=0# T={line.T}', _index)
                c_dummy_line = GCodeDummyLine('C', 'C=0', _index)
                insert_lines.append((x_dummy_line, c_dummy_line))
                insert_points.append(_index)
            current_code_type = line.code_type
            _index += 1
        insert_points.reverse()
        insert_lines.reverse()
        ip = 0
        for point in insert_points:
            self.processed_code_lines.insert(point, insert_lines[ip][0])
            self.processed_code_lines.insert(point + 1, insert_lines[ip][1])
            ip += 1

    def copy_file_to_processed_files_dir(self, extension, target_dir):
        """Copies a file and renames it with a new extension."""
        basename = get_file_basename(self.source_file_path)
        out_file_path = Path(f"{target_dir}\\{basename}.{extension}")
        out_file = open(out_file_path, "w+")
        out_file.write(self.compiled_lines)
        out_file.close()
        self.out_files.append(out_file_path)

    def write_new_files(self, target_dir):
        """ Creates a .xxl file and a .pgm file in the output directory.
            The files are identical, but both are required for Xilog to
            successfully load the G Code into the SCM Machine's controller.
        """
        self.copy_file_to_processed_files_dir('xxl', target_dir)
        self.copy_file_to_processed_files_dir('pgm', target_dir)

    def write_log_file(self, target_dir):
        """ Write a log file with all errors, warnings, and info messages.  This is useful for
            debugging and for keeping a record of what was processed in the G Code file.
        """
        log_lines = []
        msg_types = ['errors', 'warnings', 'info']
        for mtype in msg_types:
            self_prop = getattr(self, mtype)
            for code, instances in self_prop.items():
                for inst in instances:
                    if inst.line_number:
                        message = f"{inst.level} {code}: \"{inst.message}\" on line #{inst.line_number}"  # noqa: line too long
                    else:
                        message = f"{inst.level} {code}: \"{inst.message}\""
                    log_lines.append(message)

        basename = get_file_basename(self.source_file_path)
        out_file_path = Path(f"{target_dir}\\{basename}.log.txt")
        out_file = open(out_file_path, "w+")
        out_file.write("\n".join(log_lines))
        out_file.close()
        self.out_files.append(out_file_path)
