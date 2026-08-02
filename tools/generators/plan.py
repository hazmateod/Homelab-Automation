"""
Generation Plan.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GenerationPlan:

    directories: list[str] = field(default_factory=list)

    files: list[tuple[str, str]] = field(default_factory=list)

    def add_directory(
        self,
        directory,
    ):

        self.directories.append(directory)

    def add_file(
        self,
        template,
        destination,
    ):

        self.files.append(
            (
                template,
                destination,
            )
        )

    @property
    def directory_count(self):

        return len(
            self.directories
        )

    @property
    def file_count(self):

        return len(
            self.files
        )

    @property
    def total(self):

        return (
            self.directory_count +
            self.file_count
        )
