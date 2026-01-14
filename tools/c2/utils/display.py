import time
from utils.constant import _color

class Display:
    @staticmethod
    def _timestamp() -> str:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    @staticmethod
    def system_message(message: str):
        print(f"{Display._timestamp()} {_color('CYAN')}[SYSTEM]{_color('RESET')} {message}")

    @staticmethod
    def device_event(device_id: str, event: str):
        print(f"{Display._timestamp()} {_color('YELLOW')}[DEVICE:{device_id}]{_color('RESET')} {event}")

    @staticmethod
    def command_sent(device_id: str, command_name: str, request_id: str):
        print(f"{Display._timestamp()} {_color('BLUE')}[CMD_SENT:{request_id}]{_color('RESET')} To {device_id}: {command_name}")

    @staticmethod
    def command_response(request_id: str, device_id: str, response: str):
        print(f"{Display._timestamp()} {_color('GREEN')}[CMD_RESP:{request_id}]{_color('RESET')} From {device_id}: {response}")

    @staticmethod
    def error(message: str):
        print(f"{Display._timestamp()} {_color('RED')}[ERROR]{_color('RESET')} {message}")

    @staticmethod
    def cli_prompt():
        return f"\n{_color('BLUE')}c2:> {_color('RESET')}"

    @staticmethod
    def format_duration(seconds: float) -> str:
        seconds = int(seconds)
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        d, h = divmod(h, 24)

        if d > 0:
            return f"{d}d {h}h {m}m"
        if h > 0:
            return f"{h}h {m}m {s}s"
        if m > 0:
            return f"{m}m {s}s"
        return f"{s}s"

    @staticmethod
    def format_timestamp(timestamp: float) -> str:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))

    @staticmethod
    def print_table_header(headers: list):
        header_str = ""
        for header in headers:
            header_str += f"{header:<18}"
        print(header_str)
        print("-" * (len(headers) * 18))

    @staticmethod
    def print_table_row(columns: list):
        row_str = ""
        for col in columns:
            row_str += f"{str(col):<18}"
        print(row_str)
