from decimal import Decimal
from pathlib import Path

from settings import (
    G0_RAPID_MAX_SPEED,
    G0_RAPID_MIN_HEIGHT,
    REMOVE_BORING_HEAD_RAPIDS,
)

from Lib.utils import get_file_basename
from Lib.g_code_parser_errors import GCodeMessage


class ProcessingException(Exception):
    def __init__(self, message, code=000):
        self.message = message

    def __str__(self):
        return f"Fatal Processing Error: {self.message}"


class GCodeLine(object):
    def __init__(self, text_line, line_number):
        self._CODE_MAP = {
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
        if self.code_data[0] == 'H' or not self.code_data[0] in self._CODE_MAP:
            """ This is the header line so don't change it
            """
            self.formatted_text = self.original_text
        elif self.code_data[0].startswith('C'):
            self.code_type = 'C'
            self.command_type = self._CODE_MAP['C']
        elif self.code_data[0].startswith('F'):
            self.code_type = 'F'
            self.command_type = self._CODE_MAP['F']
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
            self.command_type = self._CODE_MAP[self.code_type]
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
        self.command_type = self._CODE_MAP['B']
        self.format_variables_into_print_line()


class GCodeXXL(object):
    def __init__(self, source_file_path, z_max_tolerance=None):
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
            self.out_files = []
            self.log_file = ''

    def add_error(self, code, line):
        code_errors = self.errors.get(code, [])
        code_errors.append(GCodeMessage(line=line, code=code))
        self.errors[code] = code_errors

    def add_warning(self, code, line):
        code_warnings = self.warnings.get(code, [])
        code_warnings.append(GCodeMessage(line=line, code=code))
        self.warnings[code] = code_warnings

    def add_info(self, code, line):
        code_infos = self.info.get(code, [])
        code_infos.append(GCodeMessage(line=line, code=code))
        self.info[code] = code_infos

    def process(self):
        self.get_axis_max_values_from_file()
        self.z_warning_threshold = self.z_max_tolerance + self.z_max
        self.verify_y_max_not_zero()
        self.process_lines()
        self.check_depth_of_cuts()
        self.check_rapid_height()
        self.correct_rapid_speed()
        self.update_code_for_boring_head()

    def compile_formatted_lines(self):
        self.compiled_lines = '\n'.join([line.formatted_text for line in self.processed_code_lines])

    def write_new_files(self, target_dir):
        self.copy_file_to_processed_files_dir('xxl', target_dir)
        self.copy_file_to_processed_files_dir('pgm', target_dir)

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
        """
        Detects if value of Y MAX in the file is 0 and prompts for a value
        if it is 0.
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
        _line = 0
        for line in self.file_data:
            g_code_line = GCodeLine(line, _line)
            self.processed_code_lines.append(g_code_line)
            _line += 1

    def correct_rapid_speed(self):
        """
        Ensures that any G0 rapid move lines don't
        exceed the maximum setting.
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
        """
        Ensures no Z coordinate in a rapid move is below G0_RAPID_MIN_HEIGHT
        """
        for line in self.processed_code_lines:
            if line.code_type == 'G0' and line.Z:
                if line.Z and Decimal(line.Z) >= 0:
                    self.add_error(line=line, code=101)
                elif line.Z and abs(Decimal(line.Z)) < G0_RAPID_MIN_HEIGHT:
                    self.add_warning(line=line, code=202)

    def check_depth_of_cuts(self):
        """
        Ensures no Z coordinate is below material thickness (max_z)
        plus z_max_tolerance.
        """
        for line in self.processed_code_lines:
            if line.Z and Decimal(line.Z) > self.z_warning_threshold:
                self.add_error(line=line, code=102)
                # raise ProcessingException(line, "Z depth is greater than {self.z_warning_threshold:.4f}!!!")

    def update_code_for_boring_head(self):
        current_tool = None
        current_bore_tool = None
        current_spindle_speed = None
        del_lines = []
        for line in self.processed_code_lines:
            if line.Tool and line.Tool != current_tool:
                current_tool = line.Tool
                # print(f"setting current tool to {line.Tool}; {line.formatted_text}")
            if current_tool and current_tool < 100:
                if line.code_type == 'G0':
                    current_spindle_speed = line.S
                    # print(f"Handling boring rapid - {line.original_text}")
                    current_bore_tool = line.Tool
                    # self.warnings.append(GCodeWarning(line, "This is a boring head operation, rapid not needed?"))  # noqa
                    if REMOVE_BORING_HEAD_RAPIDS:
                        del_lines.append(line)
                    else:
                        line.formatted_text = f";*******BORING HEAD {line.formatted_text}************"
                elif line.code_type.startswith('G'):
                    line.change_to_boring_operation(current_bore_tool, current_spindle_speed)
        for deleteme in del_lines:
            self.processed_code_lines.remove(deleteme)

    def copy_file_to_processed_files_dir(self, extension, target_dir):
        """Copies a file and renames it with a new extension."""
        basename = get_file_basename(self.source_file_path)
        out_file_path = Path(f"{target_dir}\\{basename}.{extension}")
        out_file = open(out_file_path, "w+")
        out_file.write(self.compiled_lines)
        out_file.close()
        self.out_files.append(out_file_path)

    def write_log_file(self, target_dir):
        import pdb
        pdb.set_trace()
        log_lines = []
        msg_types = ['errors', 'warnings', 'info']
        for mtype in msg_types:
            self_prop = getattr(self, mtype)
            for code, instances in self_prop.items():
                for inst in instances:
                    message = f"ERROR {code}: \"{inst.message}\" on line #{inst.line.line_number}"
                    log_lines.append(message)

        basename = get_file_basename(self.source_file_path)
        out_file_path = Path(f"{target_dir}\\{basename}.log.txt")
        out_file = open(out_file_path, "w+")
        out_file.write("\n".join(log_lines))
        out_file.close()
        self.out_files.append(out_file_path)

        # self.info.append(
        #     GCodeInfo(None, f"File processed and copied to: {out_file_path}")
        # )
        # print(f"File processed and copied to: {out_file_path}")
