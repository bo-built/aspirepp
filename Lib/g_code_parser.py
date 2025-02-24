import os
from decimal import Decimal

from settings import (
    G0_RAPID_MAX_SPEED,
    G0_RAPID_MIN_HEIGHT,
    PROCESSED_FILES_DIR
)


class ProcessingException(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return f"Fatal Processing Error: {self.message}"


class GCodeMessage(object):
    def __init__(self, line, message):
        self.line = line
        self._message = message
        if self.line:
            self.message = f"{self.level} on line #{self.line.line_number}: {self._message}"
        else:
            self.message = f"{self.level}: {self._message}"


class GCodeInfo(GCodeMessage):
    def __init__(self, line, message):
        self.level = "INFO"
        super(GCodeInfo, self).__init__(line, message)


class GCodeWarning(GCodeMessage):
    def __init__(self, line, message):
        self.level = "WARNING"
        super(GCodeWarning, self).__init__(line, message)


class GCodeError(GCodeMessage):
    def __init__(self, line, message):
        self.level = "ERROR"
        super(GCodeError, self).__init__(line, message)


class GCodeLine(object):
    def __init__(self, text_line, line_number):
        self._CODE_MAP = {
            'G0': 'RAPID MOVE',
            'G1': 'LINEAR FEED MOVE',
            'G2': 'ARC MOVE (CLOCKWISE)',
            'G3': 'ARC MOVE (COUNTER CLOCKWISE)',
            'XBLOWER': 'XBLOWER',
            'H': 'HEADER',
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

        self.code_data = text_line.split(' ')
        self.code_type = self.code_data[0]

        known_vars = ['X', 'Y', 'Z', 'I', 'J', 'V', 'T', 'S']
        if self.code_data[0] == 'H' or not self.code_data[0] in self._CODE_MAP:
            """ This is the header line, or something like F=1
                so don't change it
            """
            self.formatted_text = self.original_text

        elif self.code_data[0] == 'XBLOWER':
            """ This is an XBLOWER command, make sure it looks like
                XBLOWER E=0# T=105
                and not
                XBLOWER E=0# T105
            """
            self.command_type == 'XBLOWER'
            for bit in self.code_data:
                if bit.startswith('T') and not bit.startswith('T='):
                    self.T = bit.replace('T', '')
                    replace_str = 'T'
                elif bit.startswith('T='):
                    self.T = bit.replace('T=', '')
                    replace_str = 'T='
            self.formatted_text = self.original_text.replace(
                replace_str,
                'T=f{self.T}'
            )
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
                for var_name in known_vars:
                    if bit.startswith(var_name) and not bit.startswith(f"{var_name}="):
                        setattr(self, var_name, bit.replace(var_name, ''))
                        bit = bit.replace(var_name, f"{var_name}=")
                    elif bit.startswith(f"{var_name}="):
                        setattr(self, var_name, bit.replace(f"{var_name}=", ''))
                    self.code_data[_bit] = bit
                _bit += 1
            self.formatted_text = ' '.join(self.code_data).strip()
            if self.comment:
                self.formatted_text = f"{self.formatted_text} ;{self.comment}"


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
            self.warnings = []
            self.errors = []
            self.info = []

    def process(self):
        self.get_axis_max_values_from_file()
        self.z_warning_threshold = self.z_max_tolerance + self.z_max
        self.verify_y_max_not_zero()
        self.process_lines()
        self.check_depth_of_cuts()
        self.check_rapid_height()

    def write_new_files(self):
        self.copy_file_to_processed_files_dir('xxl')
        self.copy_file_to_processed_files_dir('pgm')

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

    def correct_rapid_speed(self):
        """
        Ensures that any G0 rapid move lines don't
        exceed the maximum setting.
        """
        _line = 0
        for line in self.file_data:
            if line.startswith('G0'):
                bits = line.split(' ')
                _bit = 0
                for bit in bits:
                    if bit.startswith('V'):
                        velocity = float(
                            bit.replace('V=', '').replace('V', '')
                        )
                        if velocity > (G0_RAPID_MAX_SPEED):
                            velocity = f"V={G0_RAPID_MAX_SPEED:.0f}"
                            self.warning.append(GCodeWarning(line, "corrected rapid speed"))
                        bits[_bit] = velocity
                    _bit += 1
                line = ' '.join(bits)
                self.file_data[_line] = line
            _line += 1

    def process_lines(self):
        _line = 0
        for line in self.file_data:
            g_code_line = GCodeLine(line, _line)
            self.processed_code_lines.append(g_code_line)
            _line += 1

    def check_rapid_height(self):
        """
        Ensures no Z coordinate in a rapid move is below G0_RAPID_MIN_HEIGHT
        """
        for line in self.processed_code_lines:
            if line.code_type == 'G0' and line.Z:
                if line.Z and Decimal(line.Z) >= 0:
                    self.errors.append(
                        GCodeError(line, "Rapid Z Height not a negative value!!!")
                    )
                    # raise ProcessingException(line, "Rapid Z Height not a negative value!!!")
                elif line.Z and abs(Decimal(line.Z)) < G0_RAPID_MIN_HEIGHT:
                    self.errors.append(
                        GCodeError(line, "Rapid Z Height below safety threshold!!!")
                    )
                    # raise ProcessingException(line, "Rapid Z Height below safety threshold!!!")

    def check_depth_of_cuts(self):
        """
        Ensures no Z coordinate is below material thickness (max_z)
        plus z_max_tolerance.
        """
        for line in self.processed_code_lines:
            if line.Z and Decimal(line.Z) > self.z_warning_threshold:
                self.errors.append(
                    GCodeError(line, "Z depth is greater than {self.z_warning_threshold:.4f}!!!")
                )
                # raise ProcessingException(line, "Z depth is greater than {self.z_warning_threshold:.4f}!!!")

    def copy_file_to_processed_files_dir(self, extension):
        """Copies a file and renames it with a new extension."""

        file_name_without_extension = os.path.splitext(
            os.path.basename(self.source_file_path)
        )[0]
        out_file_name = f"{file_name_without_extension}.{extension}"
        out_file_path = os.path.join(PROCESSED_FILES_DIR, out_file_name)
        out_file = open(out_file_path, "w+")
        out_file.write('\n'.join(self.file_data))
        out_file.close()
        self.info.append(
            GCodeInfo(None, f"File processed and copied to: {out_file_path}")
        )
        # print(f"File processed and copied to: {out_file_path}")
