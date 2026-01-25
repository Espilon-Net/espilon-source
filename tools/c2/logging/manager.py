from utils.constant import _color


class LogManager:
    def handle(self, log):
        level = "INFO"
        color = "GREEN"

        if log.log_error_code != 0:
            level = f"ERROR:{log.log_error_code}"
            color = "RED"

        print(
            f"{_color(color)}"
            f"[ESP:{log.id}][{log.tag}][{level}] {log.log_message}"
            f"{_color('RESET')}"
        )
