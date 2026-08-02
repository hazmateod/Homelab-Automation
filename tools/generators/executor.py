"""
Generation Plan Executor.
"""

from __future__ import annotations

from pathlib import Path

from .base import Generator
from .plan import GenerationPlan


class PlanExecutor(Generator):

    def execute(
        self,
        plan: GenerationPlan,
        **context,
    ):

        for directory in plan.directories:

            self.mkdir(
                self.project_root /
                Path(directory)
            )

        for template, destination in plan.files:

            self.render(
                template,
                self.project_root /
                Path(destination),
                **context,
            )
