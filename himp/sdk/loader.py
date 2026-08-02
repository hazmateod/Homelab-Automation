"""
SDK Loader
"""

from pathlib import Path

import yaml

from himp.models.plugin import Plugin


class SDKLoader:

    PLUGIN_DIR = Path("plugins")

    def plugins(self):

        discovered = []

        for manifest in sorted(
            self.PLUGIN_DIR.glob("*/plugin.yml")
        ):

            with manifest.open(
                encoding="utf-8",
            ) as f:

                data = yaml.safe_load(f)

            discovered.append(
                Plugin(
                    id=data["name"],
                    name=data["display_name"],
                    version=data["version"],
                    description=data["description"].strip(),
                    author=data.get("author", ""),
                    entrypoint=data.get("entrypoint", ""),
                    inventory_group=data.get(
                        "inventory_group",
                        data["name"],
                    ),
                    supports=data.get("supports", {}),
                    artifacts=data.get("artifacts", []),
                    requirements=data.get("requirements", []),
                    manifest=manifest,
                )
            )

        return discovered
