"""
Plugin validation checks.
"""


def plugin_directory(plugin):

    return (
        plugin.directory is not None
        and plugin.directory.exists()
    )


def manifest(plugin):

    return (
        plugin.manifest is not None
        and plugin.manifest.exists()
    )


def name(plugin):

    return bool(plugin.name)


def version(plugin):

    return bool(plugin.version)


def description(plugin):

    return bool(plugin.description)


def entrypoint(plugin):

    return bool(plugin.entrypoint)


def entrypoint_file(plugin):

    return (
        plugin.entrypoint_path is not None
        and plugin.entrypoint_path.exists()
    )


def requirements(plugin):

    return plugin.requirement_count() > 0


def artifacts(plugin):

    return plugin.artifact_count() > 0


def health(plugin):

    return hasattr(plugin, "health")
