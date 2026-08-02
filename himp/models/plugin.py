"""
Plugin model.
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Plugin:

    id: str
    name: str
    version: str
    description: str

    author: str = ""
    entrypoint: str = ""
    inventory_group: str = ""

    supports: dict = field(default_factory=dict)
    artifacts: list = field(default_factory=list)
    requirements: list = field(default_factory=list)

    manifest: Path | None = None

    enabled: bool = True

    def __post_init__(self):

        if not self.inventory_group:
            self.inventory_group = self.id

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False

    def is_enabled(self):
        return self.enabled

    def supports_capability(self, capability):
        return self.supports.get(capability, False)

    def supports_all(self, *capabilities):
        return all(
            self.supports_capability(capability)
            for capability in capabilities
        )

    def supports_discovery(self):
        return self.supports_capability("discovery")

    def supports_health(self):
        return self.supports_capability("health")

    def supports_reporting(self):
        return self.supports_capability("reporting")

    def supports_validation(self):
        return self.supports_capability("validation")

    def supported_capabilities(self):
        return sorted(
            capability
            for capability, enabled in self.supports.items()
            if enabled
        )

    def capability_count(self):
        return len(self.supported_capabilities())

    def artifact_count(self):
        return len(self.artifacts)

    def requirement_count(self):
        return len(self.requirements)

    def has_artifact(self, name):
        return name in self.artifacts

    def has_requirement(self, name):
        return name in self.requirements

    def get_artifacts(self):
        return list(self.artifacts)

    def get_requirements(self):
        return list(self.requirements)

    @property
    def directory(self):
        if self.manifest is None:
            return None
        return self.manifest.parent

    @property
    def entrypoint_path(self):
        if self.directory is None:
            return None
        return self.directory / self.entrypoint

    @property
    def discovery_path(self):
        if self.directory is None:
            return None
        return self.directory / "tasks" / "discovery.yml"

    @property
    def health_path(self):
        if self.directory is None:
            return None
        return self.directory / "tasks" / "health.yml"

    def has_discovery(self):
        return (
            self.discovery_path is not None
            and self.discovery_path.exists()
        )

    def has_health(self):
        return (
            self.health_path is not None
            and self.health_path.exists()
        )

    def health_ready(self):
        return (
            self.supports_health()
            and self.has_discovery()
            and self.has_health()
        )

    def summary(self):
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "inventory_group": self.inventory_group,
            "enabled": self.enabled,
            "capabilities": self.capability_count(),
            "artifacts": self.artifact_count(),
            "requirements": self.requirement_count(),
        }
