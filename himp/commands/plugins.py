"""
Plugin Commands
"""

from himp.plugins.loader import PluginLoader


def run(args):

    loader = PluginLoader()

    plugins = loader.plugins()

    enabled = len(loader.enabled())
    disabled = len(loader.disabled())

    print("HIMP Plugins")
    print("============")
    print()

    print(f"Total Plugins : {len(plugins)}")
    print(f"Enabled       : {enabled}")
    print(f"Disabled      : {disabled}")

    print()

    print(
        f"{'ID':<12} "
        f"{'Name':<28} "
        f"{'Version':<8} "
        f"{'Enabled':<8}"
    )

    print("-" * 64)

    for plugin in plugins:

        print(
            f"{plugin.id:<12} "
            f"{plugin.name:<28} "
            f"{plugin.version:<8} "
            f"{str(plugin.is_enabled()):<8}"
        )
