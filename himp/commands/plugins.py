"""
Plugin Commands
"""

from himp.plugins.loader import PluginLoader


def run(args):

    loader = PluginLoader()

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

    for plugin in loader.plugins():

        print(
            f"{plugin.name:<15} "
            f"{plugin.version:<10} "
            f"{str(plugin.is_enabled()):<10} "
            f"{plugin.description}"
        )
