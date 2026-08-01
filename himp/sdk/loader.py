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
                    name=data["display_name"],
                    version=data["version"],
                    description=data["description"].strip(),
                )
            )

        return discovered
