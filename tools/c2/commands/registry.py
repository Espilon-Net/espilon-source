class CommandRegistry:
    def __init__(self):
        self._handlers = {}

    def register(self, handler):
        self._handlers[handler.name] = handler

    def get(self, name):
        return self._handlers.get(name)

    def list(self):
        return list(self._handlers.keys())
