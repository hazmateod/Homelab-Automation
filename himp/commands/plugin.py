"""
Plugin Commands
"""

from himp.plugins.loader import PluginLoader
from himp.lib.output import error


def run(args):

    if not args.name:
        error("Plugin name is required.")
        return

    loader = PluginLoader()

    plugin = loader.find(args.name)

    if plugin is None:
        error(f"Plugin '{args.name}' not found.")
        return

    print(f"Name         : {plugin.name}")
    print(f"Version      : {plugin.version}")
    print(f"Author       : {plugin.author}")
    print(f"Description  : {plugin.description}")
    print(f"Entrypoint   : {plugin.entrypoint}")
    print(f"Enabled      : {plugin.is_enabled()}")

    print()
    print("Supports")
    print("--------")

    for capability, enabled in sorted(plugin.supports.items()):
        print(f"{capability:<12} : {enabled}")

    print()
    print("Requirements")
    print("------------")

    for requirement in plugin.requirements:
        print(requirement)

    print()
    print("Artifacts")
    print("---------")

    for artifact in plugin.artifacts:
        print(artifact)
