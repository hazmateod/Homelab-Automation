"""
Execution model.
"""

from dataclasses import dataclass, field


@dataclass
class Execution:

    plugin: str

    success: bool = False

    return_code: int = 0

    elapsed: float = 0.0

    stdout: str = ""

    stderr: str = ""

    warnings: list = field(default_factory=list)

    artifacts: list = field(default_factory=list)

    def add_warning(self, warning):

        self.warnings.append(warning)

    def add_artifact(self, artifact):

        self.artifacts.append(artifact)

    def warning_count(self):

        return len(self.warnings)

    def artifact_count(self):

        return len(self.artifacts)
