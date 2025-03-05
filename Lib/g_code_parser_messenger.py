CODES = {
    101: {"level": "error", "message": "Rapid Z Height not a negative value!!!"},
    102: {"level": "error", "message": "Z depth is greater than safety threshold!!!"},
    202: {"level": "warning", "message": "Rapid Z Height below safety threshold!!!"},
    301: {"level": "info", "message": "corrected rapid speed"},
}


class GCodeCustomMessage(object):
    def __init__(self, message):
        self.message = message


class GCodeMessage(object):
    def __init__(self, line_number, code):
        self.line_number = line_number

        self.code = code
        self.message = CODES[self.code]["message"]
        self.level = CODES[self.code]["level"].upper()
