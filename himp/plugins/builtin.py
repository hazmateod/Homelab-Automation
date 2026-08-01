"""
Built-in plugins.
"""

from himp.models.plugin import Plugin


def plugins():

    return [
        Plugin(
            name="Proxmox",
            version="1.0",
            description="Proxmox VE Plugin",
        ),
        Plugin(
            name="PBS",
            version="1.0",
            description="Proxmox Backup Server Plugin",
        ),
        Plugin(
            name="Technitium",
            version="1.0",
            description="Technitium DNS Plugin",
        ),
        Plugin(
            name="Unbound",
            version="1.0",
            description="Unbound DNS Plugin",
        ),
    ]
