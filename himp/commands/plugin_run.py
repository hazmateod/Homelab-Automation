"""
Plugin Run Commands
"""

from himp.lib.output import error
from himp.sdk.runner import PluginRunner


def run(args):

    runner = PluginRunner()

    success = runner.run(args.name)

    if success:
        print(f"Plugin '{args.name}' executed successfully.")
    else:
        error(f"Plugin '{args.name}' failed.")
