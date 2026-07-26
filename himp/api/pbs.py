#!/usr/bin/env python3
"""
HIMP - Proxmox Backup Server API Client
"""

from __future__ import annotations

from urllib.parse import urljoin

import requests

from himp.config import Config


class PBSClient:
    """Proxmox Backup Server REST API client."""

    def __init__(
        self,
        host: str,
        token_id: str,
        token_secret: str,
        verify_ssl: bool = False,
    ):
        self.host = host
        self.token_id = token_id
        self.token_secret = token_secret

        self.base_url = f"https://{host}:8007/api2/json/"

        self.session = requests.Session()
        self.session.verify = verify_ssl

        self.session.headers.update(
            {
                "Authorization": f"PBSAPIToken={token_id}={token_secret}"
            }
        )

    @classmethod
    def from_config(cls, filename="config/config.yml"):
        cfg = Config(filename)
        pbs = cfg.section("pbs")

        return cls(
            host=pbs["host"],
            token_id=pbs["token_id"],
            token_secret=pbs["token_secret"],
            verify_ssl=pbs.get("verify_ssl", False),
        )

    def get(self, endpoint):
        response = self.session.get(
            urljoin(self.base_url, endpoint),
            timeout=10,
        )

        response.raise_for_status()

        return response.json()["data"]

    def datastores(self):
        return self.get("admin/datastore")
