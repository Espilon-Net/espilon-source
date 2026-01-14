import os
import sys

# Add tools/c2/ to sys.path to import c2_pb2
sys.path.insert(0, os.path.abspath('./tools/c2'))

from commands.base import CommandHandler
from proto import c2_pb2


class RebootCommand(CommandHandler):
    name = "reboot"
    description = "Reboot ESP"

    def build(self, args):
        # For the new c2_pb2.Command, we need device_id and request_id.
        # These will be filled by the CLI's _send_command method.
        # Here, we just prepare the command_name and argv.
        # The actual c2_pb2.Command object will be constructed in NewCLI._send_command
        # and then serialized, encrypted, and sent.
        # This build method is now primarily for command validation and argument parsing
        # if the command had specific arguments. For reboot, it's simple.
        
        # The build method in the old CLI was expected to return serialized bytes.
        # In the new design, the CLI will construct the full c2_pb2.Command.
        # For now, we'll return the command name and args, which NewCLI will use.
        return {"command_name": self.name, "argv": args}
