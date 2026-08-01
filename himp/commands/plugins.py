"""
Plugin Commands
"""

from himp.models.plugin_manager import PluginManager


def run(args):

    manager = PluginManager()

    print("HIMP Plugins")
    print("============")
    print()

    print(
        f"{'Name':<15} "
        f"{'Version':<10} "
        f"{'Enabled':<10} "
        f"Description"
    )

    print("-" * 70)

    for plugin in manager.all():

        print(
            f"{plugin.name:<15} "
            f"{plugin.version:<10} "
            f"{str(plugin.is_enabled()):<10} "
            f"{plugin.description}"
        )
