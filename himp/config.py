#!/usr/bin/env python3
"""
HIMP Configuration Loader
"""

from pathlib import Path
import yaml


class Config:

    def __init__(self, filename="config/config.yml"):
        config_path = Path(filename)

        if not config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {config_path}"
            )

        with open(config_path, "r", encoding="utf-8") as f:
            self.data = yaml.safe_load(f)

    def section(self, name):
        return self.data.get(name, {})

