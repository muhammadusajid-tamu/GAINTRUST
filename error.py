import re


class Error:
    def __init__(self, body) -> None:
        self.body = body

        self.parse(body)

    def __hash__(self):
        return hash((self.code, self.context, self.message))

    def __eq__(self, err):
        return (
            self.code == err.code
            and self.context == err.context
            and self.message == err.message
        )

    def parse(self, body):
        lines = body.splitlines()
        self.diagnostic, residual, context = "", "", ""
        for line in lines:
            # err_code_match = re.search(r"error\[E[0-9]+\]", line)
            # err_nc_match = re.search(r"error: ", body)
            err_line_match = re.search(r"error(\[E\d\d\d\d\])?:", line)
            if err_line_match is not None:
                self.message = line.split(":")[-1]
                self.code = "[E-1]"
                if err_line_match.group(0) is not None:
                    self.code = err_line_match.group(0)
            elif line.startswith("-->"):
                self.location = line.split(" ")[-1]
            elif "-Ztrack-diagnostics:" in line:
                self.diagnostic = line.split("/")[1]
            elif len(line) > 2 and line[2] == "|":
                context = context + line + "\n"
            else:
                residual = residual + line + "\n"

        self.context = context
        self.residual = residual
