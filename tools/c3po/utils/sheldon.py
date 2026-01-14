import os
import shlex
import subprocess


class CommandError(Exception):
    def __init__(self, message):
        # Call the base class constructor with the parameters it needs
        Exception.__init__(self, message)


def call(cmd):
    cmd_lines = split_cmd(cmd)
    for line in cmd_lines:
        call_list = shlex.split(line)
        try:
            subprocess.call(call_list)

        except OSError:
            if call_list[0] == 'cd':
                try:
                    # ~ will raise CommandError, need to expand
                    if call_list[1][0] == '~':
                        call_list[1] = call_list[1].replace(
                            '~',
                            os.path.expanduser('~'))
                    os.chdir(call_list[1])
                except:
                    raise CommandError('{0} is not a valid command.'.format(call_list[0]))


def split_cmd(cmd):
    cmd_lines = cmd.splitlines()
    cmd_lines = map(lambda x: x.strip(), cmd_lines)
    cmd_lines = filter(lambda x: x != '', cmd_lines)
    return cmd_lines