CODES = {
    101: {"level": "error", "message": "Rapid Z Height not a negative value!!!"},
    102: {"level": "error", "message": "Z depth is greater than safety threshold!!!"},
    202: {"level": "warning", "message": "Rapid Z Height below safety threshold!!!"},
    301: {"level": "info", "message": "corrected rapid speed"},
}


class GCodeMessage(object):
    def __init__(self, line, code):
        self.line = line

        self.code = code
        self.message = CODES[self.code]["message"]
        self.level = CODES[self.code]["level"]


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
