from abc import ABC, abstractmethod


class CommandHandler(ABC):
    name: str = ""
    description: str = ""

    @abstractmethod
    def build(self, args: list[str]) -> bytes:
        pass
